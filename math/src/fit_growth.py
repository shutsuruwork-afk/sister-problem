"""Fit peak frontier-state counts to C * mu^n * n^-beta and extrapolate."""
import math

# n -> peak number of reachable frontier states (measured with dp2.c)
PEAK = {1:2, 2:10, 3:24, 4:60, 5:152, 6:392, 7:1024, 8:2706, 9:7220,
        10:19426, 11:52648, 12:143598, 13:393876, 14:1085790, 15:3006624}

def fit(ns):
    """Least squares on ln peak = ln C + n ln mu - beta ln n."""
    rows = [(1.0, n, -math.log(n), math.log(PEAK[n])) for n in ns]
    # normal equations for 3 unknowns
    import itertools
    A = [[0.0]*3 for _ in range(3)]; b = [0.0]*3
    for r in rows:
        x = r[:3]; y = r[3]
        for i in range(3):
            for j in range(3): A[i][j] += x[i]*x[j]
            b[i] += x[i]*y
    # gaussian elimination
    for i in range(3):
        p = max(range(i,3), key=lambda k: abs(A[k][i]))
        A[i],A[p] = A[p],A[i]; b[i],b[p] = b[p],b[i]
        for k in range(i+1,3):
            f = A[k][i]/A[i][i]
            for j in range(i,3): A[k][j] -= f*A[i][j]
            b[k] -= f*b[i]
    x = [0.0]*3
    for i in reversed(range(3)):
        s = b[i] - sum(A[i][j]*x[j] for j in range(i+1,3))
        x[i] = s/A[i][i]
    lnC, lnmu, beta = x
    return math.exp(lnC), math.exp(lnmu), beta

if __name__ == "__main__":
    import sys
    hi = max(PEAK)
    for lo in (8, 10, 11):
        ns = [n for n in sorted(PEAK) if lo <= n <= hi]
        C, mu, beta = fit(ns)
        pred = lambda n: C * mu**n * n**(-beta)
        err = max(abs(pred(n)/PEAK[n]-1) for n in ns)
        print("fit n=%d..%d : mu=%.4f beta=%.3f C=%.4f  (max rel. resid %.2e)"
              % (lo, hi, mu, beta, C, err))
        for n in (20, 24, 26, 27, 28):
            v = pred(n)
            print("    peak(%2d) ~ %.3e states  -> %6.1f TB at 16 B/state, %6.1f TB at 8 B/state"
                  % (n, v, v*16/1e12, v*8/1e12))
