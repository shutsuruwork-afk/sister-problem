"""Experiment H-30 (Roadmap Route C / Bitboard ALU Optimization):
BMI1/BMI2 (tzcnt / blsr / popcnt) Hardware-Accelerated Bitboard Scanning.

Theoretical Context:
--------------------
During bitboard DFS and frontier profile slot searches, finding the next set bit in a 64-bit
occupancy mask is the most frequent micro-operation.
Scalar Bit-Shift Iterator:
    while ((mask & 1) == 0) { shift++; mask >>= 1; }  (Multiple branch/shift cycles)
Hardware BMI1/BMI2 Iterator:
    while (mask != 0) {
        idx = _tzcnt_u64(mask);   // Single cycle hardware trailing zero count
        mask = _blsr_u64(mask);   // Single cycle isolate & reset lowest set bit (x & (x-1))
    }

Classification:
---------------
Scope: Part 2 (Specific to x86-64 BMI1/BMI2 / ARM64 CLZ hardware instructions)
Functional Class: [C-Class] Throughput Layer (Bit Manipulation Instructions)
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


def benchmark_scalar_bit_shift(masks: List[int]) -> Tuple[int, float]:
    """Simulate scalar branch-and-shift bitboard traversal."""
    total_bits = 0
    t0 = time.perf_counter()
    for mask in masks:
        m = mask
        shift = 0
        while m > 0:
            if m & 1:
                total_bits += shift
            shift += 1
            m >>= 1
    elapsed = time.perf_counter() - t0
    return total_bits, elapsed


def benchmark_bmi_blsr_iterator(masks: List[int]) -> Tuple[int, float]:
    """Simulate BMI1/BMI2 hardware iterator using tzcnt and blsr (x & (x-1))."""
    total_bits = 0
    t0 = time.perf_counter()
    for mask in masks:
        m = mask
        while m > 0:
            # tzcnt: (m & -m).bit_length() - 1
            lsb = m & -m
            idx = lsb.bit_length() - 1
            total_bits += idx
            # blsr: m = m & (m - 1)
            m &= (m - 1)
    elapsed = time.perf_counter() - t0
    return total_bits, elapsed


def benchmark_h30() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-30: BMI1/BMI2 (tzcnt / blsr) Bitboard Traversal Optimization       ")
    print("=" * 80)
    N_MASKS = 1000000

    random.seed(42)
    # Generate 1M random 64-bit occupancy masks with ~8 set bits per mask
    masks = [random.randint(0, 0xFFFFFFFFFFFFFFFF) & random.randint(0, 0xFFFFFFFFFFFFFFFF) for _ in range(N_MASKS)]

    print("\n[Step 1] Micro-Benchmark: 1,000,000 Bitboard Mask Traversals:")
    bits_scalar, t_scalar = benchmark_scalar_bit_shift(masks)
    ops_scalar = N_MASKS / t_scalar / 1e6

    bits_bmi, t_bmi = benchmark_bmi_blsr_iterator(masks)
    ops_bmi = N_MASKS / t_bmi / 1e6

    assert bits_scalar == bits_bmi, "BMI iteration must match scalar bit count exactly!"

    speedup = t_scalar / t_bmi
    print(f"  Scalar Shift Iterator:             {t_scalar:.4f}s ({ops_scalar:.2f} M masks/sec)")
    print(f"  BMI (tzcnt + blsr) Iterator:       {t_bmi:.4f}s ({ops_bmi:.2f} M masks/sec) -> Speedup: {speedup:.2f}x")

    passed = speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] BMI Hardware Iterator achieves {speedup:.2f}x speedup ({ops_bmi:.2f} M masks/sec).")
        print(f"  BITBOARD ACCELERATION: Zero-branch tzcnt/blsr reduces inner bitboard loop cost by {speedup:.2f}x.")
    else:
        print(f"  DECISION: [PRUNED] Speedup ({speedup:.2f}x) below threshold (1.15x).")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h30()
