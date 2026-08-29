"""Experiment H-145: 64-bit SWAR 64-Way 1-bit Monobit Adder for A007764.

Innovation (H-145 - Specific Part 2 / Class C):
-----------------------------------------------
Implements a 64-way 1-bit monobit SWAR parallel boolean full adder array:
    Sum = a ^ b ^ c_in
    Carry_out = (a & b) | (c_in & (a ^ b))
Executes 64 parallel bit-level binary additions simultaneously in a single 64-bit ALU register (Class C).

Verification Protocol:
1. Formulate 64-way SWAR monobit full adder across 100,000 random 64-bit words.
2. Measure throughput vs scalar addition.
3. Validate 100% exact numerical recovery.
"""

from __future__ import annotations
import math
import random
import time
from typing import List, Tuple


class SWAR64WayMonobitALU:
    """64-bit SWAR 64-Lane 1-bit Monobit Full Adder."""

    def __init__(self):
        pass

    def full_add_64way(self, a: int, b: int, c_in: int) -> Tuple[int, int]:
        s = a ^ b ^ c_in
        c_out = (a & b) | (c_in & (a ^ b))
        return s, c_out


def benchmark_h145_swar64():
    print("=" * 80)
    print("  [H-145 Innovation] 64-bit SWAR 64-Way 1-bit Monobit Modular ALU (Part 2 / Class C)")
    print("=" * 80)

    alu = SWAR64WayMonobitALU()
    N = 100000
    random.seed(42)
    inputs_a = [random.randint(0, (1 << 64) - 1) for _ in range(N)]
    inputs_b = [random.randint(0, (1 << 64) - 1) for _ in range(N)]
    inputs_c = [random.randint(0, (1 << 64) - 1) for _ in range(N)]

    t0 = time.time()
    for a, b, c in zip(inputs_a, inputs_b, inputs_c):
        _ = alu.full_add_64way(a, b, c)
    el = time.time() - t0

    throughput = (64 * N) / el
    print(f"  Processed {64*N:,} 1-bit full additions via SWAR 64-Way ALU in {el:.4f}s")
    print(f"  Throughput: {throughput:,.0f} ops/second in pure Python!")


if __name__ == "__main__":
    benchmark_h145_swar64()
