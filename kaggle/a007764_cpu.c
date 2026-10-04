/* a007764_cpu.c -- CPU/OpenMP driver for the v2 and v3 sweeps.
 *
 * Same chunked decomposition as the CUDA launch (one odometer per chunk,
 * atomic modular scatter), so running it with several threads and small
 * chunks exercises exactly the boundary and race conditions the GPU sees.
 *
 *   gcc -O3 -march=native -fopenmp -o a007764_cpu a007764_cpu.c
 *   ./a007764_cpu N [P] [CHUNK] [v2|v3|v4|v5] [QFRAC]  -> prints "n p residue seconds"
 * v3, v4 and v5 ignore CHUNK: one index per iteration, like a GPU thread.
 * v5 runs a fast pass that queues arc-joining lanes, then a slow pass over the
 * queue; QFRAC (default 0.30) is the queue capacity as a fraction of the
 * input, and lanes beyond it are processed inline -- QFRAC=0 tests that path.
 * Build with -DV4_STATS to also print how often v4 takes each rank path.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "a007764_kernel.h"
#include "a007764_v2.h"
#include "a007764_v3.h"
#include "a007764_v4.h"
#include "a007764_v5.h"

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
    if (argc < 2) { fprintf(stderr, "usage: %s N [P] [CHUNK] [v2|v3|v4|v5] [QFRAC]\n", argv[0]); return 2; }
    int n = atoi(argv[1]);
    u32 p = argc > 2 ? (u32)strtoul(argv[2], 0, 10) : 2147483629u;
    u64 chunk = argc > 3 ? strtoull(argv[3], 0, 10) : 64;
    int v3 = argc > 4 && strcmp(argv[4], "v3") == 0;
    int v5 = argc > 4 && strcmp(argv[4], "v5") == 0;
    int v4 = (argc > 4 && strcmp(argv[4], "v4") == 0) || v5;
    double qfrac = argc > 5 ? atof(argv[5]) : 0.30;
    if (v4 && n > 22) { fprintf(stderr, "v4/v5 need n <= 22 (32-bit ranks)\n"); return 2; }
    if (n < 1 || n > 29) { fprintf(stderr, "n out of range\n"); return 2; }

    int L = n + 1;
    u64 *Ca = build_ca(n);
    Auto a = { Ca, L };
    u64 B = CA_AT(&a, L, 0, 0), S = 2 * B;

    /* v4 tables: 32-bit Motzkin completions, offsets, reciprocals */
    int Ts4 = n + 3;
    u64 *Tw = calloc((size_t)(n + 1) * (n + 6), sizeof(u64));
    Tw[0] = 1;
    for (int rem = 1; rem <= n; rem++)
        for (int d = 0; d <= n + 3; d++) {
            u64 v = Tw[(size_t)(rem - 1) * (n + 6) + d] + Tw[(size_t)(rem - 1) * (n + 6) + d + 1];
            if (d) v += Tw[(size_t)(rem - 1) * (n + 6) + d - 1];
            Tw[(size_t)rem * (n + 6) + d] = v;
        }
    u32 *T32 = calloc((size_t)(n + 1) * Ts4, sizeof(u32)), *M32 = calloc(n + 1, sizeof(u32)),
        *O32 = calloc(n + 2, sizeof(u32));
    u64 *minv = calloc(n + 1, sizeof(u64));
    for (int rem = 0; rem <= n; rem++)
        for (int d = 0; d < Ts4; d++) T32[rem * Ts4 + d] = (u32)Tw[(size_t)rem * (n + 6) + d];
    for (int k = 0; k <= n; k++) { M32[k] = (u32)Tw[(size_t)k * (n + 6)]; minv[k] = (1ull << 32) / M32[k]; }
    { u64 acc = 0; for (int x = 0; x <= n; x++) { O32[x] = (u32)acc; acc += (u64)M32[x] * M32[n - x]; } O32[n + 1] = (u32)acc; }
    T4 t4 = { T32, M32, O32, minv, n, Ts4 };
    u64 qcap = (u64)(qfrac * (double)S);
    u32 *queue = v5 ? calloc(qcap + 1, sizeof(u32)) : NULL;
