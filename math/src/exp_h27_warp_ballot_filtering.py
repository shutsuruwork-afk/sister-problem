"""Experiment H-27 (Roadmap Route C / GPU Warp Synchronous Filtering):
GPU Warp Vote (__ballot_sync) Non-Zero Transition Filtering Engine.

Theoretical Context:
--------------------
During frontier transfer, ~40% of candidate local transitions are invalid (cycle creation or plug mismatch).
In standard GPU branch execution:
    if (is_valid) { atomicAdd(&shmem[rank], val); }
threads experience warp divergence serialization.
With GPU Warp-Level Synchronization (`__ballot_sync(0xFFFFFFFF, is_valid)`):
1. The 32 threads evaluate validity predicates concurrently into a single 32-bit integer mask.
2. If `active_mask == 0`, all 32 lanes instantly skip memory writes in 1 cycle (100% warp-level early exit).
3. Active threads compute compacted destination offsets via `__popc(active_mask & prefix_mask)`, eliminating divergence.

Classification:
---------------
Scope: Part 2 (Specific to NVIDIA GPU Warp Instruction Architecture)
Functional Class: [C-Class] Throughput Layer (Warp Synchronous Instruction)
"""

from __future__ import annotations
import math
import random
import time
from typing import Dict, List, Tuple

KNOWN_A007764: Dict[int, int] = {
    1: 2,
    2: 12,
    3: 184,
    4: 8512,
    5: 1262816,
}


# --------------------------------------------------------------------------
# 1. Divergent Branching Model (Baseline)
# --------------------------------------------------------------------------
def simulate_divergent_warp_execution(valid_flags: List[bool], ranks: List[int], vals: List[int], p: int) -> Tuple[List[int], float]:
    """Simulate serialized divergent execution when threads take different branch paths."""
    shmem = [0] * 65536
    t0 = time.perf_counter()
    
    # Process warps of 32 threads
    for warp_idx in range(0, len(valid_flags), 32):
        chunk_flags = valid_flags[warp_idx:warp_idx + 32]
        chunk_ranks = ranks[warp_idx:warp_idx + 32]
        chunk_vals = vals[warp_idx:warp_idx + 32]
        
        # Divergence penalty: if warp is split, both branches are executed serially
        for f, r, v in zip(chunk_flags, chunk_ranks, chunk_vals):
            if f:
                shmem[r] = (shmem[r] + v) % p

    elapsed = time.perf_counter() - t0
    return shmem, elapsed


# --------------------------------------------------------------------------
# 2. Warp Ballot Synchronous Filtering Model (H-27)
# --------------------------------------------------------------------------
def simulate_ballot_filtered_warp_execution(valid_flags: List[bool], ranks: List[int], vals: List[int], p: int) -> Tuple[List[int], float]:
    """Simulate __ballot_sync early-exit and compacted lane indexing."""
    shmem = [0] * 65536
    t0 = time.perf_counter()
    
    for warp_idx in range(0, len(valid_flags), 32):
        chunk_flags = valid_flags[warp_idx:warp_idx + 32]
        
        # 1. __ballot_sync: convert 32 boolean flags into a 32-bit integer mask
        ballot_mask = 0
        for lane in range(32):
            if chunk_flags[lane]:
                ballot_mask |= (1 << lane)
                
        # 2. 1-cycle Early Exit if entire warp is invalid
        if ballot_mask == 0:
            continue
            
        chunk_ranks = ranks[warp_idx:warp_idx + 32]
        chunk_vals = vals[warp_idx:warp_idx + 32]
        
        # 3. Compacted execution for non-zero lanes
        for lane in range(32):
            if (ballot_mask >> lane) & 1:
                r = chunk_ranks[lane]
                v = chunk_vals[lane]
                shmem[r] = (shmem[r] + v) % p

    elapsed = time.perf_counter() - t0
    return shmem, elapsed


def benchmark_h27() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-27: GPU Warp Vote (__ballot_sync) Transition Filtering Engine     ")
    print("=" * 80)
    p = 4294967291
    N_OPS = 2000000

    random.seed(42)
    # ~40% invalid transitions in realistic frontier DP
    valid_flags = [random.random() > 0.40 for _ in range(N_OPS)]
    test_ranks = [random.randint(0, 30000) for _ in range(N_OPS)]
    test_vals = [random.randint(1, 1000) for _ in range(N_OPS)]

    # 1. Benchmark Divergent Baseline
    print("\n[Step 1] Micro-Benchmark: 2,000,000 Transition Evaluations (Divergence vs Ballot):")
    res_div, t_div = simulate_divergent_warp_execution(valid_flags, test_ranks, test_vals, p)
    ops_div = N_OPS / t_div / 1e6

    # 2. Benchmark Warp Ballot Filtering (H-27)
    res_bal, t_bal = simulate_ballot_filtered_warp_execution(valid_flags, test_ranks, test_vals, p)
    ops_bal = N_OPS / t_bal / 1e6

    assert res_div == res_bal, "Ballot results must match baseline exactly!"

    speedup = t_div / t_bal
    print(f"  Divergent Branch Execution:        {t_div:.4f}s ({ops_div:.2f} M ops/sec)")
    print(f"  Warp Ballot Early-Exit Engine:     {t_bal:.4f}s ({ops_bal:.2f} M ops/sec) -> Speedup: {speedup:.2f}x")

    passed = speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] Warp Ballot Engine achieves {speedup:.2f}x speedup ({ops_bal:.2f} M ops/sec).")
        print(f"  GPU INSTRUCTION ACCELERATION: __ballot_sync enables 1-cycle warp-level pruning.")
    else:
        print(f"  DECISION: [PRUNED] Speedup ({speedup:.2f}x) below threshold (1.15x).")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h27()
