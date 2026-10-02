"""r03: smallest residue width b such that pairwise-coprime moduli < 2^b
can carry a(28).

The largest product of pairwise-coprime integers <= m is lcm(1..m)
(take the largest prime power p^k <= m for every prime p).  ROADMAP only
counted primes; prime powers are equally valid CRT moduli.
"""
import math

def primes_upto(m):
    s = bytearray([1]) * (m + 1); s[0:2] = b'\x00\x00'
    for p in range(2, int(m ** 0.5) + 1):
        if s[p]: s[p*p::p] = bytearray(len(s[p*p::p]))
    return [p for p in range(m + 1) if s[p]]

def best_moduli(m):
    out = []
    for p in primes_upto(m):
        q = p
        while q * p <= m: q *= p
        out.append(q)
    return out

NEED = 640        # a(28) ~ 629 bits (NOTES sec.3) plus margin
print(f"{'b':>3} {'primes only: bits':>18} {'with prime powers: bits':>24} {'moduli':>7}  carries a(28)?")
for b in range(7, 13):
    m = (1 << b) - 1
    ponly = sum(math.log2(p) for p in primes_upto(m))
    mods = best_moduli(m)
    pp = sum(math.log2(q) for q in mods)
    print(f"{b:>3} {ponly:>18.1f} {pp:>24.1f} {len(mods):>7}  {'yes' if pp >= NEED else 'no'}")

# minimum number of 9-bit moduli actually needed, largest first
mods = sorted(best_moduli(511), reverse=True)
acc = 0
for k, q in enumerate(mods, 1):
    acc += math.log2(q)
    if acc >= NEED: break
print(f"\n9-bit: {k} moduli suffice ({acc:.1f} bits); n=28 peak storage at 9 bit = "
      f"{2207285372764 * 9 / 8 / 2**40:.2f} TiB per buffer")
