"""How many frontier states actually matter?

The forward DP keeps every state reachable from the start.  A state only
contributes to the answer if it is ALSO co-reachable, i.e. some completion of
it yields a valid s-t path.  This script computes both sets exactly (by storing
every layer and running a backward marking pass) so we can see how much a
two-sided method could save.
"""
import sys
from frontier import EMPTY, successors

def layers(n):
    C = n + 1
    W = C + 1
    cur = {tuple([EMPTY] * W)}
    yield ("init", cur)
    for i in range(C):
        for j in range(C):
            args = (j, i == 0 and j == 0, i == C - 1 and j == C - 1,
                    i < C - 1, j < C - 1)
            nxt = set()
            for st in cur:
                nxt.update(successors(st, *args))
            cur = nxt
            yield (("v", i, j), cur)
        cur = {(EMPTY,) + st[:C] for st in cur if st[C] == EMPTY}
        yield (("shift", i), cur)

def analyse(n):
    C = n + 1
    W = C + 1
    ls = list(layers(n))
    # backward marking: a state is useful if some transition leads to a useful
    # state in the next layer
    accept = tuple([EMPTY] * W)
    useful = [None] * len(ls)
    useful[-1] = {accept} & ls[-1][1]
    for k in range(len(ls) - 2, -1, -1):
        tag = ls[k + 1][0]
        good = useful[k + 1]
        keep = set()
        if tag[0] == "shift":
            for st in ls[k][1]:
                if st[C] == EMPTY and (EMPTY,) + st[:C] in good:
                    keep.add(st)
        else:
            _, i, j = tag
            args = (j, i == 0 and j == 0, i == C - 1 and j == C - 1,
                    i < C - 1, j < C - 1)
            for st in ls[k][1]:
                for ns in successors(st, *args):
                    if ns in good:
                        keep.add(st); break
        useful[k] = keep
    reach_peak = max(len(l[1]) for l in ls)
    use_peak = max(len(u) for u in useful)
    tot_r = sum(len(l[1]) for l in ls)
    tot_u = sum(len(u) for u in useful)
    return reach_peak, use_peak, tot_r, tot_u

if __name__ == "__main__":
    hi = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(" n   reach_peak  useful_peak  peak_ratio   sum_reach   sum_useful  sum_ratio")
    for n in range(2, hi + 1):
        rp, up, tr, tu = analyse(n)
        print("%2d %11d %12d %11.4f %11d %12d %10.4f"
              % (n, rp, up, up / rp, tr, tu, tu / tr))
