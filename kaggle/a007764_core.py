"""Exact frontier DP for OEIS A007764 with rank-indexed dense storage.

This module is the trusted core: it implements only results that were
re-derived and verified from scratch (see AUDIT_PHASE1_PHASE2.md).

State space (math/NOTES.md sec.1, independently re-verified):
  A row-boundary profile is a word of length L = n+1 over
  {0, '(', ')', M} which factors uniquely as

      (Motzkin word of length a)  M  (Motzkin word of length b),   a + b = n

  because no arc can straddle the M plug.  Hence the number of
  row-boundary states is

      B(n) = sum_a M_a * M_{n-a} = M_{n+2} - M_{n+1}

  and the mid-row peak is exactly 2*B(n).

Symbols: 0 = EMPTY, 1 = OPEN '(', 2 = CLOSE ')', 3 = MARK.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

EMPTY, OPEN, CLOSE, MARK = 0, 1, 2, 3

KNOWN_A007764: Dict[int, int] = {
    1: 2,
    2: 12,
    3: 184,
    4: 8512,
    5: 1262816,
    6: 575780564,
    7: 789360053252,
    8: 3266598486981642,
    9: 41044208702632496804,
    10: 1568758030464750013214100,
    11: 182413291514248049241470885236,
    12: 64528039343270018963357185158482118,
}


# --------------------------------------------------------------------------
# Motzkin tables
# --------------------------------------------------------------------------
def motzkin_numbers(k_max: int) -> List[int]:
    """M[0..k_max] with M_k = #{Motzkin words of length k}."""
    M = [0] * (k_max + 1)
    M[0] = 1
    if k_max >= 1:
        M[1] = 1
    for k in range(2, k_max + 1):
        M[k] = M[k - 1] + sum(M[i] * M[k - 2 - i] for i in range(k - 1))
    return M


def completion_table(k_max: int) -> List[List[int]]:
    """T[rem][d] = #{ways to finish a Motzkin word: rem symbols left, depth d}."""
    T = [[0] * (k_max + 2) for _ in range(k_max + 1)]
    T[0][0] = 1
    for rem in range(1, k_max + 1):
        for d in range(0, k_max + 1):
            v = T[rem - 1][d]                       # place EMPTY
            v += T[rem - 1][d + 1]                  # place OPEN
            if d > 0:
                v += T[rem - 1][d - 1]              # place CLOSE
            T[rem][d] = v
    return T


# --------------------------------------------------------------------------
# Motzkin word ranking  (symbol order EMPTY < OPEN < CLOSE)
# --------------------------------------------------------------------------
def rank_motzkin(word: List[int], T: List[List[int]]) -> int:
    r, d = 0, 0
    k = len(word)
    for i, c in enumerate(word):
        rem = k - i - 1
        if c == OPEN:
            r += T[rem][d]
            d += 1
        elif c == CLOSE:
            r += T[rem][d] + T[rem][d + 1]
            d -= 1
        # EMPTY contributes 0
    assert d == 0
    return r


def unrank_motzkin(r: int, k: int, T: List[List[int]]) -> List[int]:
    word: List[int] = []
    d = 0
    for i in range(k):
        rem = k - i - 1
        c = T[rem][d]
        if r < c:
            word.append(EMPTY)
            continue
        r -= c
        c = T[rem][d + 1]
        if r < c:
            word.append(OPEN)
            d += 1
            continue
        r -= c
        word.append(CLOSE)
        d -= 1
    assert d == 0 and r == 0
    return word


