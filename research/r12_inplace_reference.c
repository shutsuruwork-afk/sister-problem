/* r12: a working in-place sweep (one state array) with a spill area.
 *
 * Each mid->mid step walks the array in chunks of C slots, highest chunk
 * first.  For chunk c: copy its old values out, zero it, apply the spilled
 * contributions destined for it, then process its inputs.  A write to a slot
 * in chunk >= c is safe (that slot's old value was already read); a write to a
 * lower, unread chunk is spilled as (offset, value) into that chunk's bucket.
 * Row start (boundary r -> mid 2r+b) is safe in place walking r downwards, and
 * row end (mid 2r -> boundary r) walking r upwards.  Exact, sequential, full
 * ranks (correctness and memory, not speed).  Prints a(n) mod p and the peak
 * spill relative to the 2B(n) array. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../kaggle/a007764_kernel.h"
#include "../kaggle/a007764_v2.h"
#include "../kaggle/a007764_v4.h"

typedef struct { u32 off, val; } Spill;

int main(int argc, char **argv)
{
    int n = atoi(argv[1]), lgC = argc > 2 ? atoi(argv[2]) : 12, Ts4 = n + 3; u32 p = 2147483629u;
    u64 *Tw = calloc((size_t)(n + 1) * (n + 6), 8); Tw[0] = 1;
    for (int rem = 1; rem <= n; rem++) for (int d = 0; d <= n + 3; d++) {
        u64 v = Tw[(rem-1)*(n+6)+d] + Tw[(rem-1)*(n+6)+d+1]; if (d) v += Tw[(rem-1)*(n+6)+d-1]; Tw[rem*(n+6)+d] = v; }
    u32 *T32 = calloc((n+1)*Ts4, 4), *M32 = calloc(n+1, 4), *O32 = calloc(n+2, 4); u64 *mi = calloc(n+1, 8);
    for (int rem = 0; rem <= n; rem++) for (int d = 0; d < Ts4; d++) T32[rem*Ts4+d] = (u32)Tw[rem*(n+6)+d];
    for (int k = 0; k <= n; k++) { M32[k] = (u32)Tw[k*(n+6)]; mi[k] = (1ull<<32) / M32[k]; }
    u64 acc = 0; for (int x = 0; x <= n; x++) { O32[x] = (u32)acc; acc += (u64)M32[x]*M32[n-x]; } O32[n+1] = (u32)acc;
    T4 t = { T32, M32, O32, mi, n, Ts4 };
    u64 B = O32[n+1], S = 2*B, C = 1ull << lgC, nch = (S + C - 1) / C;
    u32 *A = calloc(S, 4), *tmp = calloc(C, 4);                      /* the ONLY state array */
    Spill **bk = calloc(nch, sizeof(Spill *)); u64 *bn = calloc(nch, 8), *bc = calloc(nch, 8);
    u64 live = 0, peak = 0, ans = 0;
    A[0] = A[1] = 1;
    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            if (term) {
                for (u64 x = 0; x < S; x++) {
                    if (!A[x]) continue;
                    int dw, a; u64 u = prof_unrank4((u32)(x >> 1), &t, -1, &dw, &a);
                    u64 s = word_expand(u, (u32)(x & 1), j - 1), out[2];
                    int k = cell_successors(s, i, j, n, out);
                    for (int q = 0; q < k; q++) if (!out[q]) ans += A[x];
                }
                goto done;
            }
            if (fb) {                              /* boundary r -> mid 2r+b', walk r downwards */
                for (u64 r = B; r-- > 0;) {
                    u32 v = A[r]; A[r] = 0;
                    if (!v) continue;
                    int dw, a; u64 u = prof_unrank4((u32)r, &t, -1, &dw, &a), out[2];
                    int k = cell_successors(u << 2, i, j, n, out);
                    for (int q = 0; q < k; q++) {
                        u64 u2; u32 b2; if (word_contract(out[q], j, &u2, &b2)) continue;
                        u64 y = 2 * (u64)prof_rank4(u2, &t) + b2;    /* y >= r: already read */
                        u32 z = A[y] + v; if (z >= p) z -= p; A[y] = z;
                    }
                }
                continue;
            }
            for (u64 c = nch; c-- > 0;) {           /* mid -> mid, chunks downwards */
                u64 lo = c * C, hi = lo + C < S ? lo + C : S;
                memcpy(tmp, A + lo, (hi - lo) * 4); memset(A + lo, 0, (hi - lo) * 4);
                for (u64 e = 0; e < bn[c]; e++) {
                    u32 *d = &A[lo + bk[c][e].off]; u32 z = *d + bk[c][e].val; if (z >= p) z -= p; *d = z;
                }
                live -= bn[c]; bn[c] = 0;
                for (u64 x = lo; x < hi; x++) {
                    u32 v = tmp[x - lo]; if (!v) continue;
                    int dw, a; u64 u = prof_unrank4((u32)(x >> 1), &t, -1, &dw, &a);
                    u64 s = word_expand(u, (u32)(x & 1), j - 1), out[2];
                    int k = cell_successors(s, i, j, n, out);
                    for (int q = 0; q < k; q++) {
                        u64 u2; u32 b2; if (word_contract(out[q], j, &u2, &b2)) continue;
                        u64 y = 2 * (u64)prof_rank4(u2, &t) + b2, cy = y / C;
                        if (cy >= c) { u32 z = A[y] + v; if (z >= p) z -= p; A[y] = z; }
                        else {
                            if (bn[cy] == bc[cy]) { bc[cy] = bc[cy] ? 2 * bc[cy] : 16; bk[cy] = realloc(bk[cy], bc[cy] * sizeof(Spill)); }
                            bk[cy][bn[cy]].off = (u32)(y - cy * C); bk[cy][bn[cy]].val = v; bn[cy]++;
                            if (++live > peak) peak = live;
                        }
                    }
                }
            }
        }
        for (u64 r = 0; r < B; r++) A[r] = A[2 * r];   /* row end, upwards: 2r is read before r is written */
        memset(A + B, 0, (S - B) * 4);
    }
done:
    printf("n=%2d C=2^%-2d a(n) mod p=%10llu | one array of 2B=%llu slots + peak spill %.4f x 2B entries "
           "(%.2f bits/state at 11-bit residues, offset %d bits)\n",
           n, lgC, (unsigned long long)(ans % p), (unsigned long long)S, (double)peak / S,
           (double)peak / S * (lgC + 11), lgC);
    return 0;
}
