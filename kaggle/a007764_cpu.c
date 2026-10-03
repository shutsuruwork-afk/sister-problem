/* a007764_cpu.c -- CPU/OpenMP driver for the v2 sweep.
 *
 * Same chunked decomposition as the CUDA launch (one odometer per chunk,
 * atomic modular scatter), so running it with several threads and small
 * chunks exercises exactly the boundary and race conditions the GPU sees.
 *
 *   gcc -O3 -march=native -fopenmp -o a007764_cpu a007764_cpu.c
 *   ./a007764_cpu N [P] [CHUNK]          -> prints "n p residue seconds"
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "a007764_kernel.h"
#include "a007764_v2.h"

static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

static u64 *build_ca(int n)
{
    int L = n + 1;
    u64 *Ca = calloc((size_t)(L + 1) * (L + 2) * 2, sizeof(u64));
    Auto a = { Ca, L };
    ((u64 *)a.Ca)[((size_t)0 * (L + 2) + 0) * 2 + 1] = 1;
    for (int rem = 1; rem <= L; rem++)
        for (int d = 0; d <= L; d++)
            for (int m = 0; m < 2; m++) {
                u64 v = 0; int nd, nm;
                for (u32 c = 0; c < 4; c++)
                    if (auto_step(c, d, m, L, &nd, &nm)) v += CA_AT(&a, rem - 1, nd, nm);
                Ca[((size_t)rem * (L + 2) + d) * 2 + m] = v;
            }
    return Ca;
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s N [P] [CHUNK]\n", argv[0]); return 2; }
    int n = atoi(argv[1]);
    u32 p = argc > 2 ? (u32)strtoul(argv[2], 0, 10) : 2147483629u;
    u64 chunk = argc > 3 ? strtoull(argv[3], 0, 10) : 64;
    if (n < 1 || n > 29) { fprintf(stderr, "n out of range\n"); return 2; }

    int L = n + 1;
    u64 *Ca = build_ca(n);
    Auto a = { Ca, L };
    u64 B = CA_AT(&a, L, 0, 0), S = 2 * B;
    u32 *cur = calloc(S, sizeof(u32)), *nxt = calloc(S, sizeof(u32));
    if (!cur || !nxt) { fprintf(stderr, "allocation of %llu bytes failed\n", (unsigned long long)(8 * S)); return 1; }

    double t0 = now();
    u64 r0 = auto_rank(&a, (u64)A_MARK);        /* (0,0) emits MARK down / right */
    cur[2 * r0] = 1; cur[2 * r0 + 1] = 1;
    u64 answer = 0;

    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            if (!term) memset(nxt, 0, S * sizeof(u32));
            long long nchunks = (long long)((B + chunk - 1) / chunk);
            u64 tacc = 0;
            #pragma omp parallel for schedule(dynamic, 64) reduction(+:tacc)
            for (long long c = 0; c < nchunks; c++) {
                u64 lo = (u64)c * chunk, hi = lo + chunk, local = 0;
                if (hi > B) hi = B;
                v2_chunk(&a, cur, nxt, lo, hi, i, j, n, p, fb, term, &local);
                tacc += local;
            }
            if (term) { answer = tacc % p; goto done; }
            u32 *t = cur; cur = nxt; nxt = t;
        }
        memset(nxt, 0, S * sizeof(u32));
        for (u64 r = 0; r < B; r++) nxt[r] = cur[2 * r];
        u32 *t = cur; cur = nxt; nxt = t;
    }
done:
    printf("%d %u %llu %.3f\n", n, p, (unsigned long long)answer, now() - t0);
    free(cur); free(nxt); free(Ca);
    return 0;
}
