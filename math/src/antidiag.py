"""Paths invariant under the anti-diagonal reflection  rho*tau : (i,j) -> (n-j, n-i).

STRUCTURE THEOREM.  The grid is bipartite and s=(0,0), t=(n,n) have the same
colour, so every s-t path has even length, hence an odd number of vertices, so
the automorphism that rho*tau induces on such a path fixes exactly one vertex.
Every anti-diagonal vertex of the path is fixed by rho*tau, so the path meets
the anti-diagonal in EXACTLY ONE vertex m, and

    P  =  A  +  m  +  reverse(rho*tau(A))

where A is a self-avoiding path from s to some u with i+j = n-1, lying inside
the closed triangle T = {i+j <= n-1}.  Each u has exactly two anti-diagonal
neighbours, so

    F_{rho*tau}(n) = 2 * #{ self-avoiding paths from (0,0) to the hypotenuse of T }.

The DP sweeps T row by row.  Both loose ends need a marker: the one growing from
s, and the one left behind once the walk stops at its hypotenuse endpoint u.
Both u and s sit on the boundary of the processed region, so each marked
fragment cuts that region in two and NO arc can straddle either marker -- the
profile word therefore splits at the two markers into three balanced Motzkin
blocks, and the state count only triples rather than growing by a factor of n.
"""
import sys
sys.path.insert(0, "src")
from frontier import EMPTY, OPEN, CLOSE, MARK, partner

def successors2(state, j, is_start, can_down, can_right, at_u):
    """Successors at one vertex, with up to two free-end markers.

    Returns (list of states, completed_weightless_flag) where the flag says the
    walk closed here; the caller checks that nothing else is still open.
    """
    L, U = state[j], state[j + 1]
    s = list(state)
    out, done = [], False

    def put(d, r):
        if (d != EMPTY and not can_down) or (r != EMPTY and not can_right):
            return
        t = s[:]
        t[j], t[j + 1] = d, r
        out.append(tuple(t))

    if is_start:
        put(MARK, EMPTY); put(EMPTY, MARK)
        return out, False

    nmark = state.count(MARK)

    if L == EMPTY and U == EMPTY:
        put(EMPTY, EMPTY)
        put(OPEN, CLOSE)
        return out, False

    if (L == EMPTY) != (U == EMPTY):
        x = L if U == EMPTY else U
        put(x, EMPTY); put(EMPTY, x)
        if at_u and nmark == 1 and x != MARK:
            # the walk stops here: the arriving end is capped, its partner
            # becomes the second free end
            q = partner(state, j if U == EMPTY else j + 1)
            t = s[:]; t[j] = t[j + 1] = EMPTY; t[q] = MARK
            out.append(tuple(t))
        if at_u and nmark == 1 and x == MARK:
            # the start fragment itself ends at u: the path is complete
            t = s[:]; t[j] = t[j + 1] = EMPTY
            if all(c == EMPTY for c in t):
                done = True
        return out, done

    # both plugs arrive
    if L == OPEN and U == CLOSE:
        return out, False                      # would close a cycle
    if L == MARK and U == MARK:
        t = s[:]; t[j] = t[j + 1] = EMPTY
        if all(c == EMPTY for c in t):
            done = True                        # the two ends meet: path complete
        return out, done
    if L == MARK or U == MARK:
        q = partner(state, j + 1 if L == MARK else j)
        s[q] = MARK
        put(EMPTY, EMPTY)
        return out, False
    p, q = partner(state, j), partner(state, j + 1)
    lo, hi = (p, q) if p < q else (q, p)
    s[lo], s[hi] = OPEN, CLOSE
    put(EMPTY, EMPTY)
    return out, False

def half_paths(n, p=None):
    if n == 1:
        return 1, 1
    W = n + 1
    red = (lambda x: x % p) if p else (lambda x: x)
    layer = {(EMPTY,) * W: 1}
    answer, peak = 0, 0
    for i in range(n):
        last = n - 1 - i
        for j in range(last + 1):
            is_start = (i == 0 and j == 0)
            at_u = (j == last)
            nxt = {}
            for st, v in layer.items():
                outs, done = successors2(st, j, is_start,
                                         not at_u, not at_u, at_u)
                for ns in outs:
                    nxt[ns] = red(nxt.get(ns, 0) + v)
                if done:
                    answer = red(answer + v)
            layer = nxt
            peak = max(peak, len(layer))
        layer = {(EMPTY,) + st[:W - 1]: v for st, v in layer.items()
                 if st[W - 1] == EMPTY}
    return answer, peak

if __name__ == "__main__":
    BRUTE = {1: 2, 2: 4, 3: 12, 4: 48, 5: 288}
    hi = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    print("  n   F_rho*tau(n)                        check      triangle peak states")
    for n in range(1, hi + 1):
        a, peak = half_paths(n)
        f = 2 * a
        chk = ("OK" if f == BRUTE[n] else "FAIL(exp %d)" % BRUTE[n]) if n in BRUTE else "-"
        print("%3d   %-35d %-11s %d" % (n, f, chk, peak))
