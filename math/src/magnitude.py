"""How big is a(28)?  Fit log a(n) = kappa*n^2 + b*n + c*log n + d and use it to
size the CRT prime set for a modular computation."""
import math

EXACT = {1:2, 2:12, 3:184, 4:8512, 5:1262816, 6:575780564, 7:789360053252,
         8:3266598486981642, 9:41044208702632496804,
         10:1568758030464750013214100,
         11:182413291514248049241470885236,
         12:64528039343270018963357185158482118}

def solve(A, b):
    m = len(A)
    A = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(m):
        p = max(range(i, m), key=lambda k: abs(A[k][i])); A[i], A[p] = A[p], A[i]
        for k in range(i + 1, m):
            f = A[k][i] / A[i][i]
            for j in range(i, m + 1): A[k][j] -= f * A[i][j]
    x = [0.0] * m
    for i in reversed(range(m)):
        x[i] = (A[i][m] - sum(A[i][j] * x[j] for j in range(i + 1, m))) / A[i][i]
    return x

def fit(ns, basis):
    A = [[0.0] * len(basis) for _ in basis]; rhs = [0.0] * len(basis)
    for n in ns:
        x = [f(n) for f in basis]; y = math.log(EXACT[n])
        for i in range(len(basis)):
            for j in range(len(basis)): A[i][j] += x[i] * x[j]
            rhs[i] += x[i] * y
    return solve(A, rhs)

basis = [lambda n: n * n, lambda n: n, lambda n: math.log(n), lambda n: 1.0]
for lo in (5, 7, 8):
    ns = [n for n in sorted(EXACT) if n >= lo]
    c = fit(ns, basis)
    pred = lambda n: sum(ci * f(n) for ci, f in zip(c, basis))
    resid = max(abs(pred(n) - math.log(EXACT[n])) for n in ns)
    lam = math.exp(c[0])
    print("fit n=%2d..12: lambda=exp(kappa)=%.6f  b=%.4f c=%.3f d=%.3f  max|resid|=%.2e"
          % (lo, lam, c[1], c[2], c[3], resid))
    for n in (26, 27, 28):
        d10 = pred(n) / math.log(10)
        bits = pred(n) / math.log(2)
        print("     a(%d): ~%.1f decimal digits, ~%.0f bits -> %d primes of 62 bits"
              % (n, d10, bits, math.ceil(bits / 62) + 1))
print()
print("Known growth constant for SAWs crossing a square (Bousquet-Melou-Guttmann-Jensen):"
      "\n  lambda = 1.744550 ...  =>  log10 a(28) ~ 28^2 * log10(lambda) = %.1f digits"
      % (784 * math.log10(1.744550)))
