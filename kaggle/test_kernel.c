#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "a007764_kernel.h"

static u64 *Tt, *Mm, *Off; static int Tstride;

static void build_tables(int n) {
    int kmax = n + 4; Tstride = n + 6;
    Tt  = calloc((size_t)(kmax + 1) * Tstride, sizeof(u64));
    Mm  = calloc(kmax + 1, sizeof(u64));
    Off = calloc(n + 2, sizeof(u64));
    Tt[0 * Tstride + 0] = 1;
    for (int rem = 1; rem <= kmax; rem++)
        for (int d = 0; d <= kmax; d++) {
            u64 v = Tt[(rem-1)*Tstride + d] + Tt[(rem-1)*Tstride + d + 1];
            if (d > 0) v += Tt[(rem-1)*Tstride + d - 1];
            Tt[rem*Tstride + d] = v;
        }
    for (int k = 0; k <= kmax; k++) Mm[k] = Tt[k*Tstride + 0];
    u64 acc = 0;
    for (int a = 0; a <= n; a++) { Off[a] = acc; acc += Mm[a] * Mm[n - a]; }
    Off[n + 1] = acc;
}

int main(int argc, char **argv) {
    int nlo = atoi(argv[1]), nhi = atoi(argv[2]);
    u32 p = 4294967291u > 2147483647u ? 2147483629u : 2147483629u; /* < 2^31 */
    for (int n = nlo; n <= nhi; n++) {
        build_tables(n);
        Tables tb = { Tt, Mm, Off, n, Tstride };
        u64 B = Off[n + 1], size = 2 * B;
        u32 *cur = calloc(size, sizeof(u32)), *nxt = calloc(size, sizeof(u32));
        if (!cur || !nxt) { printf("alloc fail n=%d\n", n); return 1; }
        u64 out[2], u; u32 bb;
        int c = cell_successors(0ull, 0, 0, n, out);
        for (int t = 0; t < c; t++) {
            if (word_contract(out[t], 0, &u, &bb)) { printf("contract fail\n"); return 1; }
            cur[2 * profile_rank(u, &tb) + bb] += 1;
        }
        u64 peak = 0, answer = 0;
        for (int i = 0; i <= n; i++) {
            for (int j = (i == 0 ? 1 : 0); j <= n; j++) {
                int fb = (j == 0);
                if (i == n && j == n) {
                    for (u64 idx = 0; idx < size; idx++) {
                        u32 v = cur[idx]; if (!v) continue;
                        u64 s = word_before(idx, j, fb, &tb);
                        int cc = cell_successors(s, i, j, n, out);
                        for (int t = 0; t < cc; t++)
                            if (out[t] == 0ull) answer = (answer + v) % p;
                    }
                    goto done;
                }
                memset(nxt, 0, size * sizeof(u32));
                u64 live = 0;
                for (u64 idx = 0; idx < size; idx++) {
                    u32 v = cur[idx]; if (!v) continue;
                    live++;
                    u64 s = word_before(idx, j, fb, &tb);
                    int cc = cell_successors(s, i, j, n, out);
                    for (int t = 0; t < cc; t++) {
                        if (word_contract(out[t], j, &u, &bb)) { printf("bad plug n=%d i=%d j=%d\n",n,i,j); return 1; }
                        u64 k = 2 * profile_rank(u, &tb) + bb;
                        u32 s2 = nxt[k] + v; if (s2 >= p) s2 -= p; nxt[k] = s2;
                    }
                }
                if (live > peak) peak = live;
                u32 *tmp = cur; cur = nxt; nxt = tmp;
            }
            for (u64 idx = 0; idx < size; idx++) nxt[idx] = 0;
            for (u64 idx = 0; idx < size; idx += 2) nxt[idx >> 1] = cur[idx];
            u32 *tmp = cur; cur = nxt; nxt = tmp;
        }
    done:
        printf("  n=%2d  2B(n)=%-14llu peak_live=%-14llu occ=%.4f  a(n) mod p = %llu\n",
               n, (unsigned long long)size, (unsigned long long)peak,
               (double)peak / (double)size, (unsigned long long)answer);
        free(cur); free(nxt); free(Tt); free(Mm); free(Off);
    }
    return 0;
}
