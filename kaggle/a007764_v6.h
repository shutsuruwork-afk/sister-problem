/* a007764_v6.h -- v5 carrying K residues per state in one sweep.
 *
 * Every GPU measurement so far says the sweep is compute bound: the scatter
 * hides entirely behind the index work (unrank, transition, rank).  That
 * index work is identical for every CRT prime; only the values differ.  v6
 * therefore computes each output index once and applies it to K residue
 * planes (one per prime), so the index work per prime drops to about 1/K
 * for as long as the extra memory traffic stays hidden.
 *
 * Layout: plane t of a buffer is buf[t * S + idx], S = 2*B(n).  The boundary
 * layer uses the first B entries of each plane.  Same index spaces, same
 * fast/slow split and queue as v5.
 */
#ifndef A007764_V6_H
#define A007764_V6_H

#ifndef A007764_V5_H
#include "a007764_v5.h"
#endif

#define V6_KMAX 8

typedef struct { int k; u64 S; u32 p[V6_KMAX]; } Planes;

DEVFN int v6_load(const Planes *pl, const u32 *cur, u64 idx, u32 *v)
{
    int any = 0;
    for (int t = 0; t < pl->k; t++) { v[t] = cur[(u64)t * pl->S + idx]; any |= v[t] != 0; }
    return any;
}

DEVFN void v6_emit(const Planes *pl, u32 *nxt, u64 y, const u32 *v)
{
    for (int t = 0; t < pl->k; t++)
        if (v[t]) v2_add_mod(&nxt[(u64)t * pl->S + y], v[t], pl->p[t]);
}

DEVFN void v6_term(const Planes *pl, const u32 *v, u64 *tacc)
{
    for (int t = 0; t < pl->k; t++) tacc[t] += v[t];
}

/* Slow path for one input index, all K planes. */
DEVFN void v6_slow(const T4 *t, const Planes *pl, const u32 *cur, u32 *nxt, u64 idx,
                   int i, int j, int n, int fb, int term, u64 *tacc)
{
    u32 v[V6_KMAX];
    if (!v6_load(pl, cur, idx, v)) return;
    u32 r = fb ? (u32)idx : (u32)(idx >> 1);
    u32 b = fb ? 0u : (u32)(idx & 1ull);
    int dw = 0, a = 0;
    u64 u = prof_unrank4(r, t, -1, &dw, &a);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1), out[2];
    int k = cell_successors(s, i, j, n, out);
    for (int q = 0; q < k; q++) {
        if (term) { if (out[q] == 0ull) v6_term(pl, v, tacc); continue; }
        u64 u2 = 0; u32 b2 = 0;
        if (word_contract(out[q], j, &u2, &b2)) continue;
        v6_emit(pl, nxt, 2 * (u64)prof_rank4(u2, t) + b2, v);
    }
}

/* Fast path; returns 1 if the lane joins two arcs and must be deferred. */
DEVFN int v6_fast(const T4 *t, const Planes *pl, const u32 *cur, u32 *nxt, u64 idx,
                  int i, int j, int n, int fb, int term, u64 *tacc)
{
    u32 v[V6_KMAX];
    if (!v6_load(pl, cur, idx, v)) return 0;
    int L = n + 1;
    u32 r = fb ? (u32)idx : (u32)(idx >> 1);
    u32 b = fb ? 0u : (u32)(idx & 1ull);
    int dw = 0, a = 0;
    u64 u = prof_unrank4(r, t, fb ? -1 : j - 1, &dw, &a);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1);
    u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
    if (!fb && !term && Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE)) return 1;
    u64 out[2];
    int k = cell_successors(s, i, j, n, out);
    for (int q = 0; q < k; q++) {
        if (term) { if (out[q] == 0ull) v6_term(pl, v, tacc); continue; }
        u64 u2 = 0; u32 b2 = 0;
        if (word_contract(out[q], j, &u2, &b2)) continue;
        u32 ro;
        if (fb) {
            ro = r;
        } else if (slot_get(u2, a) != A_MARK) {
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
        v6_emit(pl, nxt, 2 * (u64)ro + b2, v);
    }
    return 0;
}

#endif /* A007764_V6_H */
