"""Singular-value decay of the DP vector across a frontier bipartition.

The exact Schmidt rank is maximal (src/schmidt.py), so no EXACT tensor-network
compression exists.  What is still open is whether the spectrum decays fast
enough that an APPROXIMATE matrix-product / corner-transfer method could deliver
many correct leading bits of a(n) cheaply -- every bit it delivers is a bit the
CRT no longer has to cover.
"""
import sys, math
sys.path.insert(0, "src")
import numpy as np
from schmidt import label
from hankel import row_ops

BIG = 1 << 4000                     # effectively exact integer arithmetic

def biggest_block(W):
    v, step, _ = row_ops(W, BIG)
    for _ in range(max(1, W // 2)):
        v = step(v)
    c = W // 2
    blocks = {}
    for word, val in v.items():
        lab = label(word, c)
        if lab is None: continue
        blocks.setdefault(lab, {})[(word[:c], word[c:])] = val
    return max(blocks.values(), key=len)

if __name__ == "__main__":
    hi = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    print(" W    block      sigma_k / sigma_1  at k = 1, 2, 4, 8, 16, 32        "
          "bits gained per extra chi")
    for W in range(6, hi + 1):
        cells = biggest_block(W)
        ls = sorted({a for a, _ in cells}); rs = sorted({b for _, b in cells})
        li = {a: i for i, a in enumerate(ls)}; ri = {b: i for i, b in enumerate(rs)}
        mx = max(cells.values())
        M = np.zeros((len(ls), len(rs)))
        for (a, b), val in cells.items():
            M[li[a], ri[b]] = float(val) / float(mx)
        s = np.linalg.svd(M, compute_uv=False)
        s = s / s[0]
        picks = [k for k in (1, 2, 4, 8, 16, 32) if k <= len(s)]
        dec = "  ".join("%.1e" % s[k - 1] for k in picks)
        kk = min(len(s), 32)
        rate = -math.log2(max(s[kk - 1], 1e-300)) / kk
        print("%3d  %4dx%-4d  %-52s %.2f" % (W, len(ls), len(rs), dec, rate))
