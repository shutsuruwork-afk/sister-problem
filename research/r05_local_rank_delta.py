"""r05: an automaton ranking under which most transitions change the rank
by a quantity that depends only on two positions.

Profiles: words of length L=n+1 over {0,(,),M}, balanced, exactly one M,
M only at depth 0.  Rank = lexicographic rank with symbol order
0 < ( < ) < M, computed by a (depth, mark_seen) automaton.

Claim checked here, exhaustively over every reachable transition:
if the vertex does not rewrite a distant partner slot, then
  rank(u_after) - rank(u_before) = local(u_before[j-1:j+1] -> u_after[j-1:j+1], state at j-1)
because the automaton state after position j is identical on both sides.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kaggle'))
from a007764_core import *

class AutoRanker:
    def __init__(self, n):
        self.n = n; L = self.L = n + 1
        C = [[[0, 0] for _ in range(L + 2)] for _ in range(L + 1)]
        C[0][0][1] = 1
        for rem in range(1, L + 1):
            for d in range(L + 1):
                for m in (0, 1):
                    v = C[rem-1][d][m] + C[rem-1][d+1][m]
                    if d > 0: v += C[rem-1][d-1][m]
                    if m == 0 and d == 0: v += C[rem-1][0][1]
                    C[rem][d][m] = v
        self.C = C; self.size = C[L][0][0]

    def step(self, c, d, m):
        if c == EMPTY: return d, m
        if c == OPEN: return d + 1, m
        if c == CLOSE: return (d - 1, m) if d > 0 else None
        return (0, 1) if (m == 0 and d == 0) else None

    def contrib(self, c, d, m, rem):
        """count of words that agree so far and put a smaller symbol here"""
        tot = 0
        for c2 in (EMPTY, OPEN, CLOSE, MARK):
            if c2 == c: return tot
            ns = self.step(c2, d, m)
            if ns: tot += self.C[rem][ns[0]][ns[1]]
        raise AssertionError

    def rank(self, w, start=0, state=(0, 0)):
        d, m = state; r = 0
        for i in range(start, self.L):
            r += self.contrib(w[i], d, m, self.L - i - 1)
            d, m = self.step(w[i], d, m)
        return r

    def prefix_state(self, w, k):
        d, m = 0, 0
        for i in range(k): d, m = self.step(w[i], d, m)
        return d, m

    def unrank(self, r):
        w, d, m = [], 0, 0
        for i in range(self.L):
            rem = self.L - i - 1
            for c in (EMPTY, OPEN, CLOSE, MARK):
                ns = self.step(c, d, m)
                if not ns: continue
                k = self.C[rem][ns[0]][ns[1]]
                if r < k: w.append(c); d, m = ns; break
                r -= k
        return w

import itertools
for n in range(1, 10):
    A, P = AutoRanker(n), ProfileRanker(n)
    assert A.size == P.size, (n, A.size, P.size)
    if n <= 7:
        for r in range(A.size):
            assert A.rank(A.unrank(r)) == r
print("automaton ranking: size == B(n) for n=1..9, rank/unrank round-trip n<=7  OK")

for n in range(3, 10):
    A = AutoRanker(n); W = n + 2
    local_ok = local_n = join_n = 0
    for i in (1,):                                  # generic middle row
        for j in range(n + 1):
            for r in range(A.size):
                u = A.unrank(r)
                if j == 0:
                    s = [EMPTY] + u; lo = 0
                else:
                    for b in (0, 1):
                        pass
                variants = [(None, [EMPTY] + u)] if j == 0 else [(b, expand(u, b, j - 1)) for b in (0, 1)]
                for b, s in variants:
                    if j > 0 and contract(s, j - 1)[0] != u: continue
                    L_, U_ = s[j], s[j + 1]
                    joins = L_ != EMPTY and U_ != EMPTY and not (L_ == OPEN and U_ == CLOSE)
                    for t in successors(list_to_word(s), i, j, n):
                        u2, b2 = contract(word_to_list(t, W), j)
                        if joins:
                            join_n += 1; continue
                        local_n += 1
                        lo = max(0, j - 1); hi = j + 1           # positions lo..j differ
                        st = A.prefix_state(u, lo)
                        d1 = A.rank(u2[:hi] + [None]*0, lo, st) if False else None
                        # local delta: rank over positions lo..j only, suffix state must coincide
                        def part(w):
                            d, m = st; r = 0
                            for k in range(lo, hi):
                                r += A.contrib(w[k], d, m, A.L - k - 1); d, m = A.step(w[k], d, m)
                            return r, (d, m)
                        pa, sa = part(u); pb, sb = part(u2)
                        assert sa == sb, (n, j, u, u2)
                        if A.rank(u2) - A.rank(u) == pb - pa: local_ok += 1
    print(f"  n={n}: transitions local={local_n:7d} (delta exact: {local_ok == local_n})  "
          f"partner-joins={join_n:6d}  join share={join_n / (local_n + join_n):.3f}")
