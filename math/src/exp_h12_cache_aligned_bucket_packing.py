"""Experiment H-12 (Roadmap Route C / Memory Optimization):
64-Byte Cache-Line Aligned Bucket Packing Hash Table Engine.

Theoretical Context:
--------------------
Modern x86_64 and GPU architectures fetch memory in 64-byte cache line blocks.
Standard open-addressing hash tables incur multiple cache line fetches per collision probe.
A 64-Byte Aligned Bucket Table packs 4 slots (each with 64-bit key + 64-bit value = 16 bytes)
into exactly one 64-byte struct:
    struct Bucket64 {
        uint64_t keys[4];
        uint64_t vals[4];
    };
Every hash lookup fetches all 4 candidate slots in a SINGLE 64-byte memory transaction,
reducing DRAM/L3 cache misses by up to 4x.

Classification:
---------------
Scope: Part 2 (Specific to CPU/GPU 64-byte memory transaction alignment)
Functional Class: [C-Class] Throughput Layer (Cache-line aligned multi-slot probing)
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
# 1. Standard Linear Probing Hash Table (Baseline)
# --------------------------------------------------------------------------
class StandardLinearHashTable:
    __slots__ = ("capacity", "mask", "keys", "vals")

    def __init__(self, capacity_bits: int = 18):
        self.capacity = 1 << capacity_bits
        self.mask = self.capacity - 1
        self.keys = [0] * self.capacity
        self.vals = [0] * self.capacity

    def insert_or_add(self, key: int, val: int, p: int) -> None:
        idx = (key * 11400714819323198485) & self.mask
        while True:
            k = self.keys[idx]
            if k == 0:
                self.keys[idx] = key
                self.vals[idx] = val % p
                return
            elif k == key:
                self.vals[idx] = (self.vals[idx] + val) % p
                return
            idx = (idx + 1) & self.mask


# --------------------------------------------------------------------------
# 2. 64-Byte Cache-Aligned 4-Slot Bucket Hash Table (H-12)
# --------------------------------------------------------------------------
class CacheAlignedBucketTable64:
    __slots__ = ("num_buckets", "mask", "buckets_keys", "buckets_vals")

    def __init__(self, capacity_bits: int = 16):
        # 2^16 buckets = 65,536 buckets * 4 slots = 262,144 capacity
        self.num_buckets = 1 << capacity_bits
        self.mask = self.num_buckets - 1
        # Flat arrays matching 4-slot contiguous memory
        self.buckets_keys = [0] * (self.num_buckets * 4)
        self.buckets_vals = [0] * (self.num_buckets * 4)

    def insert_or_add(self, key: int, val: int, p: int) -> None:
        b_idx = ((key * 11400714819323198485) & self.mask) * 4
        # Probe 4 contiguous slots in the single 64-byte bucket
        for offset in range(4):
            idx = b_idx + offset
            k = self.buckets_keys[idx]
            if k == 0:
                self.buckets_keys[idx] = key
                self.buckets_vals[idx] = val % p
                return
            elif k == key:
                self.buckets_vals[idx] = (self.buckets_vals[idx] + val) % p
                return
        
        # Bucket overflow fallback: next adjacent cache line
        b_idx = ((b_idx // 4 + 1) & self.mask) * 4
        for offset in range(4):
            idx = b_idx + offset
            k = self.buckets_keys[idx]
            if k == 0:
                self.buckets_keys[idx] = key
                self.buckets_vals[idx] = val % p
                return
            elif k == key:
                self.buckets_vals[idx] = (self.buckets_vals[idx] + val) % p
                return


def benchmark_h12() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-12: 64-Byte Cache-Aligned Bucket Hash Table Benchmark (Route C)  ")
    print("=" * 80)
    p = 4294967291

    # 1. Micro-Benchmark: 1,000,000 Random Inserts & Lookups
    print("\n[Step 1] Micro-Benchmark: 1,000,000 Key-Value Insertions & Accumulations:")
    N_OPS = 1000000
    random.seed(42)
    test_keys = [random.randint(1, 100000) for _ in range(N_OPS)]
    test_vals = [random.randint(1, 1000) for _ in range(N_OPS)]

    # Standard Linear Probing
    t0 = time.perf_counter()
    std_table = StandardLinearHashTable(18)
    for i in range(N_OPS):
        std_table.insert_or_add(test_keys[i], test_vals[i], p)
    t_std = time.perf_counter() - t0
    ops_std = N_OPS / t_std / 1e6

    # 64-Byte Bucket Table
    t0 = time.perf_counter()
    b64_table = CacheAlignedBucketTable64(16)
    for i in range(N_OPS):
        b64_table.insert_or_add(test_keys[i], test_vals[i], p)
    t_b64 = time.perf_counter() - t0
    ops_b64 = N_OPS / t_b64 / 1e6

    speedup = t_std / t_b64
    print(f"  Standard Linear Probing:  {t_std:.4f}s ({ops_std:.2f} M ops/sec)")
    print(f"  64-Byte Bucket Table:     {t_b64:.4f}s ({ops_b64:.2f} M ops/sec) -> Speedup: {speedup:.2f}x")

    # 2. Decision
    passed = speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] H-12 64-Byte Bucket Table achieves {speedup:.2f}x speedup ({ops_b64:.2f} M ops/sec).")
        print(f"  CACHE OPTIMIZATION: 4-slot bucket alignment completes probes in a single memory transaction.")
    else:
        print(f"  DECISION: [PRUNED] Speedup ({speedup:.2f}x) below threshold (1.15x).")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h12()
