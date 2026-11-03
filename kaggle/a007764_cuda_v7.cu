/* CUDA entry points for v7 (packed residues).  Device code is a007764_v7.h. */

__device__ __forceinline__ void v7_pack(Pack *pk, int K, int b, const u32 *mods)
{
    pk->K = K; pk->b = b; pk->W = K * b; pk->f = 64 / pk->W;
    pk->finv = (1ull << 32) / (u64)pk->f;
    pk->recmask = pk->W == 64 ? ~0ull : ((1ull << pk->W) - 1ull);
    pk->bmask = (1ull << b) - 1ull;
    for (int t = 0; t < V7_KMAX; t++) pk->m[t] = t < K ? mods[t] : 1u;
}

extern "C" __global__ void v7_fast_k(
        const u64 *cur, u64 *nxt, unsigned long long start, unsigned long long size_in, int K, int b,
        const u32 *__restrict__ mods, int i, int j, int n, int fb, int term,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc, u32 *queue, u32 *qcount, u32 qcap)
{
    extern __shared__ u64 sm7[];
    T4 t; Pack pk;
    v5_load_tables(&t, sm7, n, T, M, off, minv);
    v7_pack(&pk, K, b, mods);
    u64 local[V7_KMAX];
    for (int q = 0; q < V7_KMAX; q++) local[q] = 0;
    u64 stride = (u64)gridDim.x * blockDim.x;
    /* one slice [start, size_in) of the input range; the queue is reused per slice */
    for (u64 idx = start + (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride) {
        if (!v7_lane(&t, &pk, cur, nxt, (u32)idx, i, j, n, fb, term, 1, local)) continue;
        unsigned mask = __activemask();
        int lane = threadIdx.x & 31, leader = __ffs(mask) - 1;
        u32 base = 0;
        if (lane == leader) base = atomicAdd(qcount, (u32)__popc(mask));
        base = __shfl_sync(mask, base, leader);
        u32 pos = base + (u32)__popc(mask & ((1u << lane) - 1u));
        if (pos < qcap) queue[pos] = (u32)idx;
        else v7_lane(&t, &pk, cur, nxt, (u32)idx, i, j, n, fb, term, 0, local);
    }
    if (term)
        for (int q = 0; q < K; q++) if (local[q]) atomicAdd(&acc[q], local[q]);
}

extern "C" __global__ void v7_slow_k(
        const u64 *cur, u64 *nxt, int K, int b,
        const u32 *__restrict__ mods, int i, int j, int n, int fb, int term,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc, const u32 *queue, const u32 *qcount, u32 qcap)
{
    extern __shared__ u64 sm7[];
    T4 t; Pack pk;
    v5_load_tables(&t, sm7, n, T, M, off, minv);
    v7_pack(&pk, K, b, mods);
    u64 local[V7_KMAX];
    for (int q = 0; q < V7_KMAX; q++) local[q] = 0;
    u32 cnt = *qcount < qcap ? *qcount : qcap;
    for (u32 q = blockIdx.x * blockDim.x + threadIdx.x; q < cnt; q += gridDim.x * blockDim.x)
        v7_lane(&t, &pk, cur, nxt, queue[q], i, j, n, fb, term, 0, local);
    if (term)
        for (int q = 0; q < K; q++) if (local[q]) atomicAdd(&acc[q], local[q]);
}

extern "C" __global__ void v7_rowend_k(const u64 *cur, u64 *nxt, int K, int b,
                                       const u32 *__restrict__ mods, u32 B, u32 words)
{
    Pack pk;
    v7_pack(&pk, K, b, mods);
    for (u32 w = blockIdx.x * blockDim.x + threadIdx.x; w < words; w += gridDim.x * blockDim.x)
        v7_rowend_word(&pk, cur, nxt, w, B);
}
