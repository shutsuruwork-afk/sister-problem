"""Checkerboard-Free Strip Upper Bound Engine for A007764.

Rigorous mathematical upper bound for self-avoiding corner-to-corner paths on an (n+1)x(n+1) grid:

Theoretical Basis:
------------------
Every simple s-t path on a planar grid graph is uniquely represented as P0 XOR boundary(F)
for a face subset F on the n x n face grid.
At interior vertices, simple paths cannot form a 2x2 checkerboard pattern
(all 4 incident edges active simultaneously).
Therefore, the number of simple paths is strictly bounded by the number of checkerboard-free
binary face configurations.

This module computes the exact transfer matrix for strips of height h <= 9, and determines
the optimal integer partition of n into heights to yield the minimal upper bound Z(n).
"""

from __future__ import annotations
import math
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple


@lru_cache(maxsize=32)
def generate_valid_transitions(h: int) -> Dict[int, List[int]]:
    """Generates the 2^h x 2^h adjacency list of valid adjacent column states.

    A 2x2 subgrid across columns col1, col2 at rows r, r+1 is a checkerboard if:
        col1[r] != col1[r+1] and col2[r] != col2[r+1] and col1[r] != col2[r]

    Args:
        h: Strip height (number of face rows, 1 <= h <= 9).

    Returns:
        Dictionary mapping each state in [0, 2^h) to list of valid successor states.
    """
    if h <= 0:
        raise ValueError(f"Height h must be positive, got {h}")
    num_states: int = 1 << h
    adj: Dict[int, List[int]] = {s: [] for s in range(num_states)}

    for s1 in range(num_states):
        for s2 in range(num_states):
            valid = True
            for r in range(h - 1):
                b1_top = (s1 >> r) & 1
                b1_bot = (s1 >> (r + 1)) & 1
                b2_top = (s2 >> r) & 1
                b2_bot = (s2 >> (r + 1)) & 1
                if (b1_top ^ b1_bot) == 1 and (b2_top ^ b2_bot) == 1 and (b1_top ^ b2_top) == 1:
                    valid = False
                    break
            if valid:
                adj[s1].append(s2)
    return adj


@lru_cache(maxsize=128)
def strip_count(h: int, n: int) -> int:
    """Computes exact number of checkerboard-free configurations on an h x n face grid.

    Args:
        h: Strip height.
        n: Grid width (number of columns).

    Returns:
        Exact integer configuration count.
    """
    if h == 0:
        return 1
    if h == 1:
        return 1 << n

    adj = generate_valid_transitions(h)
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


def evaluate_partitions(n: int, max_h: int = 9) -> List[Tuple[int, List[int]]]:
    """Finds all integer partitions of n into parts <= max_h and ranks them by upper bound.

    Args:
        n: Total grid dimension.
        max_h: Maximum strip height to consider (default 9).

    Returns:
        Sorted list of tuples (bound_value, partition_parts), ascending.
    """
    results: List[Tuple[int, List[int]]] = []

    def search(rem: int, max_part: int, current_parts: List[int]) -> None:
        if rem == 0:
            bound = 1
            for p in current_parts:
                bound *= strip_count(p, n)
            results.append((bound, current_parts[:]))
            return
        for p in range(min(rem, max_part), 0, -1):
            current_parts.append(p)
            search(rem - p, p, current_parts)
            current_parts.pop()

    search(n, max_h, [])
    results.sort(key=lambda x: x[0])
    return results


def compute_prime_requirements(bit_bound: int) -> Dict[int, Tuple[int, int]]:
    """Computes required prime counts for various modulus bit widths.

    Args:
        bit_bound: Upper bound in bits.

    Returns:
        Dict mapping bit_width -> (prime_count, total_modulus_bits).
    """
    widths: List[int] = [9, 10, 11, 12, 16, 32]
    reqs: Dict[int, Tuple[int, int]] = {}

    for w in widths:
        limit = 1 << w
        count = 0
        prod = 1
        curr = limit - 1
        while prod.bit_length() <= bit_bound + 1 and curr > 2:
            is_p = True
            if curr % 2 == 0:
                is_p = False
            else:
                d = 3
                while d * d <= curr:
                    if curr % d == 0:
                        is_p = False
                        break
                    d += 2
            if is_p:
                count += 1
                prod *= curr
            curr -= 1
        reqs[w] = (count, prod.bit_length())
    return reqs


if __name__ == "__main__":
    print("=== Bound Engine Verification ===")
    p28 = evaluate_partitions(28, max_h=9)[0]
    print(f"Optimal n=28 partition: {'+'.join(map(str, p28[1]))} -> {p28[0].bit_length()} bits")
    assert p28[0].bit_length() == 684
    print("Bound engine verification successful.")
