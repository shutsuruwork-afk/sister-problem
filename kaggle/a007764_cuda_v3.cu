/* CUDA entry point for v3.  Device code is a007764_v3.h verbatim. */

extern "C" __global__ void v3_step(
        const u32 *cur, u32 *nxt, unsigned long long size_in,
        int i, int j, int n, u32 p, int fb, int term,
        const u64 *__restrict__ Ca, unsigned long long *acc)
{
    extern __shared__ u64 sCa3[];
    int L = n + 1, nC = (L + 1) * (L + 2) * 2;
    for (int t = threadIdx.x; t < nC; t += blockDim.x) sCa3[t] = Ca[t];
    __syncthreads();
    Auto a; a.Ca = sCa3; a.L = L;

    u64 local = 0, stride = (u64)gridDim.x * blockDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride)
        v3_index(&a, cur, nxt, idx, i, j, n, p, fb, term, &local);
    if (term && local) atomicAdd(acc, local);
}
