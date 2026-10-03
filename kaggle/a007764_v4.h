/* a007764_v4.h -- v1's layout and ranking, made cheaper where the GPU
 * actually spends its time.
 *
 * The bottleneck probe on a GTX 1660 SUPER showed v1 and v3 are ~100%
 * compute bound: memory traffic and atomics hide entirely behind the
 * unrank/rank arithmetic.  So v4 attacks arithmetic only:
 *   1. 32-bit everywhere.  For n <= 22 every rank, table entry and index is
 *      below 2^32, and NVIDIA GPUs have no native 64-bit integer ALU.
 *   2. No division.  r / M_b becomes a multiply by floor(2^32 / M_b) plus at
 *      most one correction step.
 *   3. O(1) output rank in v1's MARK-split ranking.  A transition that keeps
 *      the MARK in place and rewrites no distant partner only touches
 *      positions j-1, j, which lie inside one Motzkin word; Motzkin ranking is
 *      lexicographic over a depth automaton, so the rank moves by a local term
 *      (times M_b when the change is in the left word).  The depth needed is
 *      captured during the unrank, at no extra cost.
 * Anything else (MARK moved, partner rewrite) falls back to a full rank.
 * Index spaces and the meaning of every array slot are identical to v1.
 */
#ifndef A007764_V4_H
#define A007764_V4_H

#ifndef A007764_KERNEL_H
#include "a007764_kernel.h"
#endif
#ifndef A007764_V2_H
#include "a007764_v2.h"        /* v2_add_mod */
#endif

typedef struct {
    const u32 *T;      /* T[rem * Ts + d], rem <= n, d <= n+2                */
    const u32 *M;      /* M[k], k <= n                                       */
    const u32 *off;    /* off[a], a <= n+1;  off[n+1] = B(n)                 */
    const u64 *minv;   /* floor(2^32 / M[b]), b <= n                         */
    int n, Ts;
} T4;
#define T4T(t, rem, d) ((t)->T[(rem) * (t)->Ts + (d)])

DEVFN u32 div4(u32 r, int b, const T4 *t, u32 *rem_out)
{
    u32 Mb = t->M[b];
    u32 q = (u32)(((u64)r * t->minv[b]) >> 32);   /* q in {floor-1, floor} */
    u32 rr = r - q * Mb;
    if (rr >= Mb) { q++; rr -= Mb; }
    *rem_out = rr;
    return q;
}

/* Motzkin word of length k from rank r; also the depth before local
 * position `want` (if 0 <= want < k). */
DEVFN u64 motz_unrank4(u32 r, int k, const T4 *t, int want, int *d_want)
{
    u64 w = 0; int d = 0;
    for (int i = 0; i < k; i++) {
        if (i == want) *d_want = d;
        int rem = k - i - 1;
        u32 c = T4T(t, rem, d);
        if (r < c) continue;                          /* EMPTY */
        r -= c;
        c = T4T(t, rem, d + 1);
        if (r < c) { w |= (u64)A_OPEN << (2 * i); d++; continue; }
        r -= c;
        w |= (u64)A_CLOSE << (2 * i); d--;
    }
    return w;
}

DEVFN u32 motz_rank4(u64 w, int k, const T4 *t)
{
    u32 r = 0; int d = 0;
    for (int i = 0; i < k; i++) {
        int rem = k - i - 1;
        u32 c = slot_get(w, i);
        if (c == A_OPEN)       { r += T4T(t, rem, d); d++; }
        else if (c == A_CLOSE) { r += T4T(t, rem, d) + T4T(t, rem, d + 1); d--; }
    }
    return r;
}

/* profile from rank; *a_out = MARK position, *d_want = depth of the full
 * profile just before position `want` (equal to the depth inside whichever
 * Motzkin word contains it, since the left word is balanced at the MARK). */
