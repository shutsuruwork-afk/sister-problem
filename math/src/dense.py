"""Frontier DP on a DENSE, rank-indexed array -- no hash table, no keys.

Every layer is a flat array of residues whose length is EXACTLY the number of
states the layer can hold:

  * row-boundary layer : B(n)   = M_{n+2} - M_{n+1}
  * mid-row layer      : 2*B(n)

The mid-row index comes from contracting the two slots the current vertex owns.
After processing vertex (i,j) those slots (D,R) can only be

    (0,0)   (x,0)   (0,x)   (OPEN,CLOSE) as an adjacent matched pair

because a vertex has degree 0 or 2 (or 1 at a terminal).  Contract them into a
single slot -- keeping x, or EMPTY for both (0,0) and the matched pair -- and
the result is again a valid length-(n+1) word.  One extra bit b separates the
two states that share a contracted word, so

    index = 2 * rank_valid(contracted word) + b

is a bijection onto [0, 2*B(n)).  That is the minimum possible: the layer has
exactly 2*B(n) states.
"""
import sys
sys.path.insert(0, "src")
from ranking import motzkin, rankM, unrankM, EMPTY, OPEN, CLOSE, MARK

def rank_valid(w, M):
    """Rank a valid word (one MARK, balanced, no arc straddling the MARK)."""
    L = len(w); m = L - 1
    a = w.index(MARK); b = m - a
    off = 0
    for x in range(a): off += M[x] * M[m - x]
    return off + rankM(w[:a]) * M[b] + rankM(w[a + 1:])

def unrank_valid(L, r, M):
    m = L - 1
    for a in range(L):
        blk = M[a] * M[m - a]
        if r < blk:
            b = m - a
            return unrankM(a, r // M[b]) + (MARK,) + unrankM(b, r % M[b])
        r -= blk
    raise IndexError(r)

def partner(w, k):
    if w[k] == OPEN:
        d = 0
        for t in range(k + 1, len(w)):
            if w[t] == OPEN: d += 1
            elif w[t] == CLOSE:
                if d == 0: return t
                d -= 1
    else:
        d = 0
        for t in range(k - 1, -1, -1):
            if w[t] == CLOSE: d += 1
            elif w[t] == OPEN:
                if d == 0: return t
                d -= 1
    raise AssertionError

def contract(w, j, M):
    """(profile after vertex (i,j)) -> dense index"""
    L, U = w[j], w[j + 1]
    if L == EMPTY and U == EMPTY: c, b = EMPTY, 0
    elif U == EMPTY:              c, b = L, 0
    elif L == EMPTY:              c, b = U, 1
    else:                         c, b = EMPTY, 1      # matched adjacent arc
    u = w[:j] + (c,) + w[j + 2:]
    return 2 * rank_valid(u, M) + b

def expand(idx, j, n, M):
    """dense index -> profile after vertex (i,j)"""
    u = unrank_valid(n + 1, idx >> 1, M); b = idx & 1
    c = u[j]
    if c == EMPTY: pair = (OPEN, CLOSE) if b else (EMPTY, EMPTY)
    else:          pair = (EMPTY, c) if b else (c, EMPTY)
    return u[:j] + pair + u[j + 1:]

def count_paths(n, p=None):
    M = motzkin(n + 4)
    C = n + 1
    B = M[n + 2] - M[n + 1]
    red = (lambda x: x % p) if p else (lambda x: x)

    # row-boundary layer: index = rank_valid(boundary word), length B
    cur = [0] * B
    # before any vertex the profile is all-EMPTY, which is not a valid word
    # (no MARK yet), so run row 0 from an explicit start
    start = {(EMPTY,) * (n + 2): 1}
    sizes = []
    answer = 0
    for i in range(C):
        for j in range(C):
            is_start = (i == 0 and j == 0)
            is_end = (i == C - 1 and j == C - 1)
            can_down, can_right = i < C - 1, j < C - 1
            nxt = [0] * (2 * B)
            src = (start.items() if (i == 0 and j == 0)
                   else ((expand(k, j - 1, n, M), v) for k, v in enumerate(cur) if v)
                        if j else
                        ((( EMPTY,) + unrank_valid(n + 1, k, M), v)
                         for k, v in enumerate(cur) if v))
            for w, v in src:
                L, U = w[j], w[j + 1]
                base = w[:j] + (EMPTY, EMPTY) + w[j + 2:]
                outs = []
                if is_start:
                    if can_down:  outs.append(base[:j] + (MARK, EMPTY) + base[j + 2:])
                    if can_right: outs.append(base[:j] + (EMPTY, MARK) + base[j + 2:])
                elif is_end:
                    # the path closes here; nothing is left to rank
                    if (L == MARK) != (U == MARK) and (L == EMPTY or U == EMPTY):
                        answer = red(answer + v)
                    continue
                elif L == EMPTY and U == EMPTY:
                    outs.append(base)
                    if can_down and can_right:
                        outs.append(base[:j] + (OPEN, CLOSE) + base[j + 2:])
                elif U == EMPTY:
                    if can_down:  outs.append(base[:j] + (L, EMPTY) + base[j + 2:])
                    if can_right: outs.append(base[:j] + (EMPTY, L) + base[j + 2:])
                elif L == EMPTY:
                    if can_down:  outs.append(base[:j] + (U, EMPTY) + base[j + 2:])
                    if can_right: outs.append(base[:j] + (EMPTY, U) + base[j + 2:])
                elif L == OPEN and U == CLOSE:
                    pass                                   # would close a cycle
                elif L == MARK:
                    q = partner(w, j + 1)
                    outs.append(base[:q] + (MARK,) + base[q + 1:])
                elif U == MARK:
                    q = partner(w, j)
                    outs.append(base[:q] + (MARK,) + base[q + 1:])
                else:
                    a2, b2 = partner(w, j), partner(w, j + 1)
                    lo, hi = min(a2, b2), max(a2, b2)
                    t = list(base); t[lo], t[hi] = OPEN, CLOSE
                    outs.append(tuple(t))
                for o in outs:
                    k = contract(o, j, M)
                    nxt[k] = red(nxt[k] + v)
            cur = nxt
            sizes.append(sum(1 for x in cur if x))
        # end of row: even indices hold (D, EMPTY); the contracted word is the
        # next row's boundary word
        nb = [0] * B
        for k, v in enumerate(cur):
            if v and (k & 1) == 0: nb[k >> 1] = v
        cur = nb
    return answer, max(sizes), 2 * B

if __name__ == "__main__":
    KNOWN = {1:2, 2:12, 3:184, 4:8512, 5:1262816, 6:575780564, 7:789360053252,
             8:3266598486981642, 9:41044208702632496804,
             10:1568758030464750013214100}
    print(" n   a(n) from dense DP                 matches   array len = 2B(n)   max live")
    for n in range(2, 11):
        tot, mx, ln = count_paths(n)
        ok = "OK" if tot == KNOWN[n] else "FAIL(%d)" % tot
        print("%2d  %-32d %-9s %14d %10d" % (n, tot, ok, ln, mx))
