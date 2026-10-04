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

from a007764_core import (KNOWN_A007764, MARK, EMPTY, motzkin_numbers,
                          completion_table, automaton_table, automaton_rank)

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


SOURCES = ("a007764_kernel.h", "a007764_cuda.cu", "a007764_v2.h", "a007764_cuda_v2.cu",
           "a007764_v3.h", "a007764_cuda_v3.cu", "a007764_cuda_probe.cu",
           "a007764_v4.h", "a007764_cuda_v4.cu")


def cuda_source() -> str:
    """v1 and v2 device code + kernels, concatenated exactly as compiled."""
    return "\n".join(_read(f) for f in SOURCES)


_MODULES: Dict[int, object] = {}


def _module(device: int):
    """Compile once per device and reuse."""
    import cupy as cp
    if device not in _MODULES:
        with cp.cuda.Device(device):
            _MODULES[device] = cp.RawModule(code=cuda_source(), backend="nvrtc",
                                            options=("-std=c++11",))
    return _MODULES[device]


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
            mod = _module(device)
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
# v2: incremental ranking (research/r05, r06).  Same index spaces as v1.
# --------------------------------------------------------------------------
class GpuSweepV2:
    def __init__(self, n: int, device: int = 0, block: int = 128,
                 chunk: int = 64) -> None:
        import cupy as cp

        self.cp, self.n, self.device = cp, n, device
        self.block, self.chunk = block, chunk
        L = n + 1
        with cp.cuda.Device(device):
            mod = _module(device)
            self.k_step = mod.get_function("v2_step")
            self.k_rowend = mod.get_function("row_end")
            Ca = automaton_table(n)
            self.B = Ca[(L * (L + 2) + 0) * 2 + 0]
            self.size = 2 * self.B
            self.seed = automaton_rank([MARK] + [EMPTY] * n, Ca, n)
            self.dCa = cp.asarray(np.array(Ca, dtype=np.uint64))
            self.shmem = len(Ca) * 8
            sms = cp.cuda.Device(device).attributes["MultiProcessorCount"]
            nchunks = (self.B + chunk - 1) // chunk
            self.grid = max(1, min((nchunks + block - 1) // block, sms * 16))
            self.rgrid = max(1, min((self.B + 255) // 256, sms * 32))
            self.cur = cp.zeros(self.size, dtype=cp.uint32)
            self.nxt = cp.zeros(self.size, dtype=cp.uint32)
            self.acc = cp.zeros(1, dtype=cp.uint64)

    def run(self, p: int, progress=None) -> int:
        cp, n = self.cp, self.n
        with cp.cuda.Device(self.device):
            self.cur.fill(0)
            self.cur[2 * self.seed] = 1                # (0,0) emits MARK down
            self.cur[2 * self.seed + 1] = 1            # ... or right
            for i in range(n + 1):
                for j in range(1 if i == 0 else 0, n + 1):
                    fb = 1 if j == 0 else 0
                    term = 1 if (i == n and j == n) else 0
                    if term:
                        self.acc.fill(0)
                    else:
                        self.nxt.fill(0)
                    self.k_step((self.grid,), (self.block,),
                                (self.cur, self.nxt, np.uint64(self.B),
                                 np.uint64(self.chunk), np.int32(i), np.int32(j),
                                 np.int32(n), np.uint32(p), np.int32(fb),
                                 np.int32(term), self.dCa, self.acc),
                                shared_mem=self.shmem)
                    if term:
                        return int(self.acc.get()[0] % p)
                    self.cur, self.nxt = self.nxt, self.cur
                self.nxt.fill(0)
                self.k_rowend((self.rgrid,), (256,),
                              (self.cur, self.nxt, np.uint64(self.B)))
                self.cur, self.nxt = self.nxt, self.cur
                if progress:
                    progress(i + 1, n + 1)
        raise RuntimeError("sweep finished without reaching the terminal vertex")


# --------------------------------------------------------------------------
# v3: v1's one-index-per-thread layout + v2's O(1) local output rank
# --------------------------------------------------------------------------
class GpuSweepV3:
    def __init__(self, n: int, device: int = 0, block: int = 256) -> None:
        import cupy as cp

        self.cp, self.n, self.device, self.block = cp, n, device, block
        L = n + 1
        with cp.cuda.Device(device):
            mod = _module(device)
            self.k_step = mod.get_function("v3_step")
            self.k_rowend = mod.get_function("row_end")
            Ca = automaton_table(n)
            self.B = Ca[(L * (L + 2) + 0) * 2 + 0]
            self.size = 2 * self.B
            self.seed = automaton_rank([MARK] + [EMPTY] * n, Ca, n)
            self.dCa = cp.asarray(np.array(Ca, dtype=np.uint64))
            self.shmem = len(Ca) * 8
            sms = cp.cuda.Device(device).attributes["MultiProcessorCount"]
            self.grid = max(1, min((self.size + block - 1) // block, sms * 32))
            self.cur = cp.zeros(self.size, dtype=cp.uint32)
            self.nxt = cp.zeros(self.size, dtype=cp.uint32)
            self.acc = cp.zeros(1, dtype=cp.uint64)

    def run(self, p: int, progress=None) -> int:
        cp, n = self.cp, self.n
        with cp.cuda.Device(self.device):
            self.cur.fill(0)
            self.cur[2 * self.seed] = 1
            self.cur[2 * self.seed + 1] = 1
            for i in range(n + 1):
                for j in range(1 if i == 0 else 0, n + 1):
                    fb = 1 if j == 0 else 0
                    term = 1 if (i == n and j == n) else 0
                    size_in = self.B if fb else self.size
                    if term:
                        self.acc.fill(0)
                    else:
                        self.nxt.fill(0)
                    self.k_step((self.grid,), (self.block,),
                                (self.cur, self.nxt, np.uint64(size_in), np.int32(i),
                                 np.int32(j), np.int32(n), np.uint32(p), np.int32(fb),
                                 np.int32(term), self.dCa, self.acc),
                                shared_mem=self.shmem)
                    if term:
                        return int(self.acc.get()[0] % p)
                    self.cur, self.nxt = self.nxt, self.cur
                self.nxt.fill(0)
                self.k_rowend((self.grid,), (self.block,),
                              (self.cur, self.nxt, np.uint64(self.B)))
                self.cur, self.nxt = self.nxt, self.cur
                if progress:
                    progress(i + 1, n + 1)
        raise RuntimeError("sweep finished without reaching the terminal vertex")


# --------------------------------------------------------------------------
# v4: v1's layout and MARK-split ranking, 32-bit arithmetic, no division,
#     O(1) output rank for transitions that keep the MARK and touch no partner
# --------------------------------------------------------------------------
V4_MAX_N = 22          # every rank, table entry and index stays below 2^32


def build_tables_v4(n: int):
    if n > V4_MAX_N:
        raise ValueError(f"v4 supports n <= {V4_MAX_N}")
    Ts = n + 3
    T = completion_table(n + 4)
    T32 = np.zeros((n + 1) * Ts, dtype=np.uint32)
    for rem in range(n + 1):
        for d in range(Ts):
            assert T[rem][d] < 2**32
            T32[rem * Ts + d] = T[rem][d]
    M = motzkin_numbers(n + 1)
    M32 = np.array(M[:n + 1], dtype=np.uint32)
    off = np.zeros(n + 2, dtype=np.uint32)
    acc = 0
    for a in range(n + 1):
        off[a] = acc
        acc += M[a] * M[n - a]
    off[n + 1] = acc
    minv = np.array([(1 << 32) // M[b] for b in range(n + 1)], dtype=np.uint64)
    return T32, M32, off, minv, acc


class GpuSweepV4:
    def __init__(self, n: int, device: int = 0, block: int = 256) -> None:
        import cupy as cp

        self.cp, self.n, self.device, self.block = cp, n, device, block
        T32, M32, off, minv, B = build_tables_v4(n)
        with cp.cuda.Device(device):
            mod = _module(device)
            self.k_step = mod.get_function("v4_step")
            self.k_rowend = mod.get_function("row_end")
            self.B, self.size = B, 2 * B
            self.dT, self.dM = cp.asarray(T32), cp.asarray(M32)
            self.dO, self.dI = cp.asarray(off), cp.asarray(minv)
            self.shmem = (n + 1) * 8 + ((n + 1) * (n + 3) + (n + 1) + (n + 2)) * 4
            sms = cp.cuda.Device(device).attributes["MultiProcessorCount"]
            self.sms = sms
            self.grid = max(1, min((self.size + block - 1) // block, sms * 32))
            self.cur = cp.zeros(self.size, dtype=cp.uint32)
            self.nxt = cp.zeros(self.size, dtype=cp.uint32)
            self.acc = cp.zeros(1, dtype=cp.uint64)

    def _launch(self, size_in, i, j, p, fb, term, dry):
        self.k_step((self.grid,), (self.block,),
                    (self.cur, self.nxt, np.uint64(size_in), np.int32(i), np.int32(j),
                     np.int32(self.n), np.uint32(p), np.int32(fb), np.int32(term),
                     np.int32(dry), self.dT, self.dM, self.dO, self.dI, self.acc),
                    shared_mem=self.shmem)

    def run(self, p: int, progress=None) -> int:
        cp, n = self.cp, self.n
        with cp.cuda.Device(self.device):
            self.cur.fill(0)
            self.cur[0] = 1                    # profile M0..0 has split rank 0:
            self.cur[1] = 1                    # MARK emitted down (b=0) / right (b=1)
            for i in range(n + 1):
                for j in range(1 if i == 0 else 0, n + 1):
                    fb = 1 if j == 0 else 0
                    term = 1 if (i == n and j == n) else 0
                    size_in = self.B if fb else self.size
                    if term:
                        self.acc.fill(0)
                    else:
                        self.nxt.fill(0)
                    self._launch(size_in, i, j, p, fb, term, 0)
                    if term:
                        return int(self.acc.get()[0] % p)
                    self.cur, self.nxt = self.nxt, self.cur
                self.nxt.fill(0)
                self.k_rowend((self.grid,), (self.block,),
                              (self.cur, self.nxt, np.uint64(self.B)))
                self.cur, self.nxt = self.nxt, self.cur
                if progress:
                    progress(i + 1, n + 1)
        raise RuntimeError("sweep finished without reaching the terminal vertex")

    def probe(self, mode: int = 1) -> float:
        """Probe launches (no memory writes).  mode: 1 real path, 2 all-fast,
        3 all-full-rank, 4 unrank only -- see a007764_v4.h."""
        cp, n = self.cp, self.n
        with cp.cuda.Device(self.device):
            cp.cuda.Device(self.device).synchronize()
            t0 = time.perf_counter()
            for i in range(n + 1):
                for j in range(1 if i == 0 else 0, n + 1):
                    if i == n and j == n:
                        continue
                    fb = 1 if j == 0 else 0
                    self._launch(self.B if fb else self.size, i, j, 2147483629, fb, 0, mode)
            cp.cuda.Device(self.device).synchronize()
            return time.perf_counter() - t0


def make_sweep(engine: str, n: int, device: int = 0, **kw):
    if engine == "v1":
        return GpuSweep(n, device=device)
    if engine == "v2":
        return GpuSweepV2(n, device=device, **kw)
    if engine == "v3":
        return GpuSweepV3(n, device=device)
    if engine == "v4":
        return GpuSweepV4(n, device=device)
    raise ValueError(engine)


def probe_compute(engine: str, n: int, device: int = 0, block: int = 256) -> float:
    """Seconds for one sweep's worth of per-index work with no scatter."""
    import cupy as cp

    if engine == "v4":
        return GpuSweepV4(n, device=device, block=block).probe()
    with cp.cuda.Device(device):
        mod = _module(device)
        sms = cp.cuda.Device(device).attributes["MultiProcessorCount"]
        sink = cp.zeros(1, dtype=cp.uint64)
        if engine == "v1":
            k = mod.get_function("probe_v1")
            Tf, Mf, off, B, Tstride = build_tables(n)
            dT, dM, dO = cp.asarray(Tf), cp.asarray(Mf), cp.asarray(off)
            shmem = ((n + 5) * Tstride + (n + 5) + (n + 2)) * 8
        elif engine == "v3":
            k = mod.get_function("probe_v3")
            Ca = automaton_table(n)
            L = n + 1
            B = Ca[(L * (L + 2) + 0) * 2 + 0]
            dCa = cp.asarray(np.array(Ca, dtype=np.uint64))
            shmem = len(Ca) * 8
        else:
            raise ValueError(engine)
        cp.cuda.Device(device).synchronize()
        t0 = time.perf_counter()
        for i in range(n + 1):
            for j in range(1 if i == 0 else 0, n + 1):
                if i == n and j == n:
                    continue
                fb = 1 if j == 0 else 0
                size_in = B if fb else 2 * B
                grid = max(1, min((size_in + block - 1) // block, sms * 32))
                if engine == "v1":
                    args = (np.uint64(size_in), np.int32(i), np.int32(j), np.int32(n),
                            np.int32(fb), dT, dM, dO, np.int32(Tstride), sink)
                else:
                    args = (np.uint64(size_in), np.int32(i), np.int32(j), np.int32(n),
                            np.int32(fb), dCa, sink)
                k((grid,), (block,), args, shared_mem=shmem)
        cp.cuda.Device(device).synchronize()
        return time.perf_counter() - t0


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
          devices: Sequence[int] | None = None, verbose: bool = True,
          engine: str = "v2", on_residue=None, **engine_kw
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

    errors: List[BaseException] = []

    def worker(dev: int, my_primes: List[int]) -> None:
        try:
            sweep = make_sweep(engine, n, device=dev, **engine_kw)
            for p in my_primes:
                t1 = time.time()
                r = sweep.run(p)
                with lock:
                    residues[p] = r
                    if on_residue:
                        on_residue(p, r, time.time() - t1, dev)
                if verbose:
                    print(f"  [gpu{dev}] p={p}  a({n}) mod p = {r:>10d} "
                          f"({time.time() - t1:.1f}s)", flush=True)
        except BaseException as e:          # surface worker failures
            errors.append(e)

    buckets: List[List[int]] = [[] for _ in devices]
    for k, p in enumerate(primes):
        buckets[k % len(devices)].append(p)
    threads = [threading.Thread(target=worker, args=(d, b))
               for d, b in zip(devices, buckets) if b]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]

    ordered = [residues[p] for p in primes]
    value, _ = crt(ordered, list(primes))
    return value, residues, time.time() - t0
