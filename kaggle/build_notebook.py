"""Generate the self-contained Kaggle notebook from the source files here.

Run:  python kaggle/build_notebook.py
Keeps a007764_t4x2.ipynb in sync with the .py/.h/.cu sources so the notebook
never drifts from the code that was actually verified.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["a007764_core.py", "a007764_kernel.h", "a007764_cuda.cu", "a007764_gpu.py"]


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": text.strip("\n").splitlines(keepends=True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


def build() -> dict:
    payload = {name: open(os.path.join(HERE, name)).read() for name in FILES}
    write_cell = ["import os, json, textwrap",
                  "os.makedirs('/kaggle/working/src', exist_ok=True)",
                  "SOURCES = json.loads(r'''" + json.dumps(payload) + "''')",
                  "for name, body in SOURCES.items():",
                  "    open('/kaggle/working/src/' + name, 'w').write(body)",
                  "import sys; sys.path.insert(0, '/kaggle/working/src')",
                  "print('wrote', list(SOURCES))"]

    cells = [
        md("""
# OEIS A007764 — frontier DP on 2×T4

**What this notebook actually does.** It computes `a(n)` exactly, for the largest
`n` that fits a single T4, using the rank-indexed dense frontier DP that is the
one genuinely verified memory result in this repository.

**What it does not do.** It does not compute `a(28)`. That needs ≈1.4 TiB of
device memory even after every valid reduction below; two T4s have 32 GB.
The n=28 figure printed at the end is a measured extrapolation, not a run.

### The results this notebook relies on (each re-derived from scratch)

| Result | Statement | How it is checked here |
|---|---|---|
| Boundary state count | `B(n) = Σ_a M_a·M_{n−a} = M_{n+2} − M_{n+1}` | convolution identity asserted for n≤19 |
| Mid-row peak | `peak(n) = 2·B(n)` | measured occupancy is exactly 1.0000 |
| Bijective ranking | `index = 2·rank(u) + b` onto `[0, 2B(n))` | exhaustive round-trip, n≤8 |
| Dense array | no keys, no hash table, 8→4 B/state | array length == peak live states |

Everything else that phase 1 and phase 2 recorded as a "breakthrough" is either
already contained in the above, or did not survive audit — see
`AUDIT_PHASE1_PHASE2.md`.
"""),
        md("## 1. Environment"),
        code("""
import subprocess
print(subprocess.run(['nvidia-smi',
                      '--query-gpu=index,name,memory.total',
                      '--format=csv'], capture_output=True, text=True).stdout)
import cupy as cp
ndev = cp.cuda.runtime.getDeviceCount()
print('CuPy', cp.__version__, '| visible GPUs:', ndev)
for d in range(ndev):
    free, total = cp.cuda.Device(d).mem_info
    print(f'  gpu{d}: {free/2**30:.2f} GiB free / {total/2**30:.2f} GiB total')
"""),
        md("## 2. Write the sources\n\nThe device code is written once and shared "
           "verbatim by the CPU reference and the CUDA kernel."),
        code("\n".join(write_cell)),
        md("## 3. Verify the mathematics on CPU\n\nPure Python, no GPU. This proves the "
           "state-space theorem and the ranking bijection before any kernel runs."),
        code("""
from a007764_core import (KNOWN_A007764, motzkin_numbers, ProfileRanker,
                          a_n_wordspace, a_n_dense, EMPTY, OPEN, CLOSE, MARK)
import itertools

M = motzkin_numbers(24)
for n in range(20):
    assert sum(M[a]*M[n-a] for a in range(n+1)) == M[n+2]-M[n+1]
print('B(n) = sum_a M_a M_(n-a) = M_(n+2) - M_(n+1)   verified n=0..19')

for n in range(0, 9):                       # exhaustive ranking round-trip
    P, seen = ProfileRanker(n), set()
    words = []
    for w in itertools.product([EMPTY, OPEN, CLOSE, MARK], repeat=n+1):
        if w.count(MARK) != 1:
            continue
        a = w.index(MARK)
        good = True
        for part in (w[:a], w[a+1:]):
            d = 0
            for c in part:
                d += (c == OPEN) - (c == CLOSE)
                if d < 0:
                    good = False
            if d != 0:
                good = False
        if good:
            words.append(list(w))
    assert len(words) == P.size == M[n+2]-M[n+1]
    for w in words:
        r = P.rank(w)
        assert 0 <= r < P.size and r not in seen and P.unrank(r) == w
        seen.add(r)
print('profile rank/unrank bijective onto [0,B(n))   verified exhaustively n=0..8')

for n in range(1, 10):
    assert a_n_wordspace(n) == KNOWN_A007764[n]
print('word-space frontier DP  == OEIS a(n)          verified n=1..9')
for n in range(1, 10):
    assert a_n_dense(n, report=True) == KNOWN_A007764[n]
print('dense rank-indexed DP   == OEIS a(n)          verified n=1..9, occupancy 1.0000')
"""),
        md("## 4. Memory ledger\n\nWhat actually fits, on this hardware and on a "
           "hypothetical 8×B300 node."),
        code("""
