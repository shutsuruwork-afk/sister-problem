"""Bijective ranking of frontier states.

A row-boundary state on L = n+1 slots is

    w = (Motzkin word of length a) MARK (Motzkin word of length b),  a + b = n

so the state set is the disjoint union over a of  S_a x S_b, and

    rank(w) = sum_{a'<a} M_{a'} M_{n-a'} + rankM(left) * M_b + rankM(right)

is a bijection onto [0, sum_{a+b=n} M_a M_b) = [0, M_{n+2} - M_{n+1}).

That is what lets the DP layer be a DENSE ARRAY of residues indexed by rank:
8 bytes per state, no keys, no hash table, no load-factor slack.
"""
from functools import lru_cache

EMPTY, OPEN, CLOSE, MARK = 0, 1, 2, 3

def motzkin(N):
    M = [1, 1]
    while len(M) <= N:
        n = len(M) - 1
        M.append(((2 * n + 3) * M[n] + 3 * n * M[n - 1]) // (n + 3))
    return M

@lru_cache(maxsize=None)
def _tab(k):
    """T[i][h] = number of balanced completions of a length-k Motzkin word from
    position i at height h."""
    T = [[0] * (k + 2) for _ in range(k + 1)]
    T[k][0] = 1
    for i in range(k - 1, -1, -1):
        for h in range(k + 1):
            v = T[i + 1][h] + T[i + 1][h + 1]
            if h: v += T[i + 1][h - 1]
            T[i][h] = v
    return T

def rankM(word):
    """Rank a balanced Motzkin word (symbols EMPTY/OPEN/CLOSE) in [0, M_k)."""
    k = len(word); T = _tab(k); r = 0; h = 0
    for i, c in enumerate(word):
        if c == OPEN:                       # EMPTY sorts first
            r += T[i + 1][h]
        elif c == CLOSE:
            r += T[i + 1][h] + T[i + 1][h + 1]
        h += (1 if c == OPEN else -1 if c == CLOSE else 0)
        assert h >= 0
    assert h == 0
    return r

def unrankM(k, r):
    T = _tab(k); out = []; h = 0
    for i in range(k):
        c0 = T[i + 1][h]
        if r < c0:
            out.append(EMPTY)
        else:
            r -= c0
            c1 = T[i + 1][h + 1]
            if r < c1: out.append(OPEN); h += 1
            else: r -= c1; out.append(CLOSE); h -= 1
    assert h == 0 and r == 0
    return tuple(out)

def rank_state(w, M):
    """Rank a boundary state (length n+1, exactly one MARK, no arc across it)."""
    L = len(w); n = L - 1
    a = w.index(MARK); b = n - a
    off = sum(M[x] * M[n - x] for x in range(a))
    return off + rankM(w[:a]) * M[b] + rankM(w[a + 1:])

def unrank_state(n, r, M):
    for a in range(n + 1):
        blk = M[a] * M[n - a]
        if r < blk:
            b = n - a
            return unrankM(a, r // M[b]) + (MARK,) + unrankM(b, r % M[b])
        r -= blk
    raise IndexError

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from useful import layers
    M = motzkin(64)

    print("1) rank/unrank is a bijection onto [0, M_{n+2}-M_{n+1}):")
    for n in range(1, 11):
        tot = sum(M[a] * M[n - a] for a in range(n + 1))
        assert tot == M[n + 2] - M[n + 1], n
        seen = set()
        for r in range(tot):
            w = unrank_state(n, r, M)
            assert rank_state(w, M) == r
            seen.add(w)
        print("   n=%2d  |S|=%d = M_%d-M_%d  round-trip OK, %d distinct words"
              % (n, tot, n + 2, n + 1, len(seen)))

    print("\n2) the DP's saturated row-boundary set equals exactly that word set:")
    for n in range(3, 10):
        C = n + 1
        boundary = [s for tag, s in layers(n) if tag[0] == "shift"]
        full = {unrank_state(n, r, M) for r in range(M[n + 2] - M[n + 1])}
        # DP states carry C+1 slots with slot 0 emptied by the shift
        best = max(boundary, key=len)
        got = {s[1:] for s in best}
        print("   n=%2d  max boundary layer=%6d  predicted=%6d  sets equal: %s"
              % (n, len(best), len(full), got == full))
