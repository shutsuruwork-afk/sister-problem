/* r09: if the index space [0, 2B(n)) is split into G contiguous rank ranges,
 * one per GPU, what fraction of the scattered outputs land on another GPU?
 * That fraction is the inter-GPU traffic per cell step for the n=27 frontier,
 * whose array cannot live on one GPU.  MARK-split ranking (v1/v4/v5/v6),
 * exact full ranks, every transition of a real sweep, weighted by live inputs.
 * The row-end gather (boundary r <- mid 2r) is local if boundaries scale
 * with the array, so only cell steps are counted. */
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
    const int GS[4] = {2, 8, 64, 512};
    u64 total = 0, cross[4] = {0}, ans = 0;
    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            u64 size_in = fb ? B : S;
            if (!term) memset(nxt, 0, S * 4);
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
                    /* owner of an index: input space has size_in, output space S */
                    total++;
                    for (int g = 0; g < 4; g++) {
                        u64 G = GS[g];
                        if ((x * G) / size_in != (y * G) / S) cross[g]++;
                    }
                }
            }
            if (term) goto done;
            u32 *q = cur; cur = nxt; nxt = q;
        }
        memset(nxt, 0, S * 4); for (u64 r = 0; r < B; r++) nxt[r] = cur[2*r];
        u32 *q = cur; cur = nxt; nxt = q;
    }
done:
    printf("n=%2d  a(n) mod p=%10llu  outputs=%llu  off-GPU share: G=2 %.3f  G=8 %.3f  G=64 %.3f  G=512 %.3f\n",
           n, (unsigned long long)(ans % p), (unsigned long long)total,
           (double)cross[0]/total, (double)cross[1]/total, (double)cross[2]/total, (double)cross[3]/total);
    return 0;
}
