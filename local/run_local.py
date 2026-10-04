"""Local runner for the A007764 engine (GPU via CuPy, CPU/OpenMP fallback).

    python local/run_local.py                  # verify + cross-check + benchmark + projection
    python local/run_local.py --target 20      # ... then compute a(20) exactly
    python local/run_local.py --auto --hours 3 # ... then the largest n that fits 3 h
    python local/run_local.py --resume results/run_XXXX.json   # continue a target run
    python local/run_local.py --cpu            # force the CPU path

Index convention: n counts EDGES per side ((n+1) x (n+1) points).  OEIS
A007764 counts points, so OEIS a(n+1) is this script's a(n).  Every result is
checked against data/b007764.txt (published terms through OEIS a(27), i.e.
n <= 26); no network access is needed.  The unsolved frontier is n = 27.

Every step is written to results/run_<UTC>.json as soon as it finishes, so an
interrupted run still leaves its measurements behind.  No host names or user
names are recorded.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "kaggle")
sys.path.insert(0, ENGINE)

from a007764_core import KNOWN_A007764, motzkin_numbers, oeis_known, oeis_index  # noqa: E402

P_CHECK = 2147483629
CROSS_N = (13, 14, 15, 16)


# --------------------------------------------------------------------------
def state_counts(n):
    M = motzkin_numbers(n + 3)
    B = M[n + 2] - M[n + 1]
    return B, 2 * B


def work(n):
    """state slots scanned by one prime: (n+1)^2 cells x 2B(n)."""
    return (n + 1) ** 2 * state_counts(n)[1]


def bytes_needed(n):
    return 2 * state_counts(n)[1] * 4


class Log:
    def __init__(self, path, resume=None):
        self.path = path
        self.data = resume or {}
        self.data.setdefault("started_utc", datetime.now(timezone.utc).isoformat())
        self.flush()

    def put(self, key, value):
        self.data[key] = value
        self.flush()

    def flush(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=1, default=str)
        os.replace(tmp, self.path)


def say(msg=""):
    print(msg, flush=True)


LOG = None          # set in main() so the top-level handler can record failures


# --------------------------------------------------------------------------
# environment
# --------------------------------------------------------------------------
def probe_env(force_cpu):
    env = {"python": sys.version.split()[0], "platform": platform.platform(),
           "cpu": platform.processor() or platform.machine(),
           "cpu_count": os.cpu_count(), "backend": None, "gpus": []}
    if not force_cpu:
        try:
            import cupy as cp
            env["cupy"] = cp.__version__
            env["cuda_runtime"] = cp.cuda.runtime.runtimeGetVersion()
            env["cuda_driver"] = cp.cuda.runtime.driverGetVersion()
            for d in range(cp.cuda.runtime.getDeviceCount()):
                props = cp.cuda.runtime.getDeviceProperties(d)
                free, total = cp.cuda.Device(d).mem_info
                env["gpus"].append({
                    "index": d,
                    "name": props["name"].decode() if isinstance(props["name"], bytes) else props["name"],
                    "cc": f'{props["major"]}.{props["minor"]}',
                    "sms": props["multiProcessorCount"],
                    "mem_total_gib": round(total / 2**30, 2),
                    "mem_free_gib": round(free / 2**30, 2)})
            if env["gpus"]:
                env["backend"] = "gpu"
        except Exception as e:
            env["cupy_error"] = f"{type(e).__name__}: {e}"
    if env["backend"] is None:
        env["backend"] = "cpu" if (shutil.which("gcc") or shutil.which("cc")) else None
    return env


# --------------------------------------------------------------------------
# backends: run(engine, n, p, device) -> residue
# --------------------------------------------------------------------------
class GpuBackend:
    def __init__(self, env, chunk=64):
        import cupy as cp
        import a007764_gpu as g
        self.cp, self.g, self.chunk = cp, g, chunk
        self.ndev = len(env["gpus"])

    def sweep(self, engine, n, device=0, k=1):
        self.cp.get_default_memory_pool().free_all_blocks()
        kw = {"chunk": self.chunk} if engine == "v2" else ({"k": k} if engine == "v6" else {})
        return self.g.make_sweep(engine, n, device=device, **kw)

    def run_many(self, n, primes):
        return self.sweep("v6", n, k=len(primes)).run_many(primes)

    def run(self, engine, n, p, device=0):
        return self.sweep(engine, n, device).run(p)

    def free_bytes(self):
        self.cp.get_default_memory_pool().free_all_blocks()
        return min(self.cp.cuda.Device(d).mem_info[0] for d in range(self.ndev))

    def probe(self, engine, n):
        self.cp.get_default_memory_pool().free_all_blocks()
        return self.g.probe_compute(engine, n, device=0)


class CpuBackend:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="a007764_")
        self.bin = os.path.join(self.dir, "a007764_cpu")
        cc = shutil.which("gcc") or shutil.which("cc")
        cmd = [cc, "-O3", "-march=native", "-fopenmp", "-I", ENGINE, "-o", self.bin,
               os.path.join(ENGINE, "a007764_cpu.c")]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.ndev = 1
        self.chunk = 64

    def run(self, engine, n, p, device=0):
        if engine not in ("v2", "v3", "v4", "v5", "v6"):
            raise RuntimeError("CPU backend implements v2-v6 only")
        if engine == "v6":
            PR = [2147483647, 2147483629, 2147483587, 2147483579,
                  2147483563, 2147483549, 2147483543, 2147483497]
            k = PR.index(p) + 1                 # built-in primes only
            return self.run_many(n, PR[:k])[k - 1]
        out = subprocess.run([self.bin, str(n), str(p), str(self.chunk), engine], check=True,
                             capture_output=True, text=True).stdout.split()
        return int(out[2])

    def run_many(self, n, primes):
        PR = [2147483647, 2147483629, 2147483587, 2147483579,
              2147483563, 2147483549, 2147483543, 2147483497]
        if list(primes) != PR[:len(primes)]:
            raise RuntimeError("CPU v6 runs the first K built-in primes only")
        out = subprocess.run([self.bin, str(n), "0", "0", "v6", "0.30", str(len(primes))],
                             check=True, capture_output=True, text=True).stdout.split()
        return [int(x) for x in out[2:2 + len(primes)]]

    def free_bytes(self):
        try:
            pages = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
            return pages
        except (ValueError, OSError, AttributeError):
            return 8 * 2**30


def timed(fn, *a):
    t0 = time.perf_counter()
    r = fn(*a)
    return r, time.perf_counter() - t0


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, help="compute a(N) exactly after benchmarking")
    ap.add_argument("--auto", action="store_true", help="pick the largest N fitting memory and --hours")
    ap.add_argument("--hours", type=float, default=2.0, help="time budget for --auto (default 2)")
    ap.add_argument("--engine", choices=("auto", "v1", "v2", "v3"), default="auto",
                    help="engine for the target run (default: fastest measured)")
    ap.add_argument("--cpu", action="store_true", help="force the CPU/OpenMP backend")
    ap.add_argument("--quick", action="store_true", help="verification only")
    ap.add_argument("--oeis", action="store_true", help=argparse.SUPPRESS)   # now always on, offline
    ap.add_argument("--engines", default=None,
                    help="comma list to benchmark (default: v1,v3,v5,v6 on GPU, v3,v5,v6 on CPU)")
    ap.add_argument("--resume", help="results JSON of an interrupted target run")
    ap.add_argument("--out", default=os.path.join(ROOT, "results"), help="results directory")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    resume = None
    if args.resume:
        with open(args.resume) as f:
            resume = json.load(f)
        path = args.resume
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(args.out, f"run_{stamp}.json")
    global LOG
    log = LOG = Log(path, resume)
    say(f"results -> {path}")

    # 1. environment ------------------------------------------------------
    env = probe_env(args.cpu)
    log.put("env", env)
    say(f"\n[1] environment: backend={env['backend']}  python {env['python']}  {env['platform']}")
    for gpu in env["gpus"]:
        say(f"    gpu{gpu['index']}: {gpu['name']}  cc {gpu['cc']}  {gpu['sms']} SMs  "
            f"{gpu['mem_free_gib']:.1f}/{gpu['mem_total_gib']:.1f} GiB free")
    if "cupy_error" in env:
        say(f"    CuPy unavailable: {env['cupy_error']}")
    if env["backend"] is None:
        say("no GPU and no C compiler: nothing to run")
        return 1
    be = GpuBackend(env) if env["backend"] == "gpu" else CpuBackend()
    if args.engines:
        engines = tuple(e.strip() for e in args.engines.split(","))
    else:
        engines = ("v1", "v3", "v5", "v6") if env["backend"] == "gpu" else ("v3", "v5", "v6")
    known = oeis_known()
    log.put("published_terms_n", [n for n in sorted(known) if n >= 1])
    say(f"    published terms available for n=1..{max(known)} "
        f"(OEIS a(2)..a({oeis_index(max(known))}))")

    def expect(n):
        return known[n] % P_CHECK if n in known else None

    # 2. ground truth -----------------------------------------------------
    if "verify" not in log.data:
        say("\n[2] ground truth: every engine must reproduce a(1..12) mod p  (OEIS a(2)..a(13))")
        verify = {}
        for eng in engines:
            rows = []
            for n in range(1, 13):
                got = be.run(eng, n, P_CHECK)
                exp = known[n] % P_CHECK
                rows.append({"n": n, "got": got, "expected": exp, "ok": got == exp})
                if got != exp:
                    log.put("verify", {eng: rows, "failed": True})
                    say(f"    {eng}: MISMATCH at n={n}: {got} != {exp}  -- stopping")
                    return 1
            verify[eng] = rows
            say(f"    {eng}: n=1..12 all match")
        log.put("verify", verify)
    if args.quick:
        say(f"\ndone (quick). send {path}")
        return 0

    # 3. engines against each other beyond the known terms ---------------
    if "crosscheck" not in log.data and len(engines) >= 2:
        say("\n[3] cross-check: " + ", ".join(engines) + " are independent implementations")
        rows = []
        for n in CROSS_N:
            if bytes_needed(n) > 0.85 * be.free_bytes():
                break
            row = {"n": n}
            for eng in engines:
                row[eng], row["t_" + eng] = timed(be.run, eng, n, P_CHECK)
            vals = {row[e] for e in engines}
            exp = expect(n)
            row["agree"] = len(vals) == 1 and (exp is None or exp in vals)
            row["oeis"] = exp
            rows.append(row)
            say(f"    n={n}: " + "  ".join(f"{e}={row[e]:>10d} ({row['t_' + e]:6.2f}s)" for e in engines)
                + ("  agree" if row["agree"] else "  DISAGREE") + ("  =OEIS" if exp is not None and row["agree"] else ""))
            log.put("crosscheck", rows)
            if not row["agree"]:
                say("    disagreement -- stopping")
                return 1

    # 4. benchmark --------------------------------------------------------
    if "bench" not in log.data:
        say("\n[4] benchmark")
        bench = {"chunk_tune": [], "ladder": [], "probe": []}
        if env["backend"] == "gpu" and "v2" in engines:
            tn, best = 17, None
            for chunk in (4, 8, 16, 32):
                be.chunk = chunk
                _, t = timed(be.run, "v2", tn, P_CHECK)
                bench["chunk_tune"].append({"n": tn, "chunk": chunk, "seconds": t})
                say(f"    v2 chunk={chunk:>3d}: n={tn} in {t:6.2f}s")
                if best is None or t < best[1]:
                    best = (chunk, t)
            be.chunk = bench["chunk"] = best[0]
            say(f"    -> chunk {best[0]}")
        ladder_n = (16, 17, 18, 19) if env["backend"] == "gpu" else (13, 14, 15)
        alive = list(engines)
        for n in ladder_n:
            if bytes_needed(n) > 0.85 * be.free_bytes() or not alive:
                break
            got = {}
            for eng in list(alive):
                r, t = timed(be.run, eng, n, P_CHECK)
                got[eng] = r
                bench["ladder"].append({"engine": eng, "n": n, "seconds": t,
                                        "rate": work(n) / t, "residue": r})
                say(f"    {eng} n={n}: {t:8.2f}s/prime  {work(n) / t / 1e9:7.3f} G slots/s")
                log.put("bench", bench)
                if t > 600:
                    alive.remove(eng)
            exp = expect(n)
            if len(set(got.values())) != 1 or (exp is not None and exp not in got.values()):
                say(f"    engines DISAGREE at n={n}: {got} -- stopping")
                log.put("bench", bench)
                return 1
        ladder = [r for r in bench["ladder"]]
        pn = max((r["n"] for r in ladder if r["n"] <= 18), default=None)
        if env["backend"] == "gpu":
            if pn:
                say(f"    bottleneck probe at n={pn}: same per-index work, no memory scatter")
                for eng in [e for e in ("v1", "v3", "v4") if e in engines]:
                    full = next(r["seconds"] for r in ladder if r["engine"] == eng and r["n"] == pn)
                    tc = be.probe(eng, pn)
                    bench["probe"].append({"engine": eng, "n": pn, "compute_s": tc, "full_s": full,
                                           "compute_share": tc / full})
                    say(f"      {eng}: compute-only {tc:7.2f}s of {full:7.2f}s full "
                        f"-> {100 * tc / full:5.1f}% compute, {100 * (1 - tc / full):5.1f}% memory+atomics")
        if "v6" in engines:
            from a007764_gpu import CRT_PRIMES_31BIT as PRS
            sn = max((r["n"] for r in bench["ladder"] if r["engine"] == "v6"), default=None)
            if sn:
                sn = min(sn, 18 if env["backend"] == "gpu" else 13)   # room for k up to 8
            if sn:
                say(f"    v6 residues per sweep at n={sn} (index work shared across primes):")
                bench["v6_scaling"] = []
                t1 = None
                for k in (1, 2, 3, 4, 6, 8):
                    need = (be.g.GpuSweepV6.bytes_needed(sn, k) if env["backend"] == "gpu"
                            else 2 * k * state_counts(sn)[1] * 4)
                    if need > 0.9 * be.free_bytes():
                        break
                    primes = list(PRS[:k])
                    rs, t = timed(be.run_many, sn, primes)
                    ok = all(rs[q] == known[sn] % primes[q] for q in range(k)) if sn in known else None
                    t1 = t1 or t
                    bench["v6_scaling"].append({"n": sn, "k": k, "seconds": t, "per_prime": t / k,
                                                "speedup": t1 * k / t, "match": ok})
                    say(f"      k={k}: {t:8.2f}s total  {t / k:8.2f}s per prime  "
                        f"x{t1 * k / t:4.2f} per-prime speed  {'=OEIS' if ok else ('MISMATCH' if ok is False else '')}")
                    log.put("bench", bench)
                    if ok is False:
                        say("    v6 residue mismatch -- stopping")
                        return 1
            if env["backend"] == "gpu" and pn and "v4" in engines and pn <= 22:
                say(f"    v4 time decomposition at n={pn} (probe modes, no memory writes):")
                sw = be.g.GpuSweepV4(pn, device=0)
                dec = {}
                for mode, label in ((4, "unrank only"), (2, "all outputs fast (no divergence)"),
                                    (1, "real code path"), (3, "all outputs full rank")):
                    dec[mode] = sw.probe(mode)
                    say(f"      mode {mode}: {dec[mode]:7.2f}s  {label}")
                del sw
                bench["v4_decomposition"] = {"n": pn, "unrank_only": dec[4], "all_fast": dec[2],
                                             "real_path": dec[1], "all_full": dec[3]}
                say(f"      -> removing divergence could save at most "
                    f"{100 * (1 - dec[2] / dec[1]):.0f}% of compute; unrank is "
                    f"{100 * dec[4] / dec[1]:.0f}% of the real path")
        log.put("bench", bench)
    bench = log.data["bench"]
    if env["backend"] == "gpu" and "chunk" in bench:
        be.chunk = bench["chunk"]

    def rate_of(eng):
        rows = [r for r in bench["ladder"] if r["engine"] == eng]
        return (rows[-1]["n"], rows[-1]["rate"]) if rows else None

    rates = {e: rate_of(e) for e in engines if rate_of(e)}
    if rates:
        top_n = min(v[0] for v in rates.values())
        at = {e: next(r["rate"] for r in bench["ladder"] if r["engine"] == e and r["n"] == top_n)
              for e in rates}
        base = at.get("v1") or at[engines[0]]
        say(f"    rate relative to {'v1' if 'v1' in at else engines[0]} at n={top_n}: "
            + "  ".join(f"{e} {at[e] / base:.2f}x" for e in at))
    fastest = max(rates, key=lambda e: rates[e][1]) if rates else None

    # 5. projection -------------------------------------------------------
    sys.path.insert(0, ENGINE)
    from a007764_gpu import primes_for
    rate = rates[fastest][1] if fastest else None
    scal = {r["k"]: r["speedup"] for r in bench.get("v6_scaling", [])}

    def v6_plan(n):
        """(k, per-prime rate) for v6 at size n given free memory and measured scaling."""
        if "v6" not in rates or n > 22:
            return None
        fits = [k for k in sorted(scal)
                if (be.g.GpuSweepV6.bytes_needed(n, k) if env["backend"] == "gpu"
                    else 2 * k * state_counts(n)[1] * 4) < 0.9 * be.free_bytes()]
        if not fits:
            return None
        k = max(fits)
        return k, rates["v6"][1] * scal[k]
    if not rate:
        say("\nno benchmark completed (not enough memory for n=16?); stopping")
        return 1
    free = be.free_bytes()
    proj = []
    say(f"\n[5] projection with the fastest measured engine, {fastest} "
        f"({rate / 1e9:.3f} G slots/s per device, {be.ndev} device(s))")
    for n in range(16, 29):
        np_ = len(primes_for(n))
        plan = v6_plan(n)
        r_eff = max(rate, plan[1]) if plan else rate
        hours = work(n) / r_eff * (np_ + 1) / be.ndev / 3600
        fits = bytes_needed(n) < 0.9 * free
        proj.append({"n": n, "bytes": bytes_needed(n), "fits": fits, "primes": np_ + 1, "hours": hours})
        tag = "  <- unsolved frontier" if n == 27 else ("  (published)" if n in known else "")
        if plan and plan[1] > rate:
            tag = f"  [v6 k={plan[0]}]" + tag
        say(f"    n={n:2d} (OEIS a({oeis_index(n)})): {bytes_needed(n) / 2**30:9.2f} GiB "
            f"{'fits' if fits else '----'}  {np_ + 1:2d} primes  {hours:12.2f} h{tag}")
    log.put("projection", proj)

    target = args.target
    if args.auto:
        ok = [r["n"] for r in proj if r["fits"] and r["hours"] <= args.hours]
        target = max(ok) if ok else None
        say(f"    --auto: target n = {target}")
    if resume and "target" in resume:
        target = resume["target"]["n"]
    if not target:
        say(f"\ndone. send {path}")
        return 0

    # 6. exact target -----------------------------------------------------
    if bytes_needed(target) > 0.9 * free:
        say(f"\nn={target} needs {bytes_needed(target) / 2**30:.2f} GiB; only {free / 2**30:.2f} free")
        return 1
    primes = primes_for(target)
    from a007764_gpu import CRT_PRIMES_31BIT, crt
    extra = CRT_PRIMES_31BIT[len(primes)]
    engine = fastest if args.engine == "auto" else args.engine
    tplan = v6_plan(target)
    if args.engine == "auto" and tplan and tplan[1] > rate:
        engine = "v6"
    if env["backend"] == "cpu" and engine == "v1":
        engine = "v3"
    if env["backend"] == "cpu" and engine == "v6":
        engine = "v5"                     # CPU v6 only knows the 8 built-in primes
    if engine in ("v4", "v5", "v6") and target > 22:
        engine = "v1" if env["backend"] == "gpu" else "v3"      # v4 is 32-bit only
    tgt = log.data.get("target") or {"n": target, "engine": engine, "residues": {}}
    engine = tgt["engine"]
    log.put("target", tgt)
    say(f"\n[6] a({target}) with {len(primes)} primes + 1 confirmation prime, engine {engine}")
    todo = [p for p in primes + [extra] if str(p) not in tgt["residues"]]
    if env["backend"] == "gpu":
        import a007764_gpu as g

        def record(p, r, secs, dev):
            tgt["residues"][str(p)] = {"r": r, "seconds": secs, "device": dev}
            log.put("target", tgt)

        kw = {"chunk": be.chunk} if engine == "v2" else {}
        if engine == "v6":
            kw = {"k": (tplan[0] if tplan else 1)}
            say(f"    v6 with {kw['k']} residues per sweep")
        g.solve(target, primes=todo, devices=list(range(be.ndev)), engine=engine,
                on_residue=record, **kw)
    else:
        for p in todo:
            r, secs = timed(be.run, engine, target, p)
            tgt["residues"][str(p)] = {"r": r, "seconds": secs, "device": "cpu"}
            log.put("target", tgt)
            say(f"  [cpu] p={p}  a({target}) mod p = {r:>10d} ({secs:.1f}s)")
    res = {int(k): v["r"] for k, v in tgt["residues"].items()}
    value, _ = crt([res[p] for p in primes], primes)
    value2, _ = crt([res[p] for p in primes + [extra]], primes + [extra])
    tgt.update({"value": str(value), "bits": value.bit_length(), "digits": len(str(value)),
                "confirmed_by_extra_prime": value == value2})
    tgt["oeis_index"] = oeis_index(target)
    if target in known:
        tgt["matches_known"] = value == known[target]
        say(f"published OEIS a({oeis_index(target)}): {'MATCH' if value == known[target] else 'MISMATCH'}")
    log.put("target", tgt)
    say(f"\na({target}) [OEIS a({oeis_index(target)})] = {value}")
    say(f"{value.bit_length()} bits, {len(str(value))} digits; extra prime "
        f"{'confirms' if value == value2 else 'DISAGREES -- more primes needed'}")
    say(f"\ndone. send {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say("\ninterrupted; partial results are in the results file (use --resume)")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        if LOG is not None:
            LOG.put("error", traceback.format_exc())
        say("\nfailed; the traceback above and the results file are what to send")
        sys.exit(1)
