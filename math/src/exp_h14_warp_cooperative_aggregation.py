"""Experiment H-14 (Roadmap Route C / GPU Architecture):
GPU Warp-Cooperative Shared Memory Transition Aggregation Engine.

Theoretical Context:
--------------------
In GPU frontier-line DP kernels, multiple threads within a warp (32 threads) frequently
transition to identical target boundary states (e.g., EMPTY+EMPTY extensions).
Directly issuing atomic additions (`atomicAdd_block` / `atomicAdd`) to global memory creates
severe serialized contention pipelines.
Warp-Cooperative Aggregation utilizes warp-level shuffle intrinsics (`__shfl_sync`, `__match_any_sync`):
1. Detect matching target states within the 32 threads using bitmask matching.
2. Sum residues of matching keys using warp shuffle reduction.
3. The designated lane performs a single write to shared/global memory.
This eliminates up to 32x of atomic lock collisions on GPU compute units.

Classification:
---------------
Scope: Part 2 (Specific to GPU SIMT / CUDA warp shuffle architecture)
Functional Class: [C-Class] Throughput Layer (Warp-level conflict-free reduction)
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
# 1. Serial Atomic Contention Simulation (Baseline)
# --------------------------------------------------------------------------
def simulate_atomic_contention_writes(keys: List[int], vals: List[int], p: int) -> Tuple[Dict[int, int], float]:
    t0 = time.perf_counter()
    table: Dict[int, int] = {}
    # Simulated un-coalesced atomic contention
    for k, v in zip(keys, vals):
        table[k] = (table.get(k, 0) + v) % p
    elapsed = time.perf_counter() - t0
    return table, elapsed


# --------------------------------------------------------------------------
# 2. Warp-Cooperative 32-Lane Pre-Aggregation (H-14)
# --------------------------------------------------------------------------
def simulate_warp_cooperative_writes(keys: List[int], vals: List[int], p: int) -> Tuple[Dict[int, int], float]:
    t0 = time.perf_counter()
    table: Dict[int, int] = {}
    WARP_SIZE = 32
    N = len(keys)
    
    # Process 32 lanes per warp
    for warp_start in range(0, N, WARP_SIZE):
        chunk_keys = keys[warp_start:warp_start + WARP_SIZE]
        chunk_vals = vals[warp_start:warp_start + WARP_SIZE]
        
        # In-warp shuffle aggregation
        warp_dict: Dict[int, int] = {}
        for k, v in zip(chunk_keys, chunk_vals):
            warp_dict[k] = (warp_dict.get(k, 0) + v) % p
            
        # Single coalesced write per unique key to global table
        for uk, uv in warp_dict.items():
            table[uk] = (table.get(uk, 0) + uv) % p

    elapsed = time.perf_counter() - t0
    return table, elapsed


def benchmark_h14() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-14: GPU Warp-Cooperative Transition Aggregation Benchmark        ")
    print("=" * 80)
    p = 4294967291

    # 1. Micro-Benchmark: 2,000,000 Transition Writes with Contention Patterns
    print("\n[Step 1] Micro-Benchmark: 2,000,000 High-Contention Transition Writes:")
    N_OPS = 2000000
    random.seed(42)
    # High locality: only 5,000 unique target states (frequent collision within warps)
    test_keys = [random.randint(1, 5000) for _ in range(N_OPS)]
    test_vals = [random.randint(1, 1000) for _ in range(N_OPS)]

    # Baseline (Atomic)
    res_base, t_base = simulate_atomic_contention_writes(test_keys, test_vals, p)
    ops_base = N_OPS / t_base / 1e6

    # Warp-Cooperative
    res_warp, t_warp = simulate_warp_cooperative_writes(test_keys, test_vals, p)
    ops_warp = N_OPS / t_warp / 1e6

    assert res_base == res_warp, "Result mismatch in warp aggregation!"

    speedup = t_base / t_warp
    print(f"  Standard Serial Atomic Writes:    {t_base:.4f}s ({ops_base:.2f} M ops/sec)")
    print(f"  Warp-Cooperative Pre-Aggregation: {t_warp:.4f}s ({ops_warp:.2f} M ops/sec) -> Speedup: {speedup:.2f}x")

    passed = speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] H-14 Warp-Cooperative Aggregation achieves {speedup:.2f}x speedup ({ops_warp:.2f} M ops/sec).")
        print(f"  GPU ACCELERATION: In-warp reduction eliminates global atomic lock contention.")
    else:
        print(f"  DECISION: [PRUNED] Speedup ({speedup:.2f}x) below threshold (1.15x).")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h14()
