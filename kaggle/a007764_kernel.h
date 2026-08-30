/* a007764_kernel.h -- frontier DP core shared verbatim by the CPU reference
 * and the CUDA kernel.  Compiles as plain C99 and as CUDA device code.
 *
 * Word encoding: 2 bits per frontier slot inside a u64.
 *   0 EMPTY, 1 OPEN '(', 2 CLOSE ')', 3 MARK
 * Frontier width W = n + 2, so n <= 30 fits a u64.
 *
 * Index spaces (math/NOTES.md sec.2):
 *   boundary : rank(u) in [0, B(n)),  u a length-(n+1) profile
 *   mid row  : 2*rank(u) + b in [0, 2*B(n)) after contracting slots (j, j+1)
 */
#ifndef A007764_KERNEL_H
#define A007764_KERNEL_H

#ifdef __CUDACC__
#define DEVFN __device__ __forceinline__
#else
#define DEVFN static inline
#include <stdint.h>
#endif

typedef unsigned long long u64;
typedef unsigned int u32;

#define A_EMPTY 0u
#define A_OPEN  1u
#define A_CLOSE 2u
#define A_MARK  3u

/* Tables shared by every thread.  Tstride = n + 6. */
typedef struct {
    const u64 *T;      /* T[rem * Tstride + d] : Motzkin completions        */
    const u64 *M;      /* M[k] : Motzkin numbers                            */
    const u64 *off;    /* off[a] : profile-rank offset for MARK at slot a   */
    int n;
    int Tstride;
} Tables;

DEVFN u32 slot_get(u64 s, int k)          { return (u32)((s >> (2 * k)) & 3ull); }
DEVFN u64 slot_set(u64 s, int k, u32 v)   { return (s & ~(3ull << (2 * k))) | ((u64)v << (2 * k)); }
DEVFN u64 lowmask(int k)                  { return (k >= 32) ? ~0ull : ((1ull << (2 * k)) - 1ull); }

/* ---- Motzkin word ranking (symbol order EMPTY < OPEN < CLOSE) ---------- */
DEVFN u64 motzkin_unrank(u64 r, int k, const Tables *tb)
{
    u64 w = 0; int d = 0;
    for (int i = 0; i < k; i++) {
        int rem = k - i - 1;
        u64 c = tb->T[rem * tb->Tstride + d];
        if (r < c) { continue; }                      /* EMPTY */
        r -= c;
        c = tb->T[rem * tb->Tstride + d + 1];
        if (r < c) { w |= (u64)A_OPEN << (2 * i); d++; continue; }
        r -= c;
        w |= (u64)A_CLOSE << (2 * i); d--;
    }
    return w;
}

DEVFN u64 motzkin_rank(u64 w, int k, const Tables *tb)
{
    u64 r = 0; int d = 0;
    for (int i = 0; i < k; i++) {
        int rem = k - i - 1;
        u32 c = slot_get(w, i);
        if (c == A_OPEN) {
            r += tb->T[rem * tb->Tstride + d];
            d++;
        } else if (c == A_CLOSE) {
            r += tb->T[rem * tb->Tstride + d] + tb->T[rem * tb->Tstride + d + 1];
            d--;
        }
    }
    return r;
}

/* ---- boundary profile ranking : (Motzkin a) MARK (Motzkin b), a+b = n --- */
DEVFN u64 profile_unrank(u64 r, const Tables *tb)
{
    int n = tb->n, a = 0;
    while (r >= tb->off[a + 1]) a++;
    r -= tb->off[a];
    int b = n - a;
    u64 Mb = tb->M[b];
    u64 ql = r / Mb, qr = r - ql * Mb;
    u64 left  = motzkin_unrank(ql, a, tb);
    u64 right = motzkin_unrank(qr, b, tb);
    return left | ((u64)A_MARK << (2 * a)) | (right << (2 * (a + 1)));
}

DEVFN u64 profile_rank(u64 w, const Tables *tb)
{
    int n = tb->n, a = 0;
    while (slot_get(w, a) != A_MARK) a++;
    int b = n - a;
    u64 left  = w & lowmask(a);
    u64 right = w >> (2 * (a + 1));
    return tb->off[a] + motzkin_rank(left, a, tb) * tb->M[b]
                      + motzkin_rank(right, b, tb);
}

