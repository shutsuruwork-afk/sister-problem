/* Bottleneck probes: the exact per-index work of v1 / v3 with the scatter
 * replaced by an XOR into a register.  Every index is treated as live (all
 * indices are valid states, the ranking being a bijection).  Comparing a
 * full sweep of probes with a real sweep splits time into compute versus
 * memory + atomics. */

extern "C" __global__ void probe_v1(
        unsigned long long size_in, int i, int j, int n, int fb,
        const u64 *__restrict__ T, const u64 *__restrict__ M,
        const u64 *__restrict__ off, int Tstride, unsigned long long *sink)
{
    extern __shared__ u64 smem[];
    Tables tb;
    load_tables(&tb, smem, T, M, off, n, Tstride);
    u64 x = 0, stride = (u64)gridDim.x * blockDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride) {
        u64 s = word_before(idx, j, fb, &tb), out[2], u; u32 b;
        int k = cell_successors(s, i, j, n, out);
        for (int t = 0; t < k; t++)
            if (!word_contract(out[t], j, &u, &b)) x ^= 2 * profile_rank(u, &tb) + b + (u64)t;
    }
    if (x == 0x9e3779b97f4a7c15ull) sink[0] = x;        /* defeats dead-code elimination */
}

extern "C" __global__ void probe_v3(
        unsigned long long size_in, int i, int j, int n, int fb,
        const u64 *__restrict__ Ca, unsigned long long *sink)
{
    extern __shared__ u64 sCa3[];
    int L = n + 1, nC = (L + 1) * (L + 2) * 2;
    for (int t = threadIdx.x; t < nC; t += blockDim.x) sCa3[t] = Ca[t];
    __syncthreads();
    Auto a; a.Ca = sCa3; a.L = L;
    u64 x = 0, stride = (u64)gridDim.x * blockDim.x;
    for (u64 idx = (u64)blockIdx.x * blockDim.x + threadIdx.x; idx < size_in; idx += stride) {
        u64 r = fb ? idx : (idx >> 1);
        u32 b = fb ? 0u : (u32)(idx & 1ull);
        unsigned st = 0;
        u64 u = auto_unrank_at(&a, r, fb ? -1 : j - 1, &st);
        u64 s = fb ? (u << 2) : word_expand(u, b, j - 1);
        u32 Lp = slot_get(s, j), Up = slot_get(s, j + 1);
        int isjoin = Lp && Up && !(Lp == A_OPEN && Up == A_CLOSE);
        u64 out[2];
        int k = cell_successors(s, i, j, n, out);
        for (int t = 0; t < k; t++) {
            u64 u2 = 0; u32 b2 = 0;
            if (word_contract(out[t], j, &u2, &b2)) continue;
            u64 ro = isjoin ? auto_rank(&a, u2)
                   : fb ? r
                   : r - auto_local2(&a, u, j - 1, st) + auto_local2(&a, u2, j - 1, st);
            x ^= 2 * ro + b2 + (u64)t;
        }
    }
    if (x == 0x9e3779b97f4a7c15ull) sink[0] = x;
}
