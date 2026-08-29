"""What is the smallest linear DP that can count paths on a width-W strip?

c_W(h) = number of self-avoiding (0,0)->(h-1,W-1) paths on an h x W vertex grid
       = u . T^(h-2) . v
for the width-W row-transfer operator T.  Any such sequence obeys a linear
recurrence in h, and the order of the MINIMAL one is the Hankel rank r_W.

r_W is a hard floor: no linear method -- no clever quotient, no basis change --
can compute the whole family with fewer than r_W coordinates.  Comparing r_W
with the frontier state count B(W-1) = M_{W+1} - M_W therefore decides whether
the state space can be shrunk at all, or whether n=28 is purely an engineering
problem.
"""
import sys
sys.path.insert(0, "src")
from frontier import EMPTY, OPEN, CLOSE, MARK, successors
from ranking import motzkin

def row_ops(W, p):
    """Return (v, step, finish): initial vector, row transfer, closing functional."""
    def run_row(vec, first, last):
        # profile has W+1 slots; slot 0 is the horizontal plug entering the row
        cur = {(EMPTY,) + s: c for s, c in vec.items()} if not first else dict(vec)
        for j in range(W):
            nxt = {}
            args = (j, first and j == 0, last and j == W - 1, True, j < W - 1)
            for st, c in cur.items():
                for ns in successors(st, *args):
                    nxt[ns] = (nxt.get(ns, 0) + c) % p
            cur = nxt
        return {s[:W]: c for s, c in cur.items() if s[W] == EMPTY and c}

    empty_profile = {(EMPTY,) * (W + 1): 1}
    v = run_row(empty_profile, True, False)             # row 0, contains the start
    step = lambda vec: run_row(vec, False, False)
    def finish(vec):
        out = run_row(vec, False, True)
        return out.get((EMPTY,) * W, 0) % p
    return v, step, finish

def berlekamp_massey(s, p):
    C, B = [1], [1]
    L, m, b = 0, 1, 1
    for i in range(len(s)):
        d = s[i]
        for j in range(1, L + 1):
            d = (d + C[j] * s[i - j]) % p
        if d == 0:
            m += 1
        elif 2 * L <= i:
            T = C[:]
            coef = d * pow(b, p - 2, p) % p
            C += [0] * (len(B) + m - len(C))
            for j in range(len(B)):
                C[j + m] = (C[j + m] - coef * B[j]) % p
            L, B, b, m = i + 1 - L, T, d, 1
        else:
            coef = d * pow(b, p - 2, p) % p
            C += [0] * (len(B) + m - len(C))
            for j in range(len(B)):
                C[j + m] = (C[j + m] - coef * B[j]) % p
            m += 1
    return L

if __name__ == "__main__":
    P = (1 << 61) - 1
    M = motzkin(40)
    KNOWN = {1:2, 2:12, 3:184, 4:8512, 5:1262816, 6:575780564, 7:789360053252}
    hi = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print("  W   B(W-1)=M_{W+1}-M_W   terms   Hankel rank r_W   r_W/B(W-1)   a(W-1) check")
    for W in range(2, hi + 1):
        dim = M[W + 1] - M[W]
        v, step, finish = row_ops(W, P)
        seq, vec = [], v
        need = 2 * dim + 4
        square = None
        for h in range(2, need + 2):
            seq.append(finish(vec))
            if h == W:                      # the square case must reproduce a(W-1)
                square = seq[-1]
            vec = step(vec)
            if not vec: break
        r = berlekamp_massey(seq, P)
        chk = "-"
        if W - 1 in KNOWN:
            chk = "OK" if square == KNOWN[W - 1] % P else "FAIL"
        print("%3d %16d %8d %14d %12.4f   %s"
              % (W, dim, len(seq), r, r / dim, chk))
