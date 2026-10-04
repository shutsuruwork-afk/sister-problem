/* CUDA entry points for v5.  Device code is a007764_v5.h verbatim. */

__device__ __forceinline__ void v5_load_tables(
        T4 *t, u64 *sm, int n, const u32 *T, const u32 *M, const u32 *off, const u64 *minv)
{
    int Ts = n + 3, nT = (n + 1) * Ts, nM = n + 1, nO = n + 2, nI = n + 1;
    u64 *sI = sm;
    u32 *sT = (u32 *)(sm + nI), *sM = sT + nT, *sO = sM + nM;
    for (int x = threadIdx.x; x < nI; x += blockDim.x) sI[x] = minv[x];
    for (int x = threadIdx.x; x < nT; x += blockDim.x) sT[x] = T[x];
    for (int x = threadIdx.x; x < nM; x += blockDim.x) sM[x] = M[x];
    for (int x = threadIdx.x; x < nO; x += blockDim.x) sO[x] = off[x];
    __syncthreads();
    t->T = sT; t->M = sM; t->off = sO; t->minv = sI; t->n = n; t->Ts = Ts;
}

extern "C" __global__ void v5_fast_k(
        const u32 *cur, u32 *nxt, unsigned long long size_in,
        int i, int j, int n, u32 p, int fb, int term,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc, u32 *queue, u32 *qcount, u32 qcap)
{
    extern __shared__ u64 sm5[];
    T4 t;
    v5_load_tables(&t, sm5, n, T, M, off, minv);
    u64 local = 0, stride = (u64)gridDim.x * blockDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride) {
        if (!v5_fast(&t, cur, nxt, idx, i, j, n, p, fb, term, &local)) continue;
        /* warp-aggregated append: one atomic per warp instead of per lane */
        unsigned mask = __activemask();
        int lane = threadIdx.x & 31, leader = __ffs(mask) - 1;
        u32 base = 0;
        if (lane == leader) base = atomicAdd(qcount, (u32)__popc(mask));
        base = __shfl_sync(mask, base, leader);
        u32 pos = base + (u32)__popc(mask & ((1u << lane) - 1u));
        if (pos < qcap) queue[pos] = (u32)idx;
        else v5_slow(&t, cur, nxt, idx, i, j, n, p, fb, term, &local);   /* queue full */
    }
    if (term && local) atomicAdd(acc, local);
}

extern "C" __global__ void v5_slow_k(
        const u32 *cur, u32 *nxt, int i, int j, int n, u32 p, int fb, int term,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc, const u32 *queue, const u32 *qcount, u32 qcap)
{
    extern __shared__ u64 sm5[];
    T4 t;
    v5_load_tables(&t, sm5, n, T, M, off, minv);
    u32 cnt = *qcount < qcap ? *qcount : qcap;
    u64 local = 0;
    for (u32 q = blockIdx.x * blockDim.x + threadIdx.x; q < cnt; q += gridDim.x * blockDim.x)
        v5_slow(&t, cur, nxt, (u64)queue[q], i, j, n, p, fb, term, &local);
    if (term && local) atomicAdd(acc, local);
}
