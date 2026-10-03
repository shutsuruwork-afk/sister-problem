/* CUDA entry point for the v2 (incremental-ranking) sweep.  Device code is
 * a007764_v2.h verbatim, validated on CPU by a007764_cpu.c. */

extern "C" __global__ void v2_step(
        const u32 *cur, u32 *nxt, unsigned long long B, unsigned long long chunk,
        int i, int j, int n, u32 p, int fb, int term,
        const u64 *__restrict__ Ca, unsigned long long *acc)
{
    extern __shared__ u64 sCa[];
    int L = n + 1, nC = (L + 1) * (L + 2) * 2;
    for (int t = threadIdx.x; t < nC; t += blockDim.x) sCa[t] = Ca[t];
    __syncthreads();
    Auto a; a.Ca = sCa; a.L = L;

    u64 nchunks = (B + chunk - 1) / chunk, local = 0;
    u64 stride = (u64)gridDim.x * blockDim.x;
    for (u64 c = (u64)blockIdx.x * blockDim.x + threadIdx.x; c < nchunks; c += stride) {
        u64 r0 = c * chunk, r1 = r0 + chunk;
        if (r1 > B) r1 = B;
        v2_chunk(&a, cur, nxt, r0, r1, i, j, n, p, fb, term, &local);
    }
    if (term && local) atomicAdd(acc, local);
}
