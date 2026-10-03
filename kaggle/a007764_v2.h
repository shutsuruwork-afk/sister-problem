/* a007764_v2.h -- incremental-ranking sweep (research/r05, r06).
 * Shared verbatim by the CPU/OpenMP harness and the CUDA kernel.
 *
 * Profiles are ranked lexicographically (symbol order EMPTY < OPEN < CLOSE <
 * MARK) by a (depth, mark_seen) automaton instead of the MARK-split formula
 * of v1.  Any bijection onto [0, B(n)) is valid, and under this one:
 *   - inputs are walked in rank order with an odometer (amortised O(1)),
 *   - a transition that does not rewrite a distant partner changes the rank
 *     by a term depending on positions j-1 and j only (exhaustively checked
 *     for n=3..9 in r05), so the output rank costs O(1),
 *   - only partner rewrites (~15% of outputs) fall back to a full rank.
 * Index spaces are unchanged from v1: boundary rank in [0,B), mid-row
 * 2*rank+b in [0,2B), and the row end is idx >> 1.
 */
#ifndef A007764_V2_H
#define A007764_V2_H

#ifndef A007764_KERNEL_H
#include "a007764_kernel.h"
#endif

/* Ca[(rem*(L+2)+d)*2+m] = completions of rem symbols from state (d,m) */
typedef struct { const u64 *Ca; int L; } Auto;
#define CA_AT(a, rem, d, m) ((a)->Ca[((u64)(rem) * ((a)->L + 2) + (d)) * 2 + (m)])

DEVFN int auto_step(u32 c, int d, int m, int L, int *nd, int *nm)
{
    if (c == A_EMPTY) { *nd = d; *nm = m; return 1; }
    if (c == A_OPEN)  { *nd = d + 1; *nm = m; return d + 1 <= L; }
    if (c == A_CLOSE) { if (!d) return 0; *nd = d - 1; *nm = m; return 1; }
    if (m || d) return 0;
    *nd = 0; *nm = 1; return 1;
}

/* number of valid words that agree so far and place a smaller symbol here */
DEVFN u64 auto_contrib(const Auto *a, u32 c, int d, int m, int rem)
{
    u64 t = 0; int nd, nm;
    for (u32 c2 = 0; c2 < c; c2++)
        if (auto_step(c2, d, m, a->L, &nd, &nm)) t += CA_AT(a, rem, nd, nm);
    return t;
}

DEVFN u64 auto_rank(const Auto *a, u64 w)
{
    int L = a->L, d = 0, m = 0, nd, nm; u64 r = 0;
    for (int k = 0; k < L; k++) {
        u32 c = slot_get(w, k);
        r += auto_contrib(a, c, d, m, L - k - 1);
        auto_step(c, d, m, L, &nd, &nm); d = nd; m = nm;
    }
    return r;
}

/* rank contribution of positions lo, lo+1 starting from packed state st */
DEVFN u64 auto_local2(const Auto *a, u64 w, int lo, unsigned st)
{
    int L = a->L, d = st & 63, m = st >> 6, nd = 0, nm = 0, rem = L - lo - 1;
    u32 c0 = slot_get(w, lo), c1 = slot_get(w, lo + 1);
    u64 t = auto_contrib(a, c0, d, m, rem);
    auto_step(c0, d, m, L, &nd, &nm);
    return t + auto_contrib(a, c1, nd, nm, rem - 1);
}

/* Odometer: current profile w with rank r, and S[k] = depth | mark<<6, the
 * automaton state just before position k. */
typedef struct { u64 w, r; unsigned char S[34]; } Odo;

DEVFN void odo_set(const Auto *a, Odo *o, u64 r)
{
    int L = a->L, d = 0, m = 0, nd, nm;
    o->w = 0; o->r = r;
    for (int k = 0; k < L; k++) {
        o->S[k] = (unsigned char)(d | (m << 6));
        int rem = L - k - 1;
        for (u32 c = 0; c < 4; c++) {
            if (!auto_step(c, d, m, L, &nd, &nm)) continue;
            u64 cnt = CA_AT(a, rem, nd, nm);
            if (r < cnt) { o->w |= (u64)c << (2 * k); d = nd; m = nm; break; }
            r -= cnt;
        }
    }
    o->S[L] = (unsigned char)(d | (m << 6));
}

