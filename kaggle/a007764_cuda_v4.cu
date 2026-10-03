/* CUDA entry point for v4.  Device code is a007764_v4.h verbatim.
 * dry = 1 turns the launch into the bottleneck probe (no scatter). */

extern "C" __global__ void v4_step(
        const u32 *cur, u32 *nxt, unsigned long long size_in,
        int i, int j, int n, u32 p, int fb, int term, int dry,
        const u32 *__restrict__ T, const u32 *__restrict__ M,
        const u32 *__restrict__ off, const u64 *__restrict__ minv,
        unsigned long long *acc)
{
    extern __shared__ u64 sm4[];
    int Ts = n + 3, nT = (n + 1) * Ts, nM = n + 1, nO = n + 2, nI = n + 1;
    u64 *sI = sm4;
    u32 *sT = (u32 *)(sm4 + nI), *sM = sT + nT, *sO = sM + nM;
    for (int x = threadIdx.x; x < nI; x += blockDim.x) sI[x] = minv[x];
    for (int x = threadIdx.x; x < nT; x += blockDim.x) sT[x] = T[x];
    for (int x = threadIdx.x; x < nM; x += blockDim.x) sM[x] = M[x];
    for (int x = threadIdx.x; x < nO; x += blockDim.x) sO[x] = off[x];
    __syncthreads();
    T4 t; t.T = sT; t.M = sM; t.off = sO; t.minv = sI; t.n = n; t.Ts = Ts;

    u64 local = 0, stride = (u64)gridDim.x * blockDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride)
        v4_index(&t, cur, nxt, idx, i, j, n, p, fb, term, dry, &local);
    if (dry) { if (local == 0x9e3779b97f4a7c15ull) acc[0] = local; }
    else if (term && local) atomicAdd(acc, local);
}
