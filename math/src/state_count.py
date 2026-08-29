"""Exact closed form for the number of frontier states.

Empirically the reachable set at a row boundary saturates after a few rows and
then equals exactly the set of profile words

    (Motzkin word of length a) MARK (Motzkin word of length b),   a + b = n

i.e. balanced-bracket words on n+1 slots carrying one MARK that no arc
straddles.  (Planarity forces this: the fragment containing the start corner
cuts the processed region in two, so no arc can have one end on each side.)

Hence   boundary(n) = sum_{a+b=n} M_a M_b = [x^n] M(x)^2 = M_{n+2} - M_{n+1}
and the mid-row peak is exactly twice that.
"""
MEASURED_PEAK = {2:10, 3:24, 4:60, 5:152, 6:392, 7:1024, 8:2706, 9:7220,
                 10:19426, 11:52648, 12:143598, 13:393876, 14:1085790,
                 15:3006624, 16:8359206, 17:23325804}

def motzkin(N):
    M = [1, 1]
    while len(M) <= N:
        n = len(M) - 1                      # (n+2)M_{n+1} = (2n+3)M_n + 3n M_{n-1}
        M.append(((2 * n + 3) * M[n] + 3 * n * M[n - 1]) // (n + 3))
    return M

M = motzkin(40)
# independent check of the recurrence against the convolution definition
for k in range(2, 20):
    conv = M[k - 1] + sum(M[i] * M[k - 2 - i] for i in range(k - 1))
    assert conv == M[k], (k, conv, M[k])

print("Verification of  peak(n) = 2 * (M_{n+2} - M_{n+1}):")
bad = 0
for n, p in sorted(MEASURED_PEAK.items()):
    pred = 2 * (M[n + 2] - M[n + 1])
    ok = "OK" if pred == p else "MISMATCH"
    if pred != p: bad += 1
    print("  n=%2d  measured=%12d  formula=%12d  %s" % (n, p, pred, ok))
print("  -> %d mismatches over n=2..%d\n" % (bad, max(MEASURED_PEAK)))

print("Exact state counts and memory, 8 bytes per state (one residue mod p):")
print("  n      boundary states      mid-row peak      boundary GB    mid-row GB")
for n in list(range(16, 21)) + [24, 25, 26, 27, 28, 29, 30]:
    b = M[n + 2] - M[n + 1]
    print("  %-4d %18d %17d %14.1f %13.1f"
          % (n, b, 2 * b, b * 8 / 2**30, 2 * b * 8 / 2**30))
