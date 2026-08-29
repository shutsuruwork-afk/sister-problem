"""Broken-profile frontier DP for A007764 (self-avoiding corner-to-corner
paths on the (n+1)x(n+1) vertex grid).

Slot layout, before processing vertex (i, j) of a grid with C = n+1 columns:

    slots 0 .. j-1 : vertical plugs at columns 0..j-1, crossing row i -> i+1
    slot  j        : horizontal plug between (i, j-1) and (i, j)
    slots j+1 .. C : vertical plugs at columns j..C-1, crossing row i-1 -> i

so there are W = C + 1 slots and the pair (slot j, slot j+1) holds exactly the
two plugs entering (i, j).  After the vertex is processed the same two slots
hold the two plugs leaving it (down, right).  The frontier is a staircase, so
the plug ordering is planar and connectivity is a NON-CROSSING partial
matching.  Symbols:

    0 : no plug
    1 : plug that is the left end of an arc   ( '(' )
    2 : plug that is the right end of an arc  ( ')' )
    3 : the single free end of the fragment containing the start corner

The bracket sequence formed by the 1/2 symbols is balanced, so partners are
determined by bracket matching and never need to be stored.
"""

EMPTY, OPEN, CLOSE, MARK = 0, 1, 2, 3


def partner(state, k):
    """Index matched with slot k under bracket matching (state[k] in {1,2})."""
    if state[k] == OPEN:
        depth = 0
        for t in range(k + 1, len(state)):
            if state[t] == OPEN:
                depth += 1
            elif state[t] == CLOSE:
                if depth == 0:
                    return t
                depth -= 1
    else:
        depth = 0
        for t in range(k - 1, -1, -1):
            if state[t] == CLOSE:
                depth += 1
            elif state[t] == OPEN:
                if depth == 0:
                    return t
                depth -= 1
    raise AssertionError("unbalanced state %r at %d" % (state, k))


def successors(state, j, is_start, is_end, can_down, can_right):
    """Yield the states reachable by processing one vertex.

    `state` is a tuple of length W; slots j and j+1 are the incoming
    (left, up) plugs and become the outgoing (down, right) plugs.
    """
    L, U = state[j], state[j + 1]
    s = list(state)

    def emit(d, r):
        if d != EMPTY and not can_down:
            return
        if r != EMPTY and not can_right:
            return
        s[j], s[j + 1] = d, r
        yield tuple(s)

    if is_start:
        # degree 1: exactly one plug leaves, carrying the free-end marker
        assert L == EMPTY and U == EMPTY
        yield from emit(MARK, EMPTY)
        yield from emit(EMPTY, MARK)
        return

    if is_end:
        # degree 1: exactly one plug arrives, and it must be the marked end
        if (L == MARK) != (U == MARK):
            if L == EMPTY or U == EMPTY:
                yield from emit(EMPTY, EMPTY)
        return

    if L == EMPTY and U == EMPTY:
        yield from emit(EMPTY, EMPTY)          # vertex unused
        yield from emit(OPEN, CLOSE)           # vertex is a corner: new arc
        return

    if L != EMPTY and U == EMPTY:
        yield from emit(L, EMPTY)              # continue downwards
        yield from emit(EMPTY, L)              # continue to the right
        return

    if L == EMPTY and U != EMPTY:
        yield from emit(U, EMPTY)
        yield from emit(EMPTY, U)
        return

    # both plugs arrive: the vertex has degree 2 and joins the two fragments
    if L == OPEN and U == CLOSE:
        return                                  # would close a cycle
    if L == MARK:
        q = partner(state, j + 1)
        s[q] = MARK
    elif U == MARK:
        p = partner(state, j)
        s[p] = MARK
    else:
        p, q = partner(state, j), partner(state, j + 1)
        lo, hi = (p, q) if p < q else (q, p)
        s[lo], s[hi] = OPEN, CLOSE
    yield from emit(EMPTY, EMPTY)


def count_paths(n, verbose=False):
    """Number of self-avoiding paths from (0,0) to (n,n) on the grid graph."""
    C = n + 1                      # vertices per row
    W = C + 1                      # profile slots
    layer = {tuple([EMPTY] * W): 1}
    widths = []
    for i in range(C):
        for j in range(C):
            is_start = (i == 0 and j == 0)
            is_end = (i == C - 1 and j == C - 1)
            can_down = (i < C - 1)
            can_right = (j < C - 1)
            nxt = {}
            for st, v in layer.items():
                for ns in successors(st, j, is_start, is_end, can_down, can_right):
                    nxt[ns] = nxt.get(ns, 0) + v
            layer = nxt
            widths.append(len(layer))
        # end of row: slot C holds the outgoing horizontal plug (always empty),
        # shift the profile right so that slot 0 is the incoming one
        layer = {(EMPTY,) + st[:C]: v for st, v in layer.items() if st[C] == EMPTY}
    if verbose:
        print("  peak layer width:", max(widths))
    return layer.get(tuple([EMPTY] * W), 0), max(widths)


if __name__ == "__main__":
    import sys
    nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    for n in range(1, nmax + 1):
        v, w = count_paths(n)
        print("%2d %-60s peak_states=%d" % (n, v, w))
