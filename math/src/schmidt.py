"""Exact Schmidt rank of the DP vector across a bipartition of the frontier.

The Hankel bound (NEW-STRUCTURE.md) rules out smaller LINEAR realisations.  It
says nothing about representing the DP vector itself in compressed form.  Split
the profile word at position c:

    word = l | r

Because the bracket word is balanced and no arc straddles the MARK, l and r only
communicate through the label (which side holds the MARK, how many arcs cross
the cut).  So the vector is block diagonal over ~2W labels, and

    Schmidt rank = sum over labels of rank( V_label[l][r] ).

If that rank is far below sum of min(|L|,|R|), the DP vector is an exact matrix
product state with small bond dimension and the whole 3^W wall collapses.  If it
is essentially full, tensor-network methods can only ever be approximate -- still
useful (they would supply high-order bits and cut the CRT prime count), but not
exact.  Either way this measurement decides it.
"""
import sys
sys.path.insert(0, "src")
from frontier import EMPTY, OPEN, CLOSE, MARK
from hankel import row_ops

P = (1 << 61) - 1

def rank_mod(rows, ncol, p=P):
    """Gaussian elimination over GF(p); rows is a list of lists."""
    r = 0
    rows = [row[:] for row in rows]
    for col in range(ncol):
        piv = None
        for i in range(r, len(rows)):
            if rows[i][col] % p:
                piv = i; break
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        inv = pow(rows[r][col], p - 2, p)
        rows[r] = [(x * inv) % p for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col]:
                f = rows[i][col]
                rows[i] = [(a - f * b) % p for a, b in zip(rows[i], rows[r])]
        r += 1
        if r == len(rows):
            break
    return r

def label(word, c):
    """(side of the MARK, number of arcs crossing the cut) or None if invalid."""
    m = word.index(MARK)
    depth = 0
    for k in range(c):
        if word[k] == OPEN: depth += 1
        elif word[k] == CLOSE: depth -= 1
        if depth < 0: return None
    return (0 if m < c else 1, depth)

def analyse(W, rows_done=None):
    v, step, _ = row_ops(W, P)
    for _ in range(rows_done if rows_done is not None else max(1, W // 2)):
        v = step(v)
    c = W // 2
    blocks = {}
    for word, val in v.items():
        lab = label(word, c)
        if lab is None: continue
        blocks.setdefault(lab, {})[(word[:c], word[c:])] = val
    tot_rank = tot_max = 0
    for lab, cells in blocks.items():
        ls = sorted({a for a, _ in cells}); rs = sorted({b for _, b in cells})
        li = {a: i for i, a in enumerate(ls)}; ri = {b: i for i, b in enumerate(rs)}
        mat = [[0] * len(rs) for _ in ls]
        for (a, b), val in cells.items():
            mat[li[a]][ri[b]] = val % P
        tot_rank += rank_mod(mat, len(rs))
        tot_max += min(len(ls), len(rs))
    return len(v), tot_rank, tot_max

if __name__ == "__main__":
    hi = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print("  W   |support|   Schmidt rank   max possible   rank/max")
    for W in range(4, hi + 1):
        n, r, mx = analyse(W)
        print("%3d %10d %14d %14d %10.4f" % (W, n, r, mx, r / mx))