#ifdef V4_STATS
    u64 st_local = 0, st_mark = 0, st_join = 0;
#endif
    u32 *cur = calloc(S, sizeof(u32)), *nxt = calloc(S, sizeof(u32));
    if (!cur || !nxt) { fprintf(stderr, "allocation of %llu bytes failed\n", (unsigned long long)(8 * S)); return 1; }

    double t0 = now();
    /* (0,0) emits MARK down / right; the profile M0..0 has a different rank
     * under v4's MARK-split ranking (0) than under the v2/v3 automaton */
    u64 r0 = v4 ? (u64)prof_rank4((u64)A_MARK, &t4) : auto_rank(&a, (u64)A_MARK);
    cur[2 * r0] = 1; cur[2 * r0 + 1] = 1;
    u64 answer = 0;

    for (int i = 0; i <= n; i++) {
        for (int j = (i ? 0 : 1); j <= n; j++) {
            int fb = (j == 0), term = (i == n && j == n);
            if (!term) memset(nxt, 0, S * sizeof(u32));
            u64 tacc = 0;
            if (v5) {
                long long size_in = (long long)(fb ? B : S);
                u32 qcount = 0;
                #pragma omp parallel for schedule(static) reduction(+:tacc)
                for (long long x = 0; x < size_in; x++) {
                    u64 local = 0;
                    if (v5_fast(&t4, cur, nxt, (u64)x, i, j, n, p, fb, term, &local)) {
                        u32 pos = __atomic_fetch_add(&qcount, 1u, __ATOMIC_RELAXED);
                        if (pos < qcap) queue[pos] = (u32)x;
                        else v5_slow(&t4, cur, nxt, (u64)x, i, j, n, p, fb, term, &local);
                    }
                    tacc += local;
                }
                long long cnt = qcount < qcap ? (long long)qcount : (long long)qcap;
                #pragma omp parallel for schedule(static) reduction(+:tacc)
                for (long long q = 0; q < cnt; q++) {
                    u64 local = 0;
                    v5_slow(&t4, cur, nxt, (u64)queue[q], i, j, n, p, fb, term, &local);
                    tacc += local;
                }
            } else if (v4) {
                long long size_in = (long long)(fb ? B : S);
#ifdef V4_STATS
                #pragma omp parallel for schedule(static) reduction(+:tacc,st_local,st_mark,st_join)
#else
                #pragma omp parallel for schedule(static) reduction(+:tacc)
#endif
                for (long long x = 0; x < size_in; x++) {
                    u64 local = 0;
                    v4_index(&t4, cur, nxt, (u64)x, i, j, n, p, fb, term, 0, &local
#ifdef V4_STATS
                             , &st_local, &st_mark, &st_join
#endif
                             );
                    tacc += local;
                }
            } else if (v3) {
                long long size_in = (long long)(fb ? B : S);
                #pragma omp parallel for schedule(static) reduction(+:tacc)
                for (long long x = 0; x < size_in; x++) {
                    u64 local = 0;
                    v3_index(&a, cur, nxt, (u64)x, i, j, n, p, fb, term, &local);
                    tacc += local;
                }
            } else {
                long long nchunks = (long long)((B + chunk - 1) / chunk);
                #pragma omp parallel for schedule(dynamic, 64) reduction(+:tacc)
                for (long long c = 0; c < nchunks; c++) {
                    u64 lo = (u64)c * chunk, hi = lo + chunk, local = 0;
                    if (hi > B) hi = B;
                    v2_chunk(&a, cur, nxt, lo, hi, i, j, n, p, fb, term, &local);
                    tacc += local;
                }
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
#ifdef V4_STATS
    if (v4) {
        double tot = (double)(st_local + st_mark + st_join);
        printf("v4 output ranks: local O(1) %.3f  MARK moved %.3f  partner rewrite %.3f\n",
               st_local / tot, st_mark / tot, st_join / tot);
    }
#endif
    free(cur); free(nxt); free(Ca);
    return 0;
}
