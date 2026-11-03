/* a007764_v7.h -- v5/v6 with residues packed below 32 bits.
 *
 * Each state carries a record of K residues of b bits (W = K*b <= 64 bits);
 * f = floor(64 / W) records share one 64-bit word.  A record is updated with
 * a compare-and-swap on its word, so neighbours in the same word never lose
 * an update.  This is what lets memory buy CRT progress at the frontier:
 * one 8xB300 node holds about 11 bits per state with two buffers, so the
 * residues must be narrower than 32 bits (RESEARCH_LOG F27).
 *
 * Moduli must be pairwise coprime and below 2^b.  Indices are 32-bit (n <= 22,
 * as in v4-v6).  Same index spaces and fast/slow split as v5.
 */
#ifndef A007764_V7_H
#define A007764_V7_H

#ifndef A007764_V5_H
#include "a007764_v5.h"
#endif

#define V7_KMAX 8

typedef struct {
    int K, b, W, f;
    u64 finv;          /* floor(2^32 / f) */
    u64 recmask, bmask;
    u32 m[V7_KMAX];
} Pack;

DEVFN u32 pk_div(const Pack *pk, u32 y, u32 *rem)
{
    u32 q = (u32)(((u64)y * pk->finv) >> 32);
    u32 rr = y - q * (u32)pk->f;
    if (rr >= (u32)pk->f) { q++; rr -= (u32)pk->f; }
    *rem = rr;
    return q;
}

DEVFN u64 pk_get(const Pack *pk, const u64 *buf, u32 y)
{
    u32 s, w = pk_div(pk, y, &s);
    return (buf[w] >> (s * pk->W)) & pk->recmask;
}

DEVFN void pk_unpack(const Pack *pk, u64 rec, u32 *v)
{
    for (int t = 0; t < pk->K; t++) v[t] = (u32)((rec >> (t * pk->b)) & pk->bmask);
}

#ifdef __CUDACC__
DEVFN u64 pk_cas(u64 *addr, u64 expect, u64 desired)
{
    return atomicCAS((unsigned long long *)addr, expect, desired);
}
#else
DEVFN u64 pk_cas(u64 *addr, u64 expect, u64 desired)
{
    __atomic_compare_exchange_n(addr, &expect, desired, 0, __ATOMIC_RELAXED, __ATOMIC_RELAXED);
    return expect;                       /* holds the value seen, as atomicCAS returns */
}
#endif

/* record y += v (lane-wise mod m_t), atomically with respect to the whole word */
DEVFN void pk_add(const Pack *pk, u64 *buf, u32 y, const u32 *v)
{
    u32 s, w = pk_div(pk, y, &s);
    unsigned sh = s * pk->W;
    u64 *addr = &buf[w];
    u64 old = *addr, assumed;
    do {
        assumed = old;
        u64 rec = (assumed >> sh) & pk->recmask, nr = 0;
        for (int t = 0; t < pk->K; t++) {
            u64 fld = ((rec >> (t * pk->b)) & pk->bmask) + v[t];
            if (fld >= pk->m[t]) fld -= pk->m[t];
            nr |= fld << (t * pk->b);
        }
        old = pk_cas(addr, assumed, (assumed & ~(pk->recmask << sh)) | (nr << sh));
    } while (old != assumed);
}

/* The transition of one input index, as output indices only.
 * fast = 1: returns -1 for a lane that joins two arcs (deferred); otherwise
 * the O(1) local rank is used.  fast = 0: full ranks, partner scans allowed.
 * For the terminal vertex the return value is the number of surviving paths
 * (outputs equal to the empty frontier), ys untouched. */
DEVFN int v7_outputs(const T4 *t, u32 idx, int i, int j, int n, int fb, int term,
                     int fast, u32 ys[2])
{
    int L = n + 1;
    u32 r = fb ? idx : (idx >> 1);
    u32 b = fb ? 0u : (idx & 1u);
    int dw = 0, a = 0;
    u64 u = prof_unrank4(r, t, (fast && !fb) ? j - 1 : -1, &dw, &a);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1);
    u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
    if (fast && !fb && !term && Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE)) return -1;
    u64 out[2];
    int k = cell_successors(s, i, j, n, out), c = 0;
    if (term) { for (int q = 0; q < k; q++) c += out[q] == 0ull; return c; }
    for (int q = 0; q < k; q++) {
        u64 u2 = 0; u32 b2 = 0;
        if (word_contract(out[q], j, &u2, &b2)) continue;
        u32 ro;
        if (fb) {
            ro = r;
        } else if (!fast || slot_get(u2, a) != A_MARK) {
            ro = prof_rank4(u2, t);
        } else {
            int lo = j - 1, hi = j, d0 = dw;
            if (a == lo) { lo = j; d0 = 0; }
            else if (a == hi) { hi = j - 1; }
            int left = hi < a;
            int end = left ? a : L;
            u32 mul = left ? t->M[n - a] : 1u;
            ro = r + (local4(u2, lo, hi, d0, end, t) - local4(u, lo, hi, d0, end, t)) * mul;
        }
        ys[c++] = 2 * ro + b2;
    }
    return c;
}

/* returns 1 if the lane must go to the slow kernel */
DEVFN int v7_lane(const T4 *t, const Pack *pk, const u64 *cur, u64 *nxt, u32 idx,
                  int i, int j, int n, int fb, int term, int fast, u64 *tacc)
{
    u64 rec = pk_get(pk, cur, idx);
    if (!rec) return 0;
    u32 ys[2];
    int c = v7_outputs(t, idx, i, j, n, fb, term, fast, ys);
    if (c < 0) return 1;
    u32 v[V7_KMAX];
    pk_unpack(pk, rec, v);
    if (term) { for (int q = 0; q < pk->K; q++) tacc[q] += (u64)v[q] * (u64)c; return 0; }
    for (int q = 0; q < c; q++) pk_add(pk, nxt, ys[q], v);
    return 0;
}

/* row end: boundary record r <- mid record 2r, one thread per destination word */
DEVFN void v7_rowend_word(const Pack *pk, const u64 *cur, u64 *nxt, u32 w, u32 B)
{
    u64 word = 0;
    for (int s = 0; s < pk->f; s++) {
        u32 r = w * (u32)pk->f + (u32)s;
        if (r < B) word |= pk_get(pk, cur, 2 * r) << (s * pk->W);
    }
    nxt[w] = word;
}

#endif /* A007764_V7_H */
