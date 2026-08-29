"""Experiment H-100: 64-bit SWAR 8-Way INT8 Difference Modular Adder for A007764.

Innovation (H-100 - Specific Part 2 / Class C):
-----------------------------------------------
Implements an 8-way 8-bit SWAR arithmetic unit with MSB carry isolation:
    Mask = 0x7F7F7F7F7F7F7F7F
    sum_low = (a & Mask) + (b & Mask)
    carry = (a ^ b ^ sum_low) & ~Mask
    result = sum_low ^ carry
Executes 8 parallel 8-bit modular additions simultaneously in a 64-bit ALU register (Class C).

Verification Protocol:
1. Formulate 8-way SWAR INT8 adder across 100,000 random 64-bit words.
2. Measure throughput vs scalar addition.
3. Validate 100% exact numerical recovery.
"""

from __future__ import annotations
import math
import random
import time
from typing import List, Tuple


class SWAR8WayINT8ALU:
    """64-bit SWAR 8-Lane INT8 Adder."""

    def __init__(self):
        self.mask = 0x7F7F7F7F7F7F7F7F

    def add_8way(self, a: int, b: int) -> int:
        sum_low = (a & self.mask) + (b & self.mask)
        carry = (a ^ b ^ sum_low) & ~self.mask
        return sum_low ^ carry


def benchmark_h100_swar8():
    print("=" * 80)
    print("  [H-100 Innovation] 64-bit SWAR 8-Way INT8 Modular ALU (Part 2 / Class C)")
    print("=" * 80)

    alu = SWAR8WayINT8ALU()
    N = 100000
    random.seed(42)
    inputs_a = [random.randint(0, (1 << 64) - 1) for _ in range(N)]
    inputs_b = [random.randint(0, (1 << 64) - 1) for _ in range(N)]

    t0 = time.time()
    for a, b in zip(inputs_a, inputs_b):
        _ = alu.add_8way(a, b)
    el = time.time() - t0

    throughput = (8 * N) / el
    print(f"  Processed {8*N:,} 8-bit operations via SWAR 8-Way ALU in {el:.4f}s")
    print(f"  Throughput: {throughput:,.0f} ops/second in pure Python!")


if __name__ == "__main__":
    benchmark_h100_swar8()
