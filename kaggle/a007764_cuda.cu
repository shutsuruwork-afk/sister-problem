/* CUDA kernels for A007764.  The device functions above this point are
 * a007764_kernel.h verbatim -- the exact code validated on CPU against the
 * twelve known OEIS terms. */

extern "C" {

__device__ __forceinline__ void atomic_add_mod(u32 *addr, u32 v, u32 p)
{
    u32 old = *addr, assumed;
    do {
        assumed = old;
        u32 nv = assumed + v;
        if (nv >= p) nv -= p;
        old = atomicCAS(addr, assumed, nv);
    } while (assumed != old);
}

/* Cooperative load of the (tiny) Motzkin tables into shared memory. */
__device__ __forceinline__ void load_tables(
        Tables *tb, u64 *smem, const u64 *T, const u64 *M, const u64 *off,
        int n, int Tstride)
{
    int Trows = n + 5, nT = Trows * Tstride, nM = n + 5, nO = n + 2;
    u64 *sT = smem, *sM = smem + nT, *sO = smem + nT + nM;
    for (int t = threadIdx.x; t < nT; t += blockDim.x) sT[t] = T[t];
    for (int t = threadIdx.x; t < nM; t += blockDim.x) sM[t] = M[t];
    for (int t = threadIdx.x; t < nO; t += blockDim.x) sO[t] = off[t];
    __syncthreads();
    tb->T = sT; tb->M = sM; tb->off = sO; tb->n = n; tb->Tstride = Tstride;
}

/* One vertex of the sweep: cur (size_in) -> nxt (2*B(n)). */
__global__ void dp_step(
        const u32 *__restrict__ cur, u32 *nxt,
        unsigned long long size_in, int i, int j, int n, u32 p,
        int from_boundary,
        const u64 *__restrict__ T, const u64 *__restrict__ M,
        const u64 *__restrict__ off, int Tstride)
{
    extern __shared__ u64 smem[];
    Tables tb;
    load_tables(&tb, smem, T, M, off, n, Tstride);

    u64 stride = (u64)blockDim.x * gridDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x;
         idx < size_in; idx += stride) {
        u32 v = cur[idx];
        if (!v) continue;
        u64 s = word_before(idx, j, from_boundary, &tb);
        u64 out[2];
        int c = cell_successors(s, i, j, n, out);
        for (int t = 0; t < c; t++) {
            u64 u; u32 b;
            if (word_contract(out[t], j, &u, &b)) continue;   /* unreachable */
            atomic_add_mod(&nxt[2 * profile_rank(u, &tb) + b], v, p);
        }
    }
}

/* End of row: the contraction sits at (n, n+1) with bit 0, so the next
 * boundary rank is exactly idx >> 1.  Pure gather, no atomics. */
__global__ void row_end(const u32 *__restrict__ cur, u32 *__restrict__ out,
                        unsigned long long B)
{
    u64 stride = (u64)blockDim.x * gridDim.x;
    for (u64 r = (u64)blockIdx.x * blockDim.x + threadIdx.x; r < B; r += stride)
        out[r] = cur[2 * r];
}

/* Terminal vertex (n,n): the MARK is consumed and the frontier must empty. */
__global__ void terminal_sum(
        const u32 *__restrict__ cur, unsigned long long *acc,
        unsigned long long size_in, int n, int from_boundary,
        const u64 *__restrict__ T, const u64 *__restrict__ M,
        const u64 *__restrict__ off, int Tstride)
{
    extern __shared__ u64 smem[];
    Tables tb;
    load_tables(&tb, smem, T, M, off, n, Tstride);

    unsigned long long local = 0;
    u64 stride = (u64)blockDim.x * gridDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x;
         idx < size_in; idx += stride) {
        u32 v = cur[idx];
        if (!v) continue;
        u64 s = word_before(idx, n, from_boundary, &tb);
        u64 out[2];
        int c = cell_successors(s, n, n, n, out);
        for (int t = 0; t < c; t++)
            if (out[t] == 0ull) local += v;
    }
    if (local) atomicAdd(acc, local);
}

}  /* extern "C" */
