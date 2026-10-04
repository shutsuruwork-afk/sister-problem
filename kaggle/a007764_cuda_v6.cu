/* CUDA entry points for v6 (K residues per sweep).  Device code is
 * a007764_v6.h verbatim; tables are loaded exactly as in v5. */

__device__ __forceinline__ void v6_planes(Planes *pl, int k, unsigned long long S, const u32 *primes)
{
    pl->k = k; pl->S = S;
    for (int t = 0; t < V6_KMAX; t++) pl->p[t] = t < k ? primes[t] : 1u;
}

extern "C" __global__ void v6_fast_k(
        const u32 *cur, u32 *nxt, unsigned long long size_in, unsigned long long S,
        int k, const u32 *__restrict__ primes,
        int i, int j, int n, int fb, int term,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc, u32 *queue, u32 *qcount, u32 qcap)
{
    extern __shared__ u64 sm6[];
    T4 t; Planes pl;
    v5_load_tables(&t, sm6, n, T, M, off, minv);
    v6_planes(&pl, k, S, primes);
    u64 local[V6_KMAX];
    for (int q = 0; q < V6_KMAX; q++) local[q] = 0;
    u64 stride = (u64)gridDim.x * blockDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride) {
        if (!v6_fast(&t, &pl, cur, nxt, idx, i, j, n, fb, term, local)) continue;
        unsigned mask = __activemask();
        int lane = threadIdx.x & 31, leader = __ffs(mask) - 1;
        u32 base = 0;
        if (lane == leader) base = atomicAdd(qcount, (u32)__popc(mask));
        base = __shfl_sync(mask, base, leader);
        u32 pos = base + (u32)__popc(mask & ((1u << lane) - 1u));
        if (pos < qcap) queue[pos] = (u32)idx;
        else v6_slow(&t, &pl, cur, nxt, idx, i, j, n, fb, term, local);
    }
    if (term)
        for (int q = 0; q < k; q++) if (local[q]) atomicAdd(&acc[q], local[q]);
}

extern "C" __global__ void v6_slow_k(
        const u32 *cur, u32 *nxt, unsigned long long S,
        int k, const u32 *__restrict__ primes,
        int i, int j, int n, int fb, int term,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc, const u32 *queue, const u32 *qcount, u32 qcap)
{
    extern __shared__ u64 sm6[];
    T4 t; Planes pl;
    v5_load_tables(&t, sm6, n, T, M, off, minv);
    v6_planes(&pl, k, S, primes);
    u64 local[V6_KMAX];
    for (int q = 0; q < V6_KMAX; q++) local[q] = 0;
    u32 cnt = *qcount < qcap ? *qcount : qcap;
    for (u32 q = blockIdx.x * blockDim.x + threadIdx.x; q < cnt; q += gridDim.x * blockDim.x)
        v6_slow(&t, &pl, cur, nxt, (u64)queue[q], i, j, n, fb, term, local);
    if (term)
        for (int q = 0; q < k; q++) if (local[q]) atomicAdd(&acc[q], local[q]);
}
