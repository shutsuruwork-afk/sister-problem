"""Experiment H-06: Anti-Diagonal Triangular DP & Mirror Splicing for A007764.

Hypothesis (H-06):
Running broken-profile DP only on the upper-left triangle { (i,j) : i+j <= n }
and splicing at the anti-diagonal interface via the anti-diagonal reflection rho*tau:
1. Computes the symmetric subset F_{rho*tau}(n) using 1/24 of the full-grid memory.
2. Evaluates whether the full count a(n) can be reconstructed via an anti-diagonal Gram pairing
   in 1/10 to 1/24 memory without prohibitive splicing overhead.

Verification Protocol:
1. Implement triangular DP up to anti-diagonal cut i+j=n.
2. Measure peak layer width of Triangular DP vs Full Square DP for n = 2..8.
3. Quantify the splicing matrix rank and memory footprint.
"""

from __future__ import annotations
from typing import Dict, List, Tuple
from state_engine import KNOWN_A007764, motzkin, EMPTY, OPEN, CLOSE, MARK, partner


def count_triangular_layers(n: int) -> Tuple[int, int, List[int]]:
    """Runs broken-profile frontier DP restricted to the triangle i + j <= n.

    Returns:
        (peak_triangular_states, peak_square_states, layer_widths)
    """
    C = n + 1
    W = C + 1
    layer = {tuple([EMPTY] * W): 1}
    tri_widths = []

    for i in range(C):
        for j in range(C):
            if i + j > n:
                continue  # Skip lower-right triangle

            is_start = (i == 0 and j == 0)
            is_end = False
            can_down = (i < C - 1)
            can_right = (j < C - 1)

            nxt = {}
            for st, v in layer.items():
                L, U = st[j], st[j + 1]
                s = list(st)

                def emit(d, r):
                    if d != EMPTY and not can_down: return
                    if r != EMPTY and not can_right: return
                    s[j], s[j + 1] = d, r
                    nxt[tuple(s)] = nxt.get(tuple(s), 0) + v

                if is_start:
                    emit(MARK, EMPTY)
                    emit(EMPTY, MARK)
                elif L == EMPTY and U == EMPTY:
                    emit(EMPTY, EMPTY)
                    if can_down and can_right:
                        emit(OPEN, CLOSE)
                elif U == EMPTY:
                    emit(L, EMPTY)
                    emit(EMPTY, L)
                elif L == EMPTY:
                    emit(U, EMPTY)
                    emit(EMPTY, U)
                elif L == OPEN and U == CLOSE:
                    pass
                elif L == MARK:
                    q = partner(st, j + 1)
                    s[q] = MARK
                    emit(EMPTY, EMPTY)
                elif U == MARK:
                    q = partner(st, j)
                    s[q] = MARK
                    emit(EMPTY, EMPTY)
                else:
                    p, q = partner(st, j), partner(st, j + 1)
                    lo, hi = min(p, q), max(p, q)
                    s[lo], s[hi] = OPEN, CLOSE
                    emit(EMPTY, EMPTY)

            layer = nxt
            tri_widths.append(len(layer))

        # Row shift
        layer = {(EMPTY,) + st[:C]: v for st, v in layer.items() if st[C] == EMPTY}

    M = motzkin(n + 4)
    square_peak = 2 * (M[n + 2] - M[n + 1])
    tri_peak = max(tri_widths) if tri_widths else 0
    return tri_peak, square_peak, tri_widths


def run_h06_test():
    print("=" * 75)
    print("  [H-06 Test] Triangular DP Peak States vs Full Square DP")
    print("=" * 75)
    print(" n  | Triangular Peak | Full Square Peak | Memory Reduction Ratio")
    print("----|-----------------|------------------|-----------------------")

    for n in range(2, 9):
        tri_pk, sq_pk, _ = count_triangular_layers(n)
        ratio = sq_pk / tri_pk if tri_pk > 0 else 0
        print(f" {n:2d} |    {tri_pk:>10d}   |   {sq_pk:>12d}   |      {ratio:6.2f}x reduction")


if __name__ == "__main__":
    run_h06_test()
