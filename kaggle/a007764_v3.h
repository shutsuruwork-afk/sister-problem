/* a007764_v3.h -- v1's thread layout with v2's O(1) output rank.
 *
 * v2 was 3.1x faster than v1 on CPU but 0.32x on a GTX 1660 SUPER, and got
 * faster as chunks shrank: per-thread rank ranges break read coalescing,
 * the odometer has data-dependent trip counts, and its state array lives in
 * local memory.  v3 keeps what v1 does well on a GPU -- one index per
 * thread, grid-stride, coalesced reads, an unrank loop of fixed trip count
 * L -- and takes from v2 only the part that needs no per-thread history:
 * the automaton state just before position j-1 falls out of the unrank loop
 * for free, which is all the O(1) local output rank (research/r05) needs.
 */
#ifndef A007764_V3_H
#define A007764_V3_H

#ifndef A007764_V2_H
#include "a007764_v2.h"
#endif

/* automaton unrank; also returns the packed state before position `want` */
DEVFN u64 auto_unrank_at(const Auto *a, u64 r, int want, unsigned *st_want)
{
    int L = a->L, d = 0, m = 0, nd, nm;
    u64 w = 0;
    for (int k = 0; k < L; k++) {
        if (k == want) *st_want = (unsigned)(d | (m << 6));
        int rem = L - k - 1;
        for (u32 c = 0; c < 4; c++) {
            if (!auto_step(c, d, m, L, &nd, &nm)) continue;
            u64 cnt = CA_AT(a, rem, nd, nm);
            if (r < cnt) { w |= (u64)c << (2 * k); d = nd; m = nm; break; }
            r -= cnt;
        }
    }
    return w;
}

/* One input index of one vertex step (same index spaces as v1/v2). */
DEVFN void v3_index(const Auto *a, const u32 *cur, u32 *nxt, u64 idx,
                    int i, int j, int n, u32 p, int fb, int term, u64 *tacc)
{
    u32 val = cur[idx];
    if (!val) return;
    u64 r = fb ? idx : (idx >> 1);
    u32 b = fb ? 0u : (u32)(idx & 1ull);
    unsigned st = 0;
    u64 u = auto_unrank_at(a, r, fb ? -1 : j - 1, &st);
    u64 s = fb ? (u << 2) : word_expand(u, b, j - 1);
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
        else if (fb) ro = r;                                 /* j=0: profile unchanged */
        else ro = r - auto_local2(a, u, j - 1, st) + auto_local2(a, u2, j - 1, st);
        v2_add_mod(&nxt[2 * ro + b2], val, p);
    }
}

#endif /* A007764_V3_H */