DEVFN void odo_next(const Auto *a, Odo *o)
{
    int L = a->L, nd, nm;
    for (int k = L - 1; k >= 0; k--) {
        u32 c = slot_get(o->w, k);
        int d = o->S[k] & 63, m = o->S[k] >> 6;
        for (u32 c2 = c + 1; c2 < 4; c2++) {
            if (!auto_step(c2, d, m, L, &nd, &nm) || !CA_AT(a, L - k - 1, nd, nm)) continue;
            o->w = slot_set(o->w, k, c2); d = nd; m = nm;
            for (int q = k + 1; q < L; q++) {
                o->S[q] = (unsigned char)(d | (m << 6));
                for (u32 c3 = 0; c3 < 4; c3++)
                    if (auto_step(c3, d, m, L, &nd, &nm) && CA_AT(a, L - q - 1, nd, nm)) {
                        o->w = slot_set(o->w, q, c3); d = nd; m = nm; break;
                    }
            }
            o->S[L] = (unsigned char)(d | (m << 6));
            o->r++;
            return;
        }
    }
}

/* modular accumulate into a shared residue array */
#ifdef __CUDACC__
DEVFN void v2_add_mod(u32 *addr, u32 v, u32 p)
{
    u32 old = *addr, assumed;
    do {
        assumed = old;
        u32 nv = assumed + v;
        if (nv >= p) nv -= p;
        old = atomicCAS(addr, assumed, nv);
    } while (assumed != old);
}
#else
DEVFN void v2_add_mod(u32 *addr, u32 v, u32 p)
{
    u32 old = __atomic_load_n(addr, __ATOMIC_RELAXED), nv;
    do {
        nv = old + v;
        if (nv >= p) nv -= p;
    } while (!__atomic_compare_exchange_n(addr, &old, nv, 1,
                                          __ATOMIC_RELAXED, __ATOMIC_RELAXED));
}
#endif

/* Process profile ranks [r0, r1) of one vertex step.
 * fb   : input is the boundary layer (vertex (i,0))
 * term : vertex (n,n); add surviving mass to *tacc instead of scattering */
DEVFN void v2_chunk(const Auto *a, const u32 *cur, u32 *nxt, u64 r0, u64 r1,
                    int i, int j, int n, u32 p, int fb, int term, u64 *tacc)
{
    if (r0 >= r1) return;
    Odo o;
    odo_set(a, &o, r0);
    for (u64 r = r0;;) {
        for (u32 b = 0; b < (fb ? 1u : 2u); b++) {
            u64 idx = fb ? r : 2 * r + b;
            u32 val = cur[idx];
            if (!val) continue;
            u64 s = fb ? (o.w << 2) : word_expand(o.w, b, j - 1);
            u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
            int isjoin = Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE);
            u64 out[2];
            int k = cell_successors(s, i, j, n, out);
            for (int t = 0; t < k; t++) {
                if (term) { if (out[t] == 0ull) *tacc += val; continue; }
                u64 u2 = 0; u32 b2 = 0;
                if (word_contract(out[t], j, &u2, &b2)) continue;   /* unreachable */
                u64 ro;
                if (isjoin) ro = auto_rank(a, u2);
                else if (fb) ro = r;                 /* j=0: profile unchanged */
                else {
                    unsigned st = o.S[j - 1];
                    ro = r - auto_local2(a, o.w, j - 1, st) + auto_local2(a, u2, j - 1, st);
                }
                v2_add_mod(&nxt[2 * ro + b2], val, p);
            }
        }
        if (++r >= r1) break;
        odo_next(a, &o);
    }
}

#endif /* A007764_V2_H */
