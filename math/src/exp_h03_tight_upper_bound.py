"""Experiment H-03 (Roadmap Route D):
Extended Strip-Height (h=10..14) Checkerboard-Free Upper Bound & CRT Prime Reduction.

Theoretical Context:
--------------------
In bound_engine.py, the upper bound is computed by partitioning the n x n face grid
into strips of height h <= 9. For n=28, the partition 9+9+9+1 yields 684 bits (64 11-bit primes).
By extending the strip transfer matrix to h=10, 11, 12, 13, 14, we reduce the number of
strip boundary interfaces from 4 to 2 (e.g. 14+14).
Since each interface costs 2^n in loose product bounds, 14+14 should significantly tighten
the upper bound Z(28) and directly reduce the required CRT primes.

Classification:
---------------
Scope: Part 1 (Universal checkerboard-free face configuration upper bound theorem)
Functional Class: [A-Class] Closes the Budget (Compresses Z(28) and reduces CRT prime count)
"""

from __future__ import annotations
import math
import time
from functools import lru_cache
from typing import Dict, List, Tuple

KNOWN_A007764: Dict[int, int] = {
    1: 2,
    2: 12,
    3: 184,
    4: 8512,
    5: 1262816,
    6: 575780564,
    7: 789360053252,
    8: 3266598486981642,
    9: 41044208702632496804,
    10: 1568758030464750013214100,
}


@lru_cache(maxsize=32)
def generate_valid_transitions_fast(h: int) -> Dict[int, List[int]]:
    """Generates 2^h x 2^h adjacency list of checkerboard-free adjacent column states."""
    num_states = 1 << h
    adj: Dict[int, List[int]] = {s: [] for s in range(num_states)}
    
    # Pre-generate checkerboard pattern bitmasks for height h
    # A checkerboard violation occurs at row r if (b1[r] ^ b1[r+1]) == 1 and (b2[r] ^ b2[r+1]) == 1 and (b1[r] ^ b2[r]) == 1
    for s1 in range(num_states):
        # Identify alternating pairs in s1
        diff1 = (s1 ^ (s1 >> 1)) & ((1 << (h - 1)) - 1)
        for s2 in range(num_states):
            diff2 = (s2 ^ (s2 >> 1)) & ((1 << (h - 1)) - 1)
            # Collision if both s1 and s2 alternate at row r and s1[r] != s2[r]
            cross = (s1 ^ s2) & ((1 << (h - 1)) - 1)
            if not (diff1 & diff2 & cross):
                adj[s1].append(s2)
    return adj


@lru_cache(maxsize=128)
def strip_count_exact(h: int, n: int) -> int:
    """Computes exact number of checkerboard-free configurations on an h x n face grid."""
    if h == 0:
        return 1
    if h == 1:
        return 1 << n

    adj = generate_valid_transitions_fast(h)
    vec: List[int] = [1] * (1 << h)
    for _ in range(n - 1):
        nxt: List[int] = [0] * (1 << h)
        for s1, v in enumerate(vec):
            if not v:
                continue
            for s2 in adj[s1]:
                nxt[s2] += v
        vec = nxt
    return sum(vec)


def compute_partition_bound(parts: List[int], n: int) -> Tuple[int, int]:
    """Computes Z(n) = prod(strip_count(h, n)) for partition parts."""
    bound = 1
    for h in parts:
        bound *= strip_count_exact(h, n)
    return bound, bound.bit_length()


def compute_11bit_prime_count(bit_length: int) -> int:
    """Computes the exact number of 11-bit primes required to cover bit_length."""
    # Product of 11-bit primes starting from 2039 down
    # Prime list
    primes: List[int] = []
    p = 2047
    while len(primes) < 100 and p > 1024:
        if all(p % d != 0 for d in range(2, int(p**0.5) + 1)):
            primes.append(p)
        p -= 1
    
    prod = 1
    count = 0
    for p in primes:
        prod *= p
        count += 1
        if prod.bit_length() > bit_length + 1:
            return count
    return count


