"""Experiment H-16: Higher-Order 2-adic Congruences for A007764.

Hypothesis (H-16):
Analyzing the 2-adic valuation v_2(a(n)) and higher-order congruences
a(n) mod 2^k (for k = 1, 2, 3, 4, 5, 6, 7, 8) reveals exact algebraic invariants
that fix the lowest k bits of a(28) without any DP computation.

Verification Protocol:
1. Tabulate a(n) mod 2^k for k in 1..8 across all known records n = 1..18.
2. Check if v_2(a(n)) grows with n (e.g. v_2(a(n)) >= floor(n/2) or similar).
3. Test if a(n) mod 16, mod 32, mod 64 follows a predictable periodic pattern for even/odd n.
"""

from __future__ import annotations
from typing import Dict

EXACT_RECORDS: Dict[int, int] = {
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
    13: 695191295289944747761005856997424900548,
    14: 227653609800798150495861186714022839958742296,
    15: 226922904005850935515250482594242698943781290372864,
    16: 688225501867803673752538183177656686154133465135272635952,
    17: 6356708573138865773229780075727936176527581177626353995968270388,
    18: 17904021235334710186774676451631580228187847953251478146430372421319200,
}


def v2(n: int) -> int:
    """Computes the 2-adic valuation v_2(n) (number of trailing zeros in binary)."""
    if n == 0:
        return float("inf")
    count = 0
    while (n & 1) == 0:
        count += 1
        n >>= 1
    return count


def run_h16_analysis():
    print("=" * 80)
    print("  [H-16 Test] 2-adic Valuation v_2(a(n)) and Modulo 2^k Invariants")
    print("=" * 80)
    print(" n  | v_2(a(n)) | mod 2 | mod 4 | mod 8 | mod 16 | mod 32 | mod 64 | mod 128 | mod 256")
    print("----|-----------|-------|-------|-------|--------|--------|--------|---------|--------")

    for n in sorted(EXACT_RECORDS.keys()):
        val = EXACT_RECORDS[n]
        val_v2 = v2(val)
        m2 = val % 2
        m4 = val % 4
        m8 = val % 8
        m16 = val % 16
        m32 = val % 32
        m64 = val % 64
        m128 = val % 128
        m256 = val % 256
        print(
            f" {n:2d} |    {val_v2:2d}     |   {m2:1d}   |   {m4:1d}   |   {m8:1d}   |   {m16:2d}   |   {m32:2d}   |   {m64:2d}   |   {m128:3d}   |  {m256:3d}"
        )


if __name__ == "__main__":
    run_h16_analysis()
