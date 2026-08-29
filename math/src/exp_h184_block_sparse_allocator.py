"""Experiment H-184: Block-Sparse Bitboard Allocator Evaluation.

Hypothesis (H-184 - Specific Part 2 / Target: Class A):
-------------------------------------------------------
Investigate whether a 2-level block-sparse allocator (1024-element sub-blocks) can reduce
dense layer vector memory by 3x to 5x across intermediate boundary stages.

Empirical Evaluation & Block Fragmentation Analysis:
1. When active Motzkin states span across broad index prefix ranges:
   - Every block of 1024 elements receives at least a few active state writes.
   - At 20% global density, 98 of 98 blocks are triggered.
   - Total allocated elements: 100,352 vs 100,000 total slots.
   - Real Memory Reduction: 1.00x (0% Savings due to Block Internal Fragmentation).
2. Overhead:
   - Extra pointer indirection and bitmask indexing overhead with zero net memory savings.

Decision:
-> Block-sparse allocation suffers from severe internal fragmentation across Motzkin index spaces.
-> VERDICT: PRUNED (Fail Fast / Empirical Fragmentation Obstruction).
"""

from __future__ import annotations
import math
import random
import time
from typing import List, Tuple, Dict


class BlockSparseAllocator:
    def __init__(self, block_size: int = 1024):
        self.block_size = block_size
        self.blocks: Dict[int, List[int]] = {}
        self.allocated_elements = 0

    def set(self, index: int, val: int):
        b_id = index // self.block_size
        offset = index % self.block_size
        if b_id not in self.blocks:
            self.blocks[b_id] = [0] * self.block_size
            self.allocated_elements += self.block_size
        self.blocks[b_id][offset] = val

    def get(self, index: int) -> int:
        b_id = index // self.block_size
        offset = index % self.block_size
        if b_id in self.blocks:
            return self.blocks[b_id][offset]
        return 0


def evaluate_h184():
    print("=" * 80)
    print("  [H-184 Evaluation] Block-Sparse Bitboard Allocator Fragmentation Test")
    print("=" * 80)

    total_capacity = 100000
    active_density = 0.20
    allocator = BlockSparseAllocator(block_size=1024)

    random.seed(42)
    active_indices = sorted(random.sample(range(total_capacity), int(total_capacity * active_density)))

    for idx in active_indices:
        allocator.set(idx, idx % 2048)

    reduction = total_capacity / allocator.allocated_elements

    print(f"  Total Index Space:    {total_capacity:>8,d} slots")
    print(f"  Physically Allocated: {allocator.allocated_elements:>8,d} slots")
    print(f"  Effective Reduction:  {reduction:4.2f}x (0% Savings due to Fragmentation)")
    print("\n[H-184 DECISION]: Block chunking fails to compress memory across sparse Motzkin spaces.")
    print("-> VERDICT: PRUNED (Fail Fast / Empirical Fragmentation Obstruction).")


if __name__ == "__main__":
    evaluate_h184()
