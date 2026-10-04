/* r07: how often does a 32-lane warp contain at least one lane that needs
 * the slow (full) output rank in v4?
 *
 * GPU lanes of a warp take consecutive indices (grid-stride launch), and a
 * warp runs every branch any of its lanes takes.  If nearly every warp has a
 * slow lane, the O(1) fast path saves nothing on a GPU even though it saves
 * a lot on a CPU -- which would explain v4 = 1.03x v1 on the GTX 1660 SUPER.
 * Sequential sweep with the validated v4 device code; per-index slow flags
 * are grouped into blocks of 32 consecutive live-or-not indices. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define V4_STATS 1
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
    u32 *cur = calloc(S, 4), *nxt = calloc(S, 4); unsigned char *slow = calloc(S, 1), *live = calloc(S, 1);
    cur[0] = cur[1] = 1;
    u64 lanes_live = 0, lanes_slow = 0, warps_live = 0, warps_slow = 0, ans = 0;
    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            u64 size_in = fb ? B : S;
            if (!term) memset(nxt, 0, S * 4);
            for (u64 x = 0; x < size_in; x++) {
                u64 l = 0, mk = 0, jn = 0, tacc = 0;
                live[x] = cur[x] != 0;
                v4_index(&t, cur, nxt, x, i, j, n, p, fb, term, 0, &tacc, &l, &mk, &jn);
                ans += tacc;
                slow[x] = (mk + jn) > 0;
            }
            if (!term) {
                for (u64 w = 0; w < size_in; w += 32) {
                    int any_live = 0, any_slow = 0;
                    for (u64 x = w; x < w + 32 && x < size_in; x++) {
                        if (live[x]) { any_live = 1; lanes_live++; if (slow[x]) { any_slow = 1; lanes_slow++; } }
                    }
                    warps_live += any_live; warps_slow += any_slow;
                }
            }
            if (term) goto done;
            u32 *q = cur; cur = nxt; nxt = q;
        }
        memset(nxt, 0, S * 4); for (u64 r = 0; r < B; r++) nxt[r] = cur[2*r];
        u32 *q = cur; cur = nxt; nxt = q;
    }
done:
    printf("n=%2d  a(n) mod p=%llu  live lanes needing a slow rank: %.3f   "
           "live warps with >=1 slow lane: %.4f   (independent-lane estimate %.4f)\n",
           n, (unsigned long long)(ans % p), (double)lanes_slow / lanes_live,
           (double)warps_slow / warps_live,
           1.0 - __builtin_pow(1.0 - (double)lanes_slow / lanes_live, 32));
    return 0;
}
