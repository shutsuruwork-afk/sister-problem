/* a007764_v5.h -- v4 split into a fast and a slow kernel per vertex step.
 *
 * GPU measurements (run 4, n=18) showed v4's branching costs more than its
 * fast path saves: forcing every output through the full rank (13.50 s) beat
 * the real mixed path (14.31 s).  A warp executes every branch any lane takes,
 * and 71-77% of warps contain a lane that needs a bracket-partner scan and a
 * full rank (research/r08), so nearly every warp paid for both paths.
 *
 * v5 separates the lanes instead of mixing them:
 *   fast kernel : lanes whose plugs do not join two arcs.  No partner scan;
 *                 output rank via the O(1) local delta, or a full rank in the
 *                 rare case the MARK moves (3-5% of warps).  Lanes that do
 *                 join arcs are appended to a queue instead.
 *   slow kernel : only the queued lanes; every lane does the same kind of
 *                 work (partner scans + full ranks), so there is no divergence.
 * If the queue is full, the fast kernel processes the lane inline, so the
 * result never depends on the queue capacity.
 */
#ifndef A007764_V5_H
#define A007764_V5_H

#ifndef A007764_V4_H
#include "a007764_v4.h"
#endif

/* Slow path: the full transition of one input index (partner scans, full ranks). */
DEVFN void v5_slow(const T4 *t, const u32 *cur, u32 *nxt, u64 idx,
                   int i, int j, int n, u32 p, int fb, int term, u64 *tacc)
{
    u32 val = cur[idx];
    if (!val) return;
    u32 r = fb ? (u32)idx : (u32)(idx >> 1);
    u32 b = fb ? 0u : (u32)(idx & 1ull);
    int dw = 0, a = 0;
    u64 u = prof_unrank4(r, t, -1, &dw, &a);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1), out[2];
    int k = cell_successors(s, i, j, n, out);
    for (int q = 0; q < k; q++) {
        if (term) { if (out[q] == 0ull) *tacc += val; continue; }
        u64 u2 = 0; u32 b2 = 0;
        if (word_contract(out[q], j, &u2, &b2)) continue;
        v2_add_mod(&nxt[2 * (u64)prof_rank4(u2, t) + b2], val, p);
    }
}

/* Fast path.  Returns 1 when the lane joins two arcs and must be deferred to
 * the slow kernel (nothing has been written for it), 0 when it is done. */
DEVFN int v5_fast(const T4 *t, const u32 *cur, u32 *nxt, u64 idx,
                  int i, int j, int n, u32 p, int fb, int term, u64 *tacc)
{
    u32 val = cur[idx];
    if (!val) return 0;
    int L = n + 1;
    u32 r = fb ? (u32)idx : (u32)(idx >> 1);
    u32 b = fb ? 0u : (u32)(idx & 1ull);
    int dw = 0, a = 0;
    u64 u = prof_unrank4(r, t, fb ? -1 : j - 1, &dw, &a);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1);
    u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
    if (!fb && !term && Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE)) return 1;
    u64 out[2];
    int k = cell_successors(s, i, j, n, out);      /* no partner scan on this path */
    for (int q = 0; q < k; q++) {
        if (term) { if (out[q] == 0ull) *tacc += val; continue; }
        u64 u2 = 0; u32 b2 = 0;
        if (word_contract(out[q], j, &u2, &b2)) continue;
        u32 ro;
        if (fb) {
            ro = r;                                  /* j=0: profile unchanged */
        } else if (slot_get(u2, a) != A_MARK) {
            ro = prof_rank4(u2, t);                  /* MARK moved: rare */
        } else {
            int lo = j - 1, hi = j, d0 = dw;
            if (a == lo) { lo = j; d0 = 0; }
            else if (a == hi) { hi = j - 1; }
            int left = hi < a;
            int end = left ? a : L;
            u32 mul = left ? t->M[n - a] : 1u;
            ro = r + (local4(u2, lo, hi, d0, end, t) - local4(u, lo, hi, d0, end, t)) * mul;
        }
        v2_add_mod(&nxt[2 * (u64)ro + b2], val, p);
    }
    return 0;
}

#endif /* A007764_V5_H */
