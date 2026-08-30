"""Experiment H-18 (Roadmap Route C / Hash Table Architecture):
Robin Hood 64-bit Bitboard Hashing vs Full Bijective Direct Array Indexing.

Theoretical Context:
--------------------
Robin Hood Hashing minimizes the variance of probe sequence lengths (PSL) by stealing
from the rich (low PSL) to give to the poor (high PSL).
However, with the adoption of H-10 / Bijective Quotient Ranking (S/Sigma), each boundary
state has a unique contiguous index in [0, |S/Sigma|).
A direct flat array index requires zero probe arithmetic and zero collision metadata:
    RAM Offset = rank * sizeof(StateSlot)
This experiment benchmarks whether Robin Hood Hash provides any memory-access advantage
over Direct Array Indexing.

Classification:
---------------
Scope: Part 2 (Specific to CPU/GPU cache line probing vs array addressing)
Functional Class: [C-Class] Throughput Layer (Comparative Evaluation)
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
# 1. Robin Hood Hash Table
# --------------------------------------------------------------------------
class RobinHoodHashTable:
    __slots__ = ("capacity", "mask", "keys", "vals", "psls")

    def __init__(self, capacity_bits: int = 18):
        self.capacity = 1 << capacity_bits
        self.mask = self.capacity - 1
        self.keys = [0] * self.capacity
        self.vals = [0] * self.capacity
        self.psls = [-1] * self.capacity

    def insert_or_add(self, key: int, val: int, p: int) -> None:
        idx = (key * 11400714819323198485) & self.mask
        curr_psl = 0
        curr_key = key
        curr_val = val % p

        while True:
            k = self.keys[idx]
            if k == 0:
                self.keys[idx] = curr_key
                self.vals[idx] = curr_val
                self.psls[idx] = curr_psl
                return
            elif k == curr_key:
                self.vals[idx] = (self.vals[idx] + curr_val) % p
                return

            # Robin Hood steal condition
            if self.psls[idx] < curr_psl:
                # Swap current with existing
                self.keys[idx], curr_key = curr_key, self.keys[idx]
                self.vals[idx], curr_val = curr_val, self.vals[idx]
                self.psls[idx], curr_psl = curr_psl, self.psls[idx]

            idx = (idx + 1) & self.mask
            curr_psl += 1


# --------------------------------------------------------------------------
# 2. Direct Bijective Flat Array (H-10 Baseline)
# --------------------------------------------------------------------------
class DirectFlatArrayTable:
    __slots__ = ("capacity", "vals")

    def __init__(self, size: int):
        self.capacity = size
        self.vals = [0] * size

    def insert_or_add(self, rank_idx: int, val: int, p: int) -> None:
        self.vals[rank_idx] = (self.vals[rank_idx] + val) % p


def benchmark_h18() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-18: Robin Hood Hash Table vs Direct Flat Array Benchmark         ")
    print("=" * 80)
    p = 4294967291
    N_OPS = 2000000
    N_STATES = 100000

    random.seed(42)
    test_keys = [random.randint(1, N_STATES) for _ in range(N_OPS)]
    test_ranks = [k - 1 for k in test_keys]
    test_vals = [random.randint(1, 1000) for _ in range(N_OPS)]

    # 1. Benchmark Direct Flat Array (H-10)
    print("\n[Step 1] Micro-Benchmark: 2,000,000 Key-Value Insertions & Accumulations:")
    t0 = time.perf_counter()
    direct_tbl = DirectFlatArrayTable(N_STATES)
    for i in range(N_OPS):
        direct_tbl.insert_or_add(test_ranks[i], test_vals[i], p)
    t_direct = time.perf_counter() - t0
    ops_direct = N_OPS / t_direct / 1e6

    # 2. Benchmark Robin Hood Hash Table
    t0 = time.perf_counter()
    rh_tbl = RobinHoodHashTable(18)
    for i in range(N_OPS):
        rh_tbl.insert_or_add(test_keys[i], test_vals[i], p)
    t_rh = time.perf_counter() - t0
    ops_rh = N_OPS / t_rh / 1e6

    speedup = t_rh / t_direct
    print(f"  Direct Flat Array (H-10 Baseline): {t_direct:.4f}s ({ops_direct:.2f} M ops/sec)")
    print(f"  Robin Hood Hash Table (H-18):      {t_rh:.4f}s ({ops_rh:.2f} M ops/sec) -> Direct Speedup: {speedup:.2f}x")

    passed = ops_rh >= ops_direct * 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] Robin Hood Hash achieved {ops_rh:.2f} M ops/sec.")
    else:
        print(f"  DECISION: [PRUNED] Direct Flat Array is {speedup:.2f}x faster than Robin Hood Hash.")
        print(f"  MATHEMATICAL VERDICT: H-10 Bijective Direct Array completely renders hash tables obsolete.")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h18()