DEVFN u64 prof_unrank4(u32 r, const T4 *t, int want, int *d_want, int *a_out)
{
    int n = t->n, a = 0;
    while (r >= t->off[a + 1]) a++;
    r -= t->off[a];
    int b = n - a;
    u32 qr, ql = div4(r, b, t, &qr);
    *d_want = 0;
    u64 left  = motz_unrank4(ql, a, t, want, d_want);
    u64 right = motz_unrank4(qr, b, t, want - (a + 1), d_want);
    *a_out = a;
    return left | ((u64)A_MARK << (2 * a)) | (right << (2 * (a + 1)));
}

DEVFN u32 prof_rank4(u64 w, const T4 *t)
{
    int n = t->n, a = 0;
    while (slot_get(w, a) != A_MARK) a++;
    int b = n - a;
    return t->off[a] + motz_rank4(w & lowmask(a), a, t) * t->M[b]
                     + motz_rank4(w >> (2 * (a + 1)), b, t);
}

DEVFN u32 contrib4(u32 c, int d, int rem, const T4 *t)
{
    if (c == A_OPEN)  return T4T(t, rem, d);
    if (c == A_CLOSE) return T4T(t, rem, d) + T4T(t, rem, d + 1);
    return 0;
}

/* Motzkin rank contribution of positions [lo, hi] (inclusive, at most two)
 * of word w, starting from depth d, inside a part that ends at `end`. */
DEVFN u32 local4(u64 w, int lo, int hi, int d, int end, const T4 *t)
{
    u32 s = 0;
    for (int k = lo; k <= hi; k++) {
        u32 c = slot_get(w, k);
        s += contrib4(c, d, end - k - 1, t);
        d += (c == A_OPEN) - (c == A_CLOSE);
    }
    return s;
}

/* Process one input index of one vertex step (same contract as v1).
 * dry: bottleneck probe -- treat the index as live and XOR the output
 * index into *tacc instead of scattering, so compute is measured alone. */
DEVFN void v4_index(const T4 *t, const u32 *cur, u32 *nxt, u64 idx,
                    int i, int j, int n, u32 p, int fb, int term, int dry, u64 *tacc
#ifdef V4_STATS
                    , u64 *st_local, u64 *st_mark, u64 *st_join
#endif
                    )
{
    u32 val = dry ? 1u : cur[idx];
    if (!val) return;
    int L = n + 1;
    u32 r = fb ? (u32)idx : (u32)(idx >> 1);
    u32 b = fb ? 0u : (u32)(idx & 1ull);
    int dw = 0, a = 0;
    u64 u = prof_unrank4(r, t, fb ? -1 : j - 1, &dw, &a);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1);
    u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
    int isjoin = Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE);
    u64 out[2];
    int k = cell_successors(s, i, j, n, out);
    for (int q = 0; q < k; q++) {
        if (term) { if (out[q] == 0ull) *tacc += val; continue; }
        u64 u2 = 0; u32 b2 = 0;
        if (word_contract(out[q], j, &u2, &b2)) continue;    /* unreachable */
        u32 ro;
        if (fb) {
            ro = r;                                          /* j=0: profile unchanged */
        } else if (isjoin || slot_get(u2, a) != A_MARK) {
            ro = prof_rank4(u2, t);                          /* partner rewrite / MARK moved */
#ifdef V4_STATS
            if (isjoin) (*st_join)++; else (*st_mark)++;
#endif
        } else {
            int lo = j - 1, hi = j, d0 = dw;
            if (a == lo) { lo = j; d0 = 0; }                 /* only j changes, right word */
            else if (a == hi) { hi = j - 1; }                /* only j-1 changes, left word */
            int left = hi < a;
            int end = left ? a : L;
            u32 mul = left ? t->M[n - a] : 1u;
            ro = r + (local4(u2, lo, hi, d0, end, t) - local4(u, lo, hi, d0, end, t)) * mul;
#ifdef V4_STATS
            (*st_local)++;
#endif
        }
        if (dry) *tacc ^= 2 * (u64)ro + b2 + (u64)q;
        else v2_add_mod(&nxt[2 * (u64)ro + b2], val, p);
    }
}

#endif /* A007764_V4_H */
