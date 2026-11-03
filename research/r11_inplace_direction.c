/* r11: can a cell step run in place (one array instead of two)?
 * For every transition x -> y of a real sweep (MARK-split ranking, v4),
 * record whether the output index lies before, at, or after the input index,
 * and how far forward the forward ones reach.  If every write went to an
 * index already read, a single ascending pass would be safe in place; the
 * forward writes are what would have to be held back.  Row-start steps
 * (boundary r -> mid 2r+b) are reported separately: y >= x there, and a
 * descending pass makes them safe (slot 2r is read before it is written). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../kaggle/a007764_kernel.h"
#include "../kaggle/a007764_v2.h"
#include "../kaggle/a007764_v4.h"

int main(int argc, char **argv)
{
    int n = atoi(argv[1]), Ts4 = n + 3; u32 p = 2147483629u;
    u64 *Tw = calloc((size_t)(n + 1) * (n + 6), 8); Tw[0] = 1;
    for (int rem = 1; rem <= n; rem++) for (int d = 0; d <= n + 3; d++) {
        u64 v = Tw[(rem-1)*(n+6)+d] + Tw[(rem-1)*(n+6)+d+1]; if (d) v += Tw[(rem-1)*(n+6)+d-1]; Tw[rem*(n+6)+d] = v; }
    u32 *T32 = calloc((n+1)*Ts4, 4), *M32 = calloc(n+1, 4), *O32 = calloc(n+2, 4); u64 *mi = calloc(n+1, 8);
    for (int rem = 0; rem <= n; rem++) for (int d = 0; d < Ts4; d++) T32[rem*Ts4+d] = (u32)Tw[rem*(n+6)+d];
    for (int k = 0; k <= n; k++) { M32[k] = (u32)Tw[k*(n+6)]; mi[k] = (1ull<<32) / M32[k]; }
    u64 acc = 0; for (int x = 0; x <= n; x++) { O32[x] = (u32)acc; acc += (u64)M32[x]*M32[n-x]; } O32[n+1] = (u32)acc;
    T4 t = { T32, M32, O32, mi, n, Ts4 };
    u64 B = O32[n+1], S = 2*B;
    u32 *cur = calloc(S, 4), *nxt = calloc(S, 4);
    cur[0] = cur[1] = 1;
    u64 back = 0, same = 0, fwd = 0, ans = 0, maxpend = 0;
    double sumdist = 0; u64 maxdist = 0;
    /* pending forward writes at the moment the ascending read pointer passes x */
    long long *delta = calloc(S + 1, sizeof(long long)), *ddes = calloc(S + 1, sizeof(long long));
    u64 maxpend_desc = 0;
    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            u64 size_in = fb ? B : S;
            if (!term) memset(nxt, 0, S * 4);
            if (!fb && !term) { memset(delta, 0, (S + 1) * sizeof(long long)); memset(ddes, 0, (S + 1) * sizeof(long long)); }
            for (u64 x = 0; x < size_in; x++) {
                u32 v = cur[x]; if (!v) continue;
                u32 r = fb ? (u32)x : (u32)(x >> 1), b = fb ? 0 : (u32)(x & 1);
                int dw, a; u64 u = prof_unrank4(r, &t, -1, &dw, &a);
                u64 s = fb ? (u << 2) : word_expand(u, b, j - 1), out[2];
                int k = cell_successors(s, i, j, n, out);
                for (int q = 0; q < k; q++) {
                    if (term) { if (!out[q]) ans += v; continue; }
                    u64 u2; u32 b2; if (word_contract(out[q], j, &u2, &b2)) continue;
                    u64 y = 2 * (u64)prof_rank4(u2, &t) + b2;
                    u32 z = nxt[y] + v; if (z >= p) z -= p; nxt[y] = z;
                    if (fb) continue;
                    if (y < x) { back++; ddes[y + 1] += 1; ddes[x + 1] -= 1; }  /* descending: pending from x down to y */
                    else if (y == x) same++;
                    else { fwd++; sumdist += (double)(y - x); if (y - x > maxdist) maxdist = y - x;
                           delta[x] += 1; delta[y] -= 1; }      /* pending from read of x until y is read */
                }
            }
            if (!fb && !term) {
                long long run = 0;
                for (u64 x = 0; x < S; x++) { run += delta[x]; if ((u64)run > maxpend) maxpend = run; }
                run = 0;
                for (u64 x = 0; x <= S; x++) { run += ddes[x]; if ((u64)run > maxpend_desc) maxpend_desc = run; }
            }
            if (term) goto done;
            u32 *q = cur; cur = nxt; nxt = q;
        }
        memset(nxt, 0, S * 4); for (u64 r = 0; r < B; r++) nxt[r] = cur[2*r];
        u32 *q = cur; cur = nxt; nxt = q;
    }
done:;
    double tot = (double)(back + same + fwd);
    printf("n=%2d  a(n) mod p=%10llu | mid->mid writes: back %.3f  same %.3f  forward %.3f | "
           "forward mean dist %.3g (=%.4f of 2B), max %.3f of 2B | peak pending: ascending %.4f, descending %.4f of 2B\n",
           n, (unsigned long long)(ans % p), back / tot, same / tot, fwd / tot,
           sumdist / (fwd ? fwd : 1), sumdist / (fwd ? fwd : 1) / S, (double)maxdist / S, (double)maxpend / S, (double)maxpend_desc / S);
    return 0;
}