from a007764_gpu import state_counts, bytes_needed, estimate_bits, primes_for
free0 = cp.cuda.Device(0).mem_info[0]
print(f'{"n":>3} {"B(n)":>18} {"peak = 2B(n)":>19} {"ping-pong uint32":>18}  fits one T4?')
best = None
for n in range(16, 30):
    B, pk = state_counts(n)
    need = bytes_needed(n)
    fits = need < free0 * 0.92
    if fits:
        best = n
    print(f'{n:>3} {B:>18,} {pk:>19,} {need/2**30:>15.2f} GiB  {"yes" if fits else "no"}')
print()
print(f'largest n that fits one T4 with this scheme: n = {best}')
"""),
        md("## 5. GPU kernel against ground truth\n\nThe CUDA kernel must reproduce all "
           "twelve known terms modulo a prime before anything larger is attempted."),
        code("""
from a007764_gpu import GpuSweep, CRT_PRIMES_31BIT
p = CRT_PRIMES_31BIT[1]
for n in range(1, 13):
    got = GpuSweep(n, device=0).run(p)
    exp = KNOWN_A007764[n] % p
    assert got == exp, (n, got, exp)
    print(f'  n={n:2d}: gpu = {got:>11d}  == a(n) mod p   OK')
print('CUDA kernel matches OEIS for every known term n=1..12')
"""),
        md("## 6. Throughput ladder\n\nMeasure the real rate. Everything after this "
           "point is projected from these numbers, not assumed."),
        code("""
import time
from a007764_gpu import state_counts
rates = {}
for n in [14, 16, 18]:
    B, pk = state_counts(n)
    t0 = time.time()
    GpuSweep(n, device=0).run(p)
    el = time.time() - t0
    cells = (n+1)**2
    rate = cells * pk / el
    rates[n] = rate
    print(f'  n={n:2d}: {el:7.2f}s for one prime   '
          f'{cells*pk:>16,} state-updates   {rate/1e9:6.3f} G updates/s')
rate = sum(rates.values()) / len(rates)
print(f'\\nmean measured rate: {rate/1e9:.3f} G state-updates/s on one T4')
"""),
        md("## 7. Main run\n\n`TARGET_N` defaults to 20, which finishes comfortably. "
           "Set it to 21 to use the full T4 (10.9 GiB, the ceiling for this scheme); "
           "budget several hours."),
        code("""
TARGET_N = 20        # 21 also fits one T4; 22 needs 30.7 GiB and does not

B, pk = state_counts(TARGET_N)
primes = primes_for(TARGET_N)
est = (TARGET_N+1)**2 * pk / rate * len(primes) / max(1, ndev)
print(f'n={TARGET_N}: {pk:,} states, {bytes_needed(TARGET_N)/2**30:.2f} GiB, '
      f'{len(primes)} primes')
print(f'projected wall clock on {ndev} GPU(s): {est/3600:.2f} h')
"""),
        code("""
from a007764_gpu import solve, crt
cp.get_default_memory_pool().free_all_blocks()
value, residues, elapsed = solve(TARGET_N, primes=primes,
                                 devices=list(range(ndev)))
print(f'\\na({TARGET_N}) = {value}')
print(f'{value.bit_length()} bits, {len(str(value))} digits, {elapsed/60:.1f} min')
"""),
        md("## 8. Independent confirmation\n\nAdd one prime beyond the estimated need "
           "and reconstruct again. An unchanged value proves the result is exact "
           "provided `a(n)` is below the enlarged modulus, which the 30-bit margin "
           "makes safe."),
        code("""
cp.get_default_memory_pool().free_all_blocks()
extra = CRT_PRIMES_31BIT[len(primes)]
r_extra = GpuSweep(TARGET_N, device=0).run(extra)
value2, _ = crt([residues[q] for q in primes] + [r_extra], list(primes) + [extra])
print('with one extra prime:', 'UNCHANGED -> value is exact'
      if value2 == value else f'CHANGED -> need more primes ({value2})')
if TARGET_N in KNOWN_A007764:
    print('vs embedded OEIS value:',
          'MATCH' if value == KNOWN_A007764[TARGET_N] else 'MISMATCH')
"""),
        md("## 9. What n=28 would take\n\nMeasured rate, extrapolated. No claim beyond "
           "arithmetic on the numbers above."),
        code("""
B28, pk28 = state_counts(28)
cells28 = 29**2
updates28 = cells28 * pk28
prime_hours = updates28 / rate / 3600
nprimes28 = len(primes_for(28))
print(f'n=28 peak states      : {pk28:,}')
print(f'  uint32 ping-pong    : {bytes_needed(28)/2**40:.2f} TiB')
print(f'  11-bit single buffer: {pk28*11/8/2**40:.2f} TiB')
print(f'  11-bit + T-Sigma/2  : {pk28*11/8/2/2**40:.2f} TiB   '
      f'(vs 1.97 TiB on an 8xB300 node)')
print(f'state-updates         : {updates28:,}')
print(f'at the rate measured  : {prime_hours:,.0f} GPU-hours per prime, '
      f'{nprimes28} primes -> {prime_hours*nprimes28:,.0f} GPU-hours total')
print()
print('So the memory budget closes only without ping-pong, and the compute')
print('budget is the part nobody in this repository has ever measured before.')
"""),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
            "accelerator": "GPU",
        },
        "nbformat": 4, "nbformat_minor": 5,
    }


if __name__ == "__main__":
    out = os.path.join(HERE, "a007764_t4x2.ipynb")
    with open(out, "w") as f:
        json.dump(build(), f, indent=1)
    print("wrote", out)