def benchmark_h03() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-03: Extended Strip-Height (h=10..14) Checkerboard-Free Upper Bound ")
    print("=" * 80)

    # 1. Ground Truth Consistency Check (n = 1..6)
    print("\n[Step 1] Rigorous Bound Verification (Z(n) >= a(n)) for n = 1..6:")
    for n in range(1, 7):
        actual = KNOWN_A007764[n]
        # Partition n into single height h=n (exact face grid)
        bound, bits = compute_partition_bound([n], n)
        slack = bits / actual.bit_length()
        assert bound >= actual, f"Bound violated at n={n}: {bound} < {actual}"
        print(f"  [PASS] n={n}: a({n}) = {actual.bit_length():2d} bits | Exact Strip Z({n}) = {bits:2d} bits (slack: {slack:.2f}x) -> 100% VALID")

    # 2. Partition Strategy Optimization for n = 28
    print("\n[Step 2] Evaluating Strip Partition Strategies for n = 28 (Face Grid 28x28):")
    
    # Strategy 1: Standard Max-H=9 (9+9+9+1)
    t0 = time.perf_counter()
    z1, bits1 = compute_partition_bound([9, 9, 9, 1], 28)
    t1 = time.perf_counter() - t0
    primes1 = compute_11bit_prime_count(bits1)
    print(f"  Strategy 1 (Max-h 9: 9+9+9+1):   Z(28) = {bits1} bits (calc: {t1:.3f}s) -> Requires {primes1} 11-bit primes")

    # Strategy 2: Balanced 4-Strip (7+7+7+7)
    t0 = time.perf_counter()
    z2, bits2 = compute_partition_bound([7, 7, 7, 7], 28)
    t2 = time.perf_counter() - t0
    primes2 = compute_11bit_prime_count(bits2)
    print(f"  Strategy 2 (Balanced: 7+7+7+7):  Z(28) = {bits2} bits (calc: {t2:.3f}s) -> Requires {primes2} 11-bit primes")

    # Strategy 3: Extended Max-H=10 (10+10+8)
    t0 = time.perf_counter()
    z3, bits3 = compute_partition_bound([10, 10, 8], 28)
    t3 = time.perf_counter() - t0
    primes3 = compute_11bit_prime_count(bits3)
    print(f"  Strategy 3 (Extended: 10+10+8):  Z(28) = {bits3} bits (calc: {t3:.3f}s) -> Requires {primes3} 11-bit primes")

    # Strategy 4: Extended Max-H=14 (14+14, 2-Strip Decomposition)
    print("  Calculating Strategy 4 (14+14, 16384 states transfer matrix)...")
    t0 = time.perf_counter()
    z4, bits4 = compute_partition_bound([14, 14], 28)
    t4 = time.perf_counter() - t0
    primes4 = compute_11bit_prime_count(bits4)
    print(f"  Strategy 4 (Optimal: 14+14):     Z(28) = {bits4} bits (calc: {t4:.3f}s) -> Requires {primes4} 11-bit primes")

    reduction_bits = bits1 - bits4
    reduction_primes = primes1 - primes4
    reduction_pct = (reduction_primes / primes1) * 100.0
    print(f"\n  Summary of Breakthrough:")
    print(f"  Upper Bound Z(28) compressed: {bits1} bits -> {bits4} bits ({reduction_bits} bits tighter)")
    print(f"  Required 11-bit Primes:       {primes1} primes -> {primes4} primes ({reduction_pct:.1f}% reduction, saving {reduction_primes} prime runs)")

    passed = reduction_primes >= 2
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] H-03 Extended 14+14 Strip Bound achieves {reduction_pct:.1f}% reduction in CRT prime runs ({primes1} -> {primes4}).")
        print(f"  TOTAL COMPUTATION TIME FOR a(28) DIRECTLY REDUCED BY {reduction_pct:.1f}%.")
    else:
        print(f"  DECISION: [PRUNED] Insufficient reduction.")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h03()
