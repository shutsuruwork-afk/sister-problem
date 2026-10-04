/* r08: which lanes would a two-kernel design have to defer?
 *  partner : both plugs occupied and not a cycle -> cell_successors scans for
 *            bracket partners (O(n)) and the output rank is a full rank
 *  markmv  : no partner scan, but some output moves the MARK -> full rank
 *  fast    : neither; O(1) local rank for every output
 * Reported per live lane and per 32-lane warp (consecutive indices, as on a
 * GPU).  Uses the validated v4 device code; the answer is checked too. */
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
    u32 *cur = calloc(S, 4), *nxt = calloc(S, 4); unsigned char *cls = calloc(S, 1);
    cur[0] = cur[1] = 1;
    u64 lane[3] = {0}, warps = 0, w_partner = 0, w_mark = 0, w_any = 0, ans = 0;
    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            u64 size_in = fb ? B : S;
            if (!term) memset(nxt, 0, S * 4);
            for (u64 x = 0; x < size_in; x++) {
                cls[x] = 255;
                if (!cur[x]) continue;
                u64 tacc = 0;
                if (!fb && !term) {                          /* classify */
                    u32 r = (u32)(x >> 1), b = (u32)(x & 1); int dw = 0, a = 0;
                    u64 u = prof_unrank4(r, &t, j - 1, &dw, &a), s = word_expand(u, b, j - 1), out[2];
                    u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
                    int partner = Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE), mark = 0;
                    int k = cell_successors(s, i, j, n, out);
                    for (int q = 0; q < k && !partner; q++) {
                        u64 u2; u32 b2; word_contract(out[q], j, &u2, &b2);
                        if (slot_get(u2, a) != A_MARK) mark = 1;
                    }
                    cls[x] = partner ? 0 : mark ? 1 : 2;
                    lane[cls[x]]++;
                }
                v4_index(&t, cur, nxt, x, i, j, n, p, fb, term, 0, &tacc);
                ans += tacc;
            }
            if (!fb && !term)
                for (u64 w = 0; w < size_in; w += 32) {
                    int live = 0, hp = 0, hm = 0;
                    for (u64 x = w; x < w + 32 && x < size_in; x++)
                        if (cls[x] != 255) { live = 1; hp |= cls[x] == 0; hm |= cls[x] == 1; }
                    if (live) { warps++; w_partner += hp; w_mark += hm; w_any += hp | hm; }
                }
            if (term) goto done;
            u32 *q = cur; cur = nxt; nxt = q;
        }
        memset(nxt, 0, S * 4); for (u64 r = 0; r < B; r++) nxt[r] = cur[2*r];
        u32 *q = cur; cur = nxt; nxt = q;
    }
done:;
    double L = (double)(lane[0] + lane[1] + lane[2]);
    printf("n=%2d  a(n) mod p=%10llu | lanes: partner %.3f  mark-move %.3f  fast %.3f | "
           "warps with a partner lane %.3f, a mark-move lane %.3f, either %.3f\n",
           n, (unsigned long long)(ans % p), lane[0] / L, lane[1] / L, lane[2] / L,
           (double)w_partner / warps, (double)w_mark / warps, (double)w_any / warps);
    return 0;
}
