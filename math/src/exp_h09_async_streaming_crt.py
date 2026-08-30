"""Experiment H-09 (Roadmap Route A / Distributed Infrastructure):
Asynchronous Streaming Multi-Prime Incremental Garner CRT Engine.

Theoretical Context:
--------------------
In full-scale distributed execution for a(28), 64 distinct 11-bit primes finish at
staggered times across distributed workers.
Instead of buffering all 64 residues and executing an expensive O(k^2) multi-precision
all-at-once CRT reduction, Garner's Incremental Algorithm processes each residue x_i mod p_i
the instant worker i completes:
    X_k = X_{k-1} + ( (x_k - X_{k-1}) * C_k mod p_k ) * M_{k-1}
where C_k = M_{k-1}^(-1) mod p_k and M_k = prod_{i=1}^k p_i.
This completely overlaps CRT reconstruction with worker computation and eliminates
aggregation latency.

Classification:
---------------
Scope: Part 2 (Specific to multi-worker / multi-process distributed CRT execution)
Functional Class: [B-Class] Operational Infrastructure (Zero-latency streaming CRT reconstruction)
"""

from __future__ import annotations
import math
import random
import time
from typing import Dict, List, Tuple

CRT_PRIMES_11BIT = [
    2039, 2029, 2027, 2017, 2011, 2003, 1999, 1997, 1993, 1987,
    1979, 1973, 1951, 1949, 1933, 1931, 1913, 1907, 1901, 1889,
    1879, 1877, 1873, 1871, 1867, 1861, 1847, 1831, 1823, 1811,
    1801, 1789, 1787, 1783, 1777, 1759, 1753, 1747, 1741, 1733,
    1723, 1721, 1709, 1699, 1697, 1693, 1669, 1667, 1663, 1657,
    1637, 1627, 1621, 1619, 1613, 1609, 1607, 1601, 1597, 1583,
    1579, 1571, 1567, 1559, # 64 primes total
]

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


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    if a == 0: return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    return gcd, y1 - (b // a) * x1, x1


# --------------------------------------------------------------------------
# 1. Batch Standard CRT
# --------------------------------------------------------------------------
def crt_reconstruct_batch(residues: List[int], primes: List[int]) -> int:
    total = 0
    N = 1
    for p in primes: N *= p
    for r, p in zip(residues, primes):
        Ni = N // p
        _, inv, _ = extended_gcd(Ni, p)
        total = (total + r * (inv % p) * Ni) % N
    return total


# --------------------------------------------------------------------------
# 2. Asynchronous Incremental Garner CRT Engine
# --------------------------------------------------------------------------
class IncrementalGarnerCRT:
    """Incrementally ingests prime residues and maintains exact integer state."""
    __slots__ = ("current_val", "current_modulus", "primes_ingested")

    def __init__(self):
        self.current_val = 0
        self.current_modulus = 1
        self.primes_ingested: List[int] = []

    def ingest_residue(self, p: int, r: int) -> None:
        """Ingests (p, r = val mod p) in O(log p) time, updating state."""
        if not self.primes_ingested:
            self.current_val = r % p
            self.current_modulus = p
            self.primes_ingested.append(p)
            return

        # X_new = X_prev + ( (r - X_prev) * inv(M_prev, p) mod p ) * M_prev
        M_prev = self.current_modulus
        diff = (r - (self.current_val % p)) % p
        _, inv_M, _ = extended_gcd(M_prev % p, p)
        coeff = (diff * (inv_M % p)) % p
        
        self.current_val = self.current_val + coeff * M_prev
        self.current_modulus *= p
        self.primes_ingested.append(p)

    def get_result(self) -> int:
        return self.current_val


def benchmark_h09() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-09: Asynchronous Streaming Incremental Garner CRT Engine       ")
    print("=" * 80)

    # 1. Ground Truth Exact Equivalence Verification (n = 1..10)
    print("\n[Step 1] Exact Ground Truth Verification (Batch CRT vs Incremental Garner):")
    passed_all = True
    for n in range(1, 11):
        expected = KNOWN_A007764[n]
        
        # Select enough 11-bit primes
        primes_used = []
        prod = 1
        for p in CRT_PRIMES_11BIT:
            primes_used.append(p)
            prod *= p
            if prod > 2 * expected: break

        residues = [expected % p for p in primes_used]
        
        # Batch CRT
        ans_batch = crt_reconstruct_batch(residues, primes_used)
        
        # Incremental Garner CRT
        garner = IncrementalGarnerCRT()
        for p, r in zip(primes_used, residues):
            garner.ingest_residue(p, r)
        ans_garner = garner.get_result()

        assert ans_batch == ans_garner == expected, f"Mismatch at n={n}"
        print(f"  [PASS] n={n:2d}: a({n:2d}) = {expected:>28d} | Batch == Garner == Ground Truth ({len(primes_used)} primes, 100% MATCH)")

    # 2. Performance & Latency Benchmark on Full 64 11-bit Primes
    print("\n[Step 2] Full 64-Prime Scalability & Reconstruction Latency Benchmark:")
    # Simulate synthetic 64-prime residues
    random.seed(42)
    sample_a28 = random.randint(1 << 620, (1 << 629) - 1)
    primes64 = CRT_PRIMES_11BIT
    residues64 = [sample_a28 % p for p in primes64]

    # Benchmark Batch CRT (simulating end-of-job synchronous stall)
    t0 = time.perf_counter()
    N_ITERS = 1000
    for _ in range(N_ITERS):
        res_b = crt_reconstruct_batch(residues64, primes64)
    t_batch = (time.perf_counter() - t0) / N_ITERS

    # Benchmark Incremental Garner (simulating streaming ingestion per prime arrival)
    t0 = time.perf_counter()
    for _ in range(N_ITERS):
        g = IncrementalGarnerCRT()
        for p, r in zip(primes64, residues64):
            g.ingest_residue(p, r)
        res_g = g.get_result()
    t_garner = (time.perf_counter() - t0) / N_ITERS

    assert res_b == res_g == sample_a28, "64-prime reconstruction mismatch!"

    speedup = t_batch / t_garner
    print(f"  Batch CRT Latency:       {t_batch * 1000.0:.4f} ms")
    print(f"  Streaming Garner CRT:    {t_garner * 1000.0:.4f} ms")
    print(f"  Reconstruction Speedup:  {speedup:.2f}x ({t_batch/t_garner:.2f}x faster)")

    passed = passed_all and speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] H-09 Streaming Garner CRT Engine achieves {speedup:.2f}x faster reconstruction with 100% precision.")
        print(f"  DISTRIBUTED OVERHEAD: Replaces all-at-once batch reduction with zero-wait incremental streaming.")
    else:
        print(f"  DECISION: [PRUNED] Speedup below threshold.")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h09()
