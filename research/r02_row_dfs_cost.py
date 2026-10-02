"""r02: cost of skipping the mid-row vector entirely.

Row-at-a-time DFS from each boundary profile visits one leaf per path
through the row, so its work is the sum of all entries of the row
transfer matrix T.  The cell sweep costs (n+1) * 2B(n) state updates per
row.  This measures both, plus the DFS internal-node count.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kaggle'))
from a007764_core import *

def row_dfs_stats(n, i=1):
    P = ProfileRanker(n); W = n + 2
    leaves = nodes = 0; nnz = set()
    for r in range(P.size):
        u = P.unrank(r)
        stack = [(list_to_word([EMPTY] + u), 0)]
        while stack:
            s, j = stack.pop(); nodes += 1
            if j == n + 1:
                if get_slot(s, n + 1) == EMPTY:
                    leaves += 1; nnz.add((s, r))
                continue
            for t in successors(s, i, j, n):
                stack.append((t, j + 1))
    return P.size, leaves, nodes, len(nnz)

print(f"{'n':>2} {'B(n)':>8} {'sweep work/row':>15} {'DFS leaves=sum(T)':>18} {'DFS nodes':>12} "
      f"{'nnz(T)':>10} {'leaves/B':>9} {'nodes/sweep':>11}")
prev = None
for n in range(3, 12):
    B, leaves, nodes, nnz = row_dfs_stats(n)
    sweep = (n + 1) * 2 * B
    g = f"  x{leaves / B / prev:.2f}" if prev else ""
    print(f"{n:>2} {B:>8} {sweep:>15} {leaves:>18} {nodes:>12} {nnz:>10} {leaves / B:>9.2f} {nodes / sweep:>11.2f}{g}")
    prev = leaves / B