# --------------------------------------------------------------------------
# Row-boundary profile ranking
#   word of length L = n+1  ==  (Motzkin len a) MARK (Motzkin len b),  a+b = n
#   rank = sum_{a'<a} M_a' * M_{n-a'}  +  rankM(left)*M_b  +  rankM(right)
# --------------------------------------------------------------------------
class ProfileRanker:
    """Bijective ranking of length-(n+1) boundary profiles onto [0, B(n))."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.L = n + 1
        self.M = motzkin_numbers(n + 4)
        self.T = completion_table(n + 4)
        # offset[a] = number of profiles whose MARK sits strictly left of a
        self.offset: List[int] = [0] * (n + 2)
        acc = 0
        for a in range(n + 1):
            self.offset[a] = acc
            acc += self.M[a] * self.M[n - a]
        self.offset[n + 1] = acc
        self.size = acc                      # == B(n) == M_{n+2} - M_{n+1}

    def rank(self, word: List[int]) -> int:
        a = word.index(MARK)
        b = self.L - 1 - a
        left, right = word[:a], word[a + 1:]
        return (self.offset[a]
                + rank_motzkin(left, self.T) * self.M[b]
                + rank_motzkin(right, self.T))

    def unrank(self, r: int) -> List[int]:
        a = 0
        while r >= self.offset[a + 1]:
            a += 1
        r -= self.offset[a]
        b = self.L - 1 - a
        ql, qr = divmod(r, self.M[b])
        return (unrank_motzkin(ql, a, self.T) + [MARK]
                + unrank_motzkin(qr, b, self.T))


# --------------------------------------------------------------------------
# Frontier (broken-profile) DP, word space.  Reference implementation.
#
# Frontier word s[0..W-1], W = n+2.  Before processing vertex (i,j):
#   s[k], k <  j    : DOWN plug already emitted by (i,k)
#   s[j]            : LEFT plug entering (i,j)
#   s[j+1]          : UP   plug entering (i,j)   (DOWN plug of (i-1,j))
#   s[k], k >  j+1  : UP   plugs for columns k-1
# After processing (i,j):  s[j] = DOWN plug, s[j+1] = RIGHT plug.
# End of row: require s[n+1] == EMPTY, then shift one slot right.
# --------------------------------------------------------------------------
def get_slot(s: int, k: int) -> int:
    return (s >> (2 * k)) & 3


def set_slot(s: int, k: int, v: int) -> int:
    return (s & ~(3 << (2 * k))) | (v << (2 * k))


def find_partner(s: int, k: int, W: int) -> int:
    """Index of the bracket matching slot k (which must hold OPEN or CLOSE)."""
    c = get_slot(s, k)
    depth = 0
    if c == OPEN:
        for t in range(k + 1, W):
            o = get_slot(s, t)
            if o == OPEN:
                depth += 1
            elif o == CLOSE:
                if depth == 0:
                    return t
                depth -= 1
    else:
        for t in range(k - 1, -1, -1):
            o = get_slot(s, t)
            if o == CLOSE:
                depth += 1
            elif o == OPEN:
                if depth == 0:
                    return t
                depth -= 1
    raise AssertionError("unmatched bracket")


def successors(s: int, i: int, j: int, n: int) -> List[int]:
    """All frontier words reachable by processing vertex (i,j) from word s."""
    W = n + 2
    L, U = get_slot(s, j), get_slot(s, j + 1)
    base = set_slot(set_slot(s, j, EMPTY), j + 1, EMPTY)
    can_down, can_right = i < n, j < n
    out: List[int] = []

    if i == 0 and j == 0:                                   # start vertex
        if L or U:
            return out
        if can_down:
            out.append(set_slot(base, j, MARK))
        if can_right:
            out.append(set_slot(base, j + 1, MARK))
        return out

    if i == n and j == n:                                   # terminal vertex
        if (L == MARK and U == EMPTY) or (U == MARK and L == EMPTY):
            out.append(base)
        return out

    if L == EMPTY and U == EMPTY:
        out.append(base)                                    # degree 0
        if can_down and can_right:                          # open a fresh arc
            out.append(set_slot(set_slot(base, j, OPEN), j + 1, CLOSE))
        return out

    if L == EMPTY or U == EMPTY:                            # straight / turn
        v = L if U == EMPTY else U
        if can_down:
            out.append(set_slot(base, j, v))
        if can_right:
            out.append(set_slot(base, j + 1, v))
        return out

    # both plugs occupied: the vertex joins two fragments, degree is now 2
    if L == OPEN and U == CLOSE:
        return out                                          # would close a cycle
    if L == MARK:
        q = find_partner(s, j + 1, W)
        return [set_slot(base, q, MARK)]
    if U == MARK:
        q = find_partner(s, j, W)
        return [set_slot(base, q, MARK)]
    a, b = find_partner(s, j, W), find_partner(s, j + 1, W)
    lo, hi = (a, b) if a < b else (b, a)
    return [set_slot(set_slot(base, lo, OPEN), hi, CLOSE)]


def a_n_wordspace(n: int, p: int | None = None) -> int:
    """Exact (or mod p) a(n) via dictionary-based frontier DP."""
    W = n + 2
    full = (1 << (2 * W)) - 1
    layer: Dict[int, int] = {0: 1}
    for i in range(n + 1):
        for j in range(n + 1):
            nxt: Dict[int, int] = {}
            for s, v in layer.items():
                for t in successors(s, i, j, n):
                    w = nxt.get(t, 0) + v
                    nxt[t] = w % p if p else w
            layer = nxt
        shifted: Dict[int, int] = {}
        for s, v in layer.items():
            if get_slot(s, n + 1) != EMPTY:
                continue
            t = (s << 2) & full
            w = shifted.get(t, 0) + v
            shifted[t] = w % p if p else w
        layer = shifted
    return layer.get(0, 0)


# --------------------------------------------------------------------------
# Dense rank-indexed DP  (math/NOTES.md sec.2, the genuine "A-class" result)
#
# After processing vertex (i,j) the two plugs at slots (j, j+1) can only be
#     (0,0)      (x,0)      (0,x)      ( '(' , ')' )
# so contracting those two slots into one gives a length-(n+1) boundary
# profile u plus one distinguishing bit b, and
#     index = 2 * rank(u) + b
# is a bijection onto [0, 2*B(n)).  No hash table, no keys, 100% occupancy.
# --------------------------------------------------------------------------
def word_to_list(s: int, W: int) -> List[int]:
    return [get_slot(s, k) for k in range(W)]


def list_to_word(xs: List[int]) -> int:
    s = 0
    for k, v in enumerate(xs):
        s |= v << (2 * k)
    return s


def contract(xs: List[int], j: int) -> Tuple[List[int], int]:
    """Fold slots (j, j+1) of a length-(n+2) word into one slot."""
    lo, hi = xs[j], xs[j + 1]
    if lo == EMPTY and hi == EMPTY:
        val, b = EMPTY, 0
    elif lo == OPEN and hi == CLOSE:
        val, b = EMPTY, 1
    elif hi == EMPTY:
        val, b = lo, 0
    elif lo == EMPTY:
        val, b = hi, 1
    else:
        raise AssertionError(f"illegal plug pair {(lo, hi)} at j={j}")
    return xs[:j] + [val] + xs[j + 2:], b


def expand(u: List[int], b: int, j: int) -> List[int]:
    """Inverse of contract()."""
    val = u[j]
    if val == EMPTY:
        pair = (EMPTY, EMPTY) if b == 0 else (OPEN, CLOSE)
    else:
        pair = (val, EMPTY) if b == 0 else (EMPTY, val)
    return u[:j] + [pair[0], pair[1]] + u[j + 1:]


def a_n_dense(n: int, p: int | None = None, report: bool = False) -> int:
    """Exact (or mod p) a(n) on a dense rank-indexed array of length 2*B(n).

    Two index spaces alternate:
      * row boundary  -> profile rank in [0, B(n))
      * mid row after vertex (i,j) -> 2*rank(contract_j(s)) + b in [0, 2*B(n))
    """
    P = ProfileRanker(n)
    W, size = n + 2, 2 * P.size
    peak = 0

    def word_before(idx, j, from_boundary):
        if from_boundary:
            return [EMPTY] + P.unrank(idx)            # word before (i,0)
        r, b = divmod(idx, 2)
        return expand(P.unrank(r), b, j - 1)          # word before (i,j)

    def step(cur, i, j, from_boundary):
        nxt = {}
        for idx, v in cur.items():
            xs = word_before(idx, j, from_boundary)
            for t in successors(list_to_word(xs), i, j, n):
                u2, b2 = contract(word_to_list(t, W), j)
                k = 2 * P.rank(u2) + b2
                w = nxt.get(k, 0) + v
                nxt[k] = w % p if p else w
        return nxt

    def terminal(cur, from_boundary):
        """Vertex (n,n): the MARK is consumed and the frontier empties out."""
        total = 0
        for idx, v in cur.items():
            xs = word_before(idx, n, from_boundary)
            for t in successors(list_to_word(xs), n, n, n):
                if t == 0:
                    total += v
        return (total % p) if p else total

    # seed: process the start vertex (0,0) from the empty frontier
    cur = {}
    for t in successors(0, 0, 0, n):
        u, b = contract(word_to_list(t, W), 0)
        k = 2 * P.rank(u) + b
        cur[k] = (cur.get(k, 0) + 1) % p if p else cur.get(k, 0) + 1
    peak = max(peak, len(cur))

    for i in range(n + 1):
        j0 = 1 if i == 0 else 0
        for j in range(j0, n + 1):
            if i == n and j == n:
                answer = terminal(cur, from_boundary=(j == 0))
                if report:
                    print(f"    n={n:2d}: array=2*B(n)={size:<14,} peak_live={peak:<14,} "
                          f"occupancy={peak / size:.4f}")
                return answer
            cur = step(cur, i, j, from_boundary=(j == 0))
            peak = max(peak, len(cur))
        # row end: contraction is at (n, n+1) and slot n+1 is always EMPTY,
        # so b == 0 and the next boundary profile rank is exactly idx >> 1
        cur = {idx >> 1: v for idx, v in cur.items() if not (idx & 1)}

    if report:
        print(f"    n={n:2d}: array=2*B(n)={size:<12,} peak_live={peak:<12,} "
              f"occupancy={peak / size:.4f}")
    return (sum(cur.values()) % p) if p else sum(cur.values())
