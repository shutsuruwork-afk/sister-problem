"""Dual-T4 GPU driver for the A007764 frontier DP.

Storage is the rank-indexed dense array of NOTES.md sec.2: length exactly
2*B(n) = 2*(M_{n+2} - M_{n+1}), 100% occupied, no keys and no hash table.
One CRT prime is one independent full sweep, so primes are handed out to the
available GPUs round-robin.

The device code is a007764_kernel.h (validated on CPU against the twelve known
OEIS terms) followed by a007764_cuda.cu.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np

from a007764_core import KNOWN_A007764, motzkin_numbers, completion_table

# Primes below 2^31 so that (a + b) stays inside uint32 in the modular atomic.
CRT_PRIMES_31BIT: List[int] = [
    2147483647, 2147483629, 2147483587, 2147483579, 2147483563, 2147483549,
    2147483543, 2147483497, 2147483489, 2147483477, 2147483423, 2147483399,
    2147483353, 2147483323, 2147483269, 2147483249, 2147483237, 2147483179,
    2147483171, 2147483137, 2147483123, 2147483077, 2147483069, 2147483059,
    2147483053, 2147483033, 2147483029, 2147482951, 2147482949, 2147482943,
    2147482937, 2147482921, 2147482877, 2147482873, 2147482867, 2147482859,
    2147482819, 2147482817, 2147482811, 2147482801, 2147482763, 2147482739,
    2147482697, 2147482693, 2147482681, 2147482663, 2147482661, 2147482649,
]


def _read(path: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, path)) as f:
        return f.read()


def cuda_source() -> str:
    """Device header + kernels, concatenated exactly as compiled."""
    return _read("a007764_kernel.h") + "\n" + _read("a007764_cuda.cu")


# --------------------------------------------------------------------------
# host-side tables
# --------------------------------------------------------------------------
def build_tables(n: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    kmax, Tstride, Trows = n + 4, n + 6, n + 5
    T = completion_table(kmax)
    M = motzkin_numbers(kmax)
    Tflat = np.zeros(Trows * Tstride, dtype=np.uint64)
    for rem in range(kmax + 1):
        for d in range(kmax + 2):
            Tflat[rem * Tstride + d] = T[rem][d]
    Marr = np.zeros(n + 5, dtype=np.uint64)
    for k in range(kmax + 1):
        Marr[k] = M[k]
    off = np.zeros(n + 2, dtype=np.uint64)
    acc = 0
    for a in range(n + 1):
        off[a] = acc
        acc += M[a] * M[n - a]
    off[n + 1] = acc
    return Tflat, Marr, off, int(acc), Tstride          # acc == B(n)


def state_counts(n: int) -> Tuple[int, int]:
    """(B(n), 2*B(n)) -- row-boundary and mid-row peak state counts."""
    M = motzkin_numbers(n + 3)
    B = M[n + 2] - M[n + 1]
    return B, 2 * B


def bytes_needed(n: int) -> int:
    """Device bytes for the ping-pong pair of uint32 residue arrays."""
    return 2 * state_counts(n)[1] * 4


# --------------------------------------------------------------------------
# single-prime sweep on one GPU
# --------------------------------------------------------------------------
class GpuSweep:
    def __init__(self, n: int, device: int = 0, block: int = 256,
                 grid: int = 4096) -> None:
        import cupy as cp

        self.cp, self.n, self.device = cp, n, device
        self.block, self.grid = block, grid
        with cp.cuda.Device(device):
            mod = cp.RawModule(code=cuda_source(), backend="nvrtc",
                               options=("-std=c++11", "--use_fast_math"))
            self.k_step = mod.get_function("dp_step")
            self.k_rowend = mod.get_function("row_end")
            self.k_term = mod.get_function("terminal_sum")

            Tf, Mf, off, B, Tstride = build_tables(n)
            self.B, self.Tstride = B, Tstride
            self.size = 2 * B
            self.dT = cp.asarray(Tf)
            self.dM = cp.asarray(Mf)
            self.dOff = cp.asarray(off)
            self.shmem = (( n + 5) * Tstride + (n + 5) + (n + 2)) * 8
            self.cur = cp.zeros(self.size, dtype=cp.uint32)
            self.nxt = cp.zeros(self.size, dtype=cp.uint32)
            self.acc = cp.zeros(1, dtype=cp.uint64)

    def run(self, p: int, progress=None) -> int:
        cp, n = self.cp, self.n
        with cp.cuda.Device(self.device):
            self.cur.fill(0)
            # seed: vertex (0,0) emits the MARK down (idx 0) or right (idx 1)
            self.cur[0:2] = 1
            size_in = self.size
            for i in range(n + 1):
                for j in range(1 if i == 0 else 0, n + 1):
                    from_boundary = 1 if j == 0 else 0
                    if i == n and j == n:
                        self.acc.fill(0)
                        self.k_term((self.grid,), (self.block,),
                                    (self.cur, self.acc, np.uint64(size_in),
                                     np.int32(n), np.int32(from_boundary),
                                     self.dT, self.dM, self.dOff,
                                     np.int32(self.Tstride)),
                                    shared_mem=self.shmem)
                        return int(self.acc.get()[0] % p)
                    self.nxt.fill(0)
                    self.k_step((self.grid,), (self.block,),
                                (self.cur, self.nxt, np.uint64(size_in),
                                 np.int32(i), np.int32(j), np.int32(n),
                                 np.uint32(p), np.int32(from_boundary),
                                 self.dT, self.dM, self.dOff,
                                 np.int32(self.Tstride)),
                                shared_mem=self.shmem)
                    self.cur, self.nxt = self.nxt, self.cur
                    size_in = self.size
                # row end -> boundary indexing, size B
                self.nxt.fill(0)
                self.k_rowend((self.grid,), (self.block,),
                              (self.cur, self.nxt, np.uint64(self.B)))
                self.cur, self.nxt = self.nxt, self.cur
                size_in = self.B
                if progress:
                    progress(i + 1, n + 1)
        raise RuntimeError("sweep finished without reaching the terminal vertex")


# --------------------------------------------------------------------------
# CRT
# --------------------------------------------------------------------------
def crt(residues: Sequence[int], primes: Sequence[int]) -> Tuple[int, int]:
    total, N = 0, 1
    for p in primes:
        N *= p
    for r, p in zip(residues, primes):
        m = N // p
        total = (total + r * m * pow(m, -1, p)) % N
    return total, N


def estimate_bits(n: int) -> int:
    """log2 a(n) from the measured growth fit (629 bits at n=28)."""
    return int(0.7479 * (n + 1) ** 2) + 8


def primes_for(n: int, margin: float = 1.30) -> List[int]:
    need = int(estimate_bits(n) * margin)
    out, bits = [], 0
    for p in CRT_PRIMES_31BIT:
        out.append(p)
        bits += 30                      # each prime contributes > 2^30
        if bits >= need:
            break
    return out


# --------------------------------------------------------------------------
# multi-GPU driver
# --------------------------------------------------------------------------
def solve(n: int, primes: Sequence[int] | None = None,
          devices: Sequence[int] | None = None, verbose: bool = True
          ) -> Tuple[int, Dict[int, int], float]:
    """Exact a(n) via one full sweep per CRT prime, spread over the GPUs."""
    import cupy as cp

    if devices is None:
        devices = list(range(cp.cuda.runtime.getDeviceCount()))
    if primes is None:
        primes = primes_for(n)
    residues: Dict[int, int] = {}
    lock = threading.Lock()
    t0 = time.time()

    def worker(dev: int, my_primes: List[int]) -> None:
        sweep = GpuSweep(n, device=dev)
        for p in my_primes:
            t1 = time.time()
            r = sweep.run(p)
            with lock:
                residues[p] = r
            if verbose:
                print(f"  [gpu{dev}] p={p}  a({n}) mod p = {r:>10d} "
                      f"({time.time() - t1:.1f}s)", flush=True)

    buckets: List[List[int]] = [[] for _ in devices]
    for k, p in enumerate(primes):
        buckets[k % len(devices)].append(p)
    threads = [threading.Thread(target=worker, args=(d, b))
               for d, b in zip(devices, buckets) if b]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ordered = [residues[p] for p in primes]
    value, _ = crt(ordered, list(primes))
    return value, residues, time.time() - t0