/* ---- contract / expand of the two plug slots (j, j+1) ------------------ */
DEVFN u64 word_expand(u64 u, u32 b, int j)
{
    u32 val = slot_get(u, j), lo, hi;
    if (val == A_EMPTY) { lo = b ? A_OPEN : A_EMPTY; hi = b ? A_CLOSE : A_EMPTY; }
    else                { lo = b ? A_EMPTY : val;    hi = b ? val : A_EMPTY;     }
    return (u & lowmask(j))
         | ((u64)lo << (2 * j)) | ((u64)hi << (2 * j + 2))
         | ((u >> (2 * (j + 1))) << (2 * (j + 2)));
}

/* returns 0 on success and writes the contracted word + bit */
DEVFN int word_contract(u64 s, int j, u64 *u_out, u32 *b_out)
{
    u32 lo = slot_get(s, j), hi = slot_get(s, j + 1), val, b;
    if (lo == A_EMPTY && hi == A_EMPTY)      { val = A_EMPTY; b = 0; }
    else if (lo == A_OPEN && hi == A_CLOSE)  { val = A_EMPTY; b = 1; }
    else if (hi == A_EMPTY)                  { val = lo;      b = 0; }
    else if (lo == A_EMPTY)                  { val = hi;      b = 1; }
    else return -1;
    *u_out = (s & lowmask(j)) | ((u64)val << (2 * j))
           | ((s >> (2 * (j + 2))) << (2 * (j + 1)));
    *b_out = b;
    return 0;
}

/* ---- bracket partner --------------------------------------------------- */
DEVFN int find_partner(u64 s, int k, int W)
{
    int depth = 0;
    if (slot_get(s, k) == A_OPEN) {
        for (int t = k + 1; t < W; t++) {
            u32 c = slot_get(s, t);
            if (c == A_OPEN) depth++;
            else if (c == A_CLOSE) { if (!depth) return t; depth--; }
        }
    } else {
        for (int t = k - 1; t >= 0; t--) {
            u32 c = slot_get(s, t);
            if (c == A_CLOSE) depth++;
            else if (c == A_OPEN) { if (!depth) return t; depth--; }
        }
    }
    return -1;
}

/* ---- one vertex transition; writes up to two successor words ----------- */
DEVFN int cell_successors(u64 s, int i, int j, int n, u64 out[2])
{
    int W = n + 2;
    u32 L = slot_get(s, j), U = slot_get(s, j + 1);
    u64 base = slot_set(slot_set(s, j, A_EMPTY), j + 1, A_EMPTY);
    int can_down = (i < n), can_right = (j < n), c = 0;

    if (i == 0 && j == 0) {
        if (L || U) return 0;
        if (can_down)  out[c++] = slot_set(base, j, A_MARK);
        if (can_right) out[c++] = slot_set(base, j + 1, A_MARK);
        return c;
    }
    if (i == n && j == n) {
        if ((L == A_MARK && U == A_EMPTY) || (U == A_MARK && L == A_EMPTY))
            out[c++] = base;
        return c;
    }
    if (L == A_EMPTY && U == A_EMPTY) {
        out[c++] = base;
        if (can_down && can_right)
            out[c++] = slot_set(slot_set(base, j, A_OPEN), j + 1, A_CLOSE);
        return c;
    }
    if (L == A_EMPTY || U == A_EMPTY) {
        u32 v = (U == A_EMPTY) ? L : U;
        if (can_down)  out[c++] = slot_set(base, j, v);
        if (can_right) out[c++] = slot_set(base, j + 1, v);
        return c;
    }
    if (L == A_OPEN && U == A_CLOSE) return 0;          /* closes a cycle */
    if (L == A_MARK) { out[c++] = slot_set(base, find_partner(s, j + 1, W), A_MARK); return c; }
    if (U == A_MARK) { out[c++] = slot_set(base, find_partner(s, j,     W), A_MARK); return c; }
    {
        int a = find_partner(s, j, W), b2 = find_partner(s, j + 1, W);
        int lo = a < b2 ? a : b2, hi = a < b2 ? b2 : a;
        out[c++] = slot_set(slot_set(base, lo, A_OPEN), hi, A_CLOSE);
    }
    return c;
}

/* ---- rebuild the frontier word standing just before vertex (i,j) ------- */
DEVFN u64 word_before(u64 idx, int j, int from_boundary, const Tables *tb)
{
    if (from_boundary) return profile_unrank(idx, tb) << 2;   /* prepend EMPTY */
    u64 r = idx >> 1; u32 b = (u32)(idx & 1ull);
    return word_expand(profile_unrank(r, tb), b, j - 1);
}

#endif /* A007764_KERNEL_H */
