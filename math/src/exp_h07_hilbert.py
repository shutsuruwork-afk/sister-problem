"""Experiment H-07: Fractal Space-Filling Curve (Hilbert Curve) Sweep vs Row Sweep.

Hypothesis (H-07):
Sweeping grid vertices in a space-filling (Hilbert / Peano) fractal order reduces
the interface boundary cut size (number of edges crossing the processed/unprocessed boundary)
from O(n) to O(sqrt(n)), exponentially reducing the peak frontier state count.

Verification Protocol:
1. Generate exact Hilbert curve traversal order for 2^k x 2^k and (n+1) x (n+1) grids.
2. Measure the exact Cut Size (number of grid edges between processed and unprocessed vertices)
   at every single vertex step for:
   - Standard Row Sweep (Lexicographical)
   - Anti-Diagonal Sweep
   - Hilbert Curve Sweep
3. Compare Peak Cut Size and Average Cut Size.
"""

from __future__ import annotations
from typing import List, Set, Tuple


def hilbert_order(n_order: int) -> List[Tuple[int, int]]:
    """Generates the 2D coordinates visited by a Hilbert curve on a (2^n_order) x (2^n_order) grid."""
    coords: List[Tuple[int, int]] = []

    def rot(n: int, x: int, y: int, rx: int, ry: int) -> Tuple[int, int]:
        if ry == 0:
            if rx == 1:
                x = n - 1 - x
                y = n - 1 - y
            x, y = y, x
        return x, y

    N = 1 << n_order
    for d in range(N * N):
        t = d
        x = y = 0
        s = 1
        while s < N:
            rx = 1 & (t // 2)
            ry = 1 & (t ^ rx)
            x, y = rot(s, x, y, rx, ry)
            x += s * rx
            y += s * ry
            t //= 4
            s *= 2
        coords.append((x, y))
    return coords


def row_order(N: int) -> List[Tuple[int, int]]:
    """Standard row-major lexicographical order."""
    return [(r, c) for r in range(N) for c in range(N)]


def diagonal_order(N: int) -> List[Tuple[int, int]]:
    """Anti-diagonal sweep order."""
    coords = []
    for s in range(2 * N - 1):
        for r in range(N):
            c = s - r
            if 0 <= c < N:
                coords.append((r, c))
    return coords


def compute_cut_profile(N: int, traversal: List[Tuple[int, int]]) -> Tuple[int, float, List[int]]:
    """Measures the number of boundary edges between visited and unvisited vertices at each step."""
    visited: Set[Tuple[int, int]] = set()
    cut_sizes: List[int] = []

    for idx, (r, c) in enumerate(traversal):
        visited.add((r, c))
        # Count all grid edges (u, v) such that u in visited and v not in visited
        cut = 0
        for vr, vc in visited:
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nr, nc = vr + dr, vc + dc
                if 0 <= nr < N and 0 <= nc < N:
                    if (nr, nc) not in visited:
                        cut += 1
        cut_sizes.append(cut)

    peak_cut = max(cut_sizes)
    avg_cut = sum(cut_sizes) / len(cut_sizes)
    return peak_cut, avg_cut, cut_sizes


def run_h07_comparison():
    print("=" * 75)
    print("  [H-07 Test] Interface Cut Size: Row Sweep vs Diagonal vs Hilbert Curve")
    print("=" * 75)
    print(" Grid Size N x N |   Row Peak (Avg)   |  Diag Peak (Avg)   |  Hilbert Peak (Avg)")
    print("-----------------|--------------------|--------------------|--------------------")

    for k in [2, 3, 4]:  # 4x4, 8x8, 16x16
        N = 1 << k
        row_seq = row_order(N)
        diag_seq = diagonal_order(N)
        hilbert_seq = hilbert_order(k)

        row_peak, row_avg, _ = compute_cut_profile(N, row_seq)
        diag_peak, diag_avg, _ = compute_cut_profile(N, diag_seq)
        hil_peak, hil_avg, _ = compute_cut_profile(N, hilbert_seq)

        print(
            f"   {N:2d} x {N:2d} ({N*N:3d} pts) |  "
            f"{row_peak:3d} cut ({row_avg:5.1f})   |  "
            f"{diag_peak:3d} cut ({diag_avg:5.1f})   |  "
            f"{hil_peak:3d} cut ({hil_avg:5.1f})"
        )


if __name__ == "__main__":
    run_h07_comparison()
