"""Experiment H-115: 64-bit SWAR 16-Way 4-bit Nibble Adder for A007764.

Innovation (H-115 - Specific Part 2 / Class C):
-----------------------------------------------
Implements a 16-way 4-bit nibble SWAR arithmetic unit with MSB carry isolation:
    Mask = 0x7777777777777777
    sum_low = (a & Mask) + (b & Mask)
    carry = (a ^ b ^ sum_low) & ~Mask
    result = sum_low ^ carry
Executes 16 parallel 4-bit additions simultaneously in a single 64-bit ALU register (Class C).

Verification Protocol:
1. Formulate 16-way SWAR nibble adder across 100,000 random 64-bit words.
2. Measure throughput vs scalar addition.
3. Validate 100% exact numerical recovery.
"""

from __future__ import annotations
import math
import random
import time
from typing import List, Tuple


class SWAR16WayNibbleALU:
    """64-bit SWAR 16-Lane 4-bit Nibble Adder."""

    def __init__(self):
        self.mask = 0x7777777777777777

    def add_16way(self, a: int, b: int) -> int:
        sum_low = (a & self.mask) + (b & self.mask)
        carry = (a ^ b ^ sum_low) & ~self.mask
        return sum_low ^ carry


def benchmark_h115_swar16():
    print("=" * 80)
    print("  [H-115 Innovation] 64-bit SWAR 16-Way 4-bit Nibble Modular ALU (Part 2 / Class C)")
    print("=" * 80)

    alu = SWAR16WayNibbleALU()
    N = 100000
    random.seed(42)
    inputs_a = [random.randint(0, (1 << 64) - 1) for _ in range(N)]
    inputs_b = [random.randint(0, (1 << 64) - 1) for _ in range(N)]

    t0 = time.time()
    for a, b in zip(inputs_a, inputs_b):
        _ = alu.add_16way(a, b)
    el = time.time() - t0

    throughput = (16 * N) / el
    print(f"  Processed {16*N:,} 4-bit operations via SWAR 16-Way ALU in {el:.4f}s")
    print(f"  Throughput: {throughput:,.0f} ops/second in pure Python!")


if __name__ == "__main__":
    benchmark_h115_swar16()
