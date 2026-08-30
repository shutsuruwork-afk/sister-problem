"""Experiment H-60 (Roadmap Route B / CRT Numerical Computation Pipeline):
Precomputed Montgomery Reduction Transformation Pipeline for 62-bit Prime Workers.

Theoretical Context:
--------------------
For 62-bit prime workers, Montgomery arithmetic requires constants:
$R = 2^{64} \pmod{p}$, $R^2 \pmod{p}$, and $p' = -p^{-1} \pmod{2^{64}}$.
Calculating modular inverse dynamically on each prime worker initialization or per-kernel dispatch
incurs $O(\log p)$ extended Euclidean latency.
Precomputing a static lookup table of Montgomery constants offline eliminates all dynamic inverse
calculations during startup and kernel context switches.
We benchmark the initialization and transformation throughput of dynamic vs precomputed constants.

Classification:
---------------
Scope: Part 2 (Specific to 62-bit Modular Arithmetic Pipeline)
Functional Class: [B-Class: Infrastructure] Startup & Modular Constant Precomputation
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


def egcd(a: int, b: int) -> Tuple[int, int, int]:
    """Extended Euclidean Algorithm."""
    if a == 0:
        return b, 0, 1
    g, y, x = egcd(b % a, a)
    return g, x - (b // a) * y, y


def mod_inverse_64(p: int) -> int:
    """Computes -p^{-1} mod 2^64."""
    # Extended Euclidean algorithm modulo 2^64
    g, x, _ = egcd(p, 1 << 64)
    inv = x % (1 << 64)
    return (-inv) % (1 << 64)


def benchmark_dynamic_montgomery_init(primes: List[int], n_reps: int = 10000) -> Tuple[float, float]:
    """Dynamically calculates Montgomery constants on the fly."""
    t0 = time.perf_counter()
    res = 0
    R = 1 << 64
    for _ in range(n_reps):
        for p in primes:
            R_mod = R % p
            R2_mod = (R * R) % p
            p_prime = mod_inverse_64(p)
            res ^= (R_mod ^ R2_mod ^ p_prime)
    elapsed = time.perf_counter() - t0
    ops_sec = (n_reps * len(primes)) / elapsed
    return elapsed, ops_sec


def benchmark_precomputed_montgomery_init(primes: List[int], n_reps: int = 10000) -> Tuple[float, float]:
    """Uses offline precomputed Montgomery constant table."""
    R = 1 << 64
    # Precomputation table
    table = {}
    for p in primes:
        table[p] = (R % p, (R * R) % p, mod_inverse_64(p))

    t0 = time.perf_counter()
    res = 0
    for _ in range(n_reps):
        for p in primes:
            R_mod, R2_mod, p_prime = table[p]
            res ^= (R_mod ^ R2_mod ^ p_prime)
    elapsed = time.perf_counter() - t0
    ops_sec = (n_reps * len(primes)) / elapsed
    return elapsed, ops_sec


def benchmark_h60() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-60: Precomputed Montgomery Reduction Constants Pipeline       ")
    print("=" * 80)

    # 10 distinct 62-bit primes
    primes = [
        4611686018427387847, 4611686018427387823, 4611686018427387799,
        4611686018427387771, 4611686018427387709, 4611686018427387687,
        4611686018427387639, 4611686018427387607, 4611686018427387533,
        4611686018427387517
    ]

    N_REPS = 10000
    print(f"\n[Step 1] Benchmarking Montgomery constant initialization on {len(primes)} primes ({N_REPS:,} iterations):")

    t_dyn, ops_dyn = benchmark_dynamic_montgomery_init(primes, N_REPS)
    t_pre, ops_pre = benchmark_precomputed_montgomery_init(primes, N_REPS)

    speedup = ops_pre / ops_dyn

    print(f"  Dynamic Egcd Constant Calculation:  {t_dyn:7.4f} s | Throughput: {ops_dyn / 1e3:8.2f} k inits/sec")
    print(f"  Precomputed Table Lookup:           {t_pre:7.4f} s | Throughput: {ops_pre / 1e3:8.2f} k inits/sec")
    print(f"  -> Initialization Speedup: {speedup:.2f}x")

    passed = speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] Precomputed Montgomery Constants achieve {speedup:.2f}x startup speedup.")
        print(f"  INFRASTRUCTURE: Precalculates R mod p, R^2 mod p, and -p^{{-1}} mod 2^64 ({ops_pre / 1e3:.2f} k inits/sec).")
    else:
        print("  DECISION: [PRUNED] Speedup below threshold (1.15x).")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h60()
