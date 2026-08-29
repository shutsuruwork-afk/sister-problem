"""Checkerboard-Free Strip Bound Engine for A007764.

Rigorous upper bound for self-avoiding paths crossing an n x n grid:
Every s-t path is P0 XOR boundary(F) for face subset F.
At interior vertices, simple paths cannot form a checkerboard pattern (all 4 surrounding faces having alternating bits).
We compute the transfer matrix for checkerboard-free strips of height h <= 9,
then partition n into strips to obtain the tightest rigorous upper bound Z(n).
"""

import math
from functools import lru_cache

def generate_valid_transitions(h):
    """Generate 2^h x 2^h transition matrix of valid adjacent columns without 2x2 checkerboard."""
    num_states = 1 << h
    # A 2x2 subgrid at rows (r, r+1) has checkerboard pattern if:
    # (col1[r] ^ col1[r+1]) == 1 and (col2[r] ^ col2[r+1]) == 1 and (col1[r] ^ col2[r]) == 1
    # i.e., bits are (0,1)/(1,0) or (1,0)/(0,1).
    adj = {s: [] for s in range(num_states)}
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

@lru_cache(maxsize=None)
def strip_count(h, n):
    """Number of checkerboard-free configurations on an h x n face grid."""
    if h == 0:
        return 1
    if h == 1:
        # Height 1 has no 2x2 subgrids, so all 2^n configurations are free
        return 1 << n
    adj = generate_valid_transitions(h)
    # Start vector: all 2^h states have count 1
    vec = [1] * (1 << h)
    for step in range(n - 1):
        nxt = [0] * (1 << h)
        for s1, v in enumerate(vec):
            if not v:
                continue
            for s2 in adj[s1]:
                nxt[s2] += v
        vec = nxt
    return sum(vec)

def evaluate_partitions(n, max_h=9):
    """Evaluate all integer partitions of n into parts <= max_h and find the minimum bound."""
    results = []
    
    def search(rem, max_part, current_parts):
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

def compute_prime_requirements(bit_bound):
    """Compute required prime counts for various modulus widths."""
    widths = [9, 10, 11, 12, 16, 32]
    reqs = {}
    for w in widths:
        limit = 1 << w
        count = 0
        prod = 1
        curr = limit - 1
        # Simple prime check
        while prod.bit_length() <= bit_bound + 1 and curr > 2:
            # is prime check
            is_p = True
            if curr % 2 == 0: is_p = False
            else:
                d = 3
                while d * d <= curr:
                    if curr % d == 0: is_p = False; break
                    d += 2
            if is_p:
                count += 1
                prod *= curr
            curr -= 1
        reqs[w] = (count, prod.bit_length())
    return reqs

if __name__ == "__main__":
    print("=== Checkerboard-Free Strip Upper Bound Analysis ===")
    for n in [26, 27, 28]:
        parts = evaluate_partitions(n, max_h=9)
        best_bound, best_part = parts[0]
        bit_len = best_bound.bit_length()
        part_str = "+".join(map(str, best_part))
        print(f"\nn = {n}:")
        print(f"  Best Partition: {part_str} -> Bound = {bit_len} bits ({best_bound:.3e})")
        # Compare alternative top partitions
        for bound, p in parts[:4]:
            print(f"    Partition {str('+'.join(map(str, p))):12s} : {bound.bit_length()} bits")
        
        prime_info = compute_prime_requirements(bit_len)
        print(f"  Required Primes for a({n}) bound ({bit_len} bits):")
        for w, (cnt, tot_bits) in prime_info.items():
            print(f"    {w:2d}-bit moduli: {cnt:3d} primes (total modulus = {tot_bits:4d} bits)")
