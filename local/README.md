# Running locally

One command verifies the engines, cross-checks them, benchmarks, projects,
and optionally computes a term exactly.  Everything lands in
`results/run_<UTC>.json`; that file is the thing to send back.

## Setup

GPU (NVIDIA, any card with compute capability ≥ 6.0):

```bash
nvidia-smi                       # note the "CUDA Version" in the top right
pip install numpy cupy-cuda12x   # driver CUDA 12.x; use cupy-cuda11x for 11.x
python -c "import cupy; print(cupy.cuda.runtime.getDeviceCount())"
```

The kernels are compiled at run time by NVRTC.  If that step fails with a
missing `nvrtc` library, install the CUDA Toolkit matching your driver, or
`pip install nvidia-cuda-nvrtc-cu12`.

CPU fallback (no GPU, or CuPy will not install): needs `gcc` with OpenMP.
Used automatically when CuPy is unavailable, or with `--cpu`.

## Run

```bash
git clone -b claude/antigravity-research-progress-ugqfqc \
    https://github.com/shutsuruwork-afk/sister-problem
cd sister-problem
python local/run_local.py            # ~minutes: verify, cross-check, benchmark, projection
```

Then, if you want a full term:

```bash
python local/run_local.py --target 20           # exact a(20)
python local/run_local.py --auto --hours 3      # largest n that fits memory and 3 h
python local/run_local.py --resume results/run_XXXX.json   # continue after Ctrl-C
python local/run_local.py --oeis --target 20    # also compare with the published OEIS terms
```

`--target` uses the fastest engine measured in step 4 unless `--engine` says
otherwise.  `--oeis` makes one GET request to the public OEIS b-file and
nothing else.

## What each step does

| step | what | stops the run if |
|---|---|---|
| 1 | records Python, OS, CuPy/CUDA versions, GPU names and memory | — |
| 2 | every engine (v1, v2, v3) reproduces OEIS a(1..12) mod p | any mismatch |
| 3 | the engines (independent implementations) agree for n=13..16 | any disagreement |
| 4 | tunes the v2 chunk size, times every engine for n=16..19 (they must agree at each n), then a bottleneck probe splits v1/v3 time into compute vs memory+atomics | any disagreement |
| 5 | projects memory and time for n=16..28 from the fastest engine's rate | — |
| 6 | (`--target`/`--auto`) one sweep per CRT prime across all GPUs, plus one extra prime that must not change the value | — |

Memory per GPU for the target run is `2 × 2B(n) × 4` bytes:
n=20 → 3.85 GiB, n=21 → 10.86 GiB, n=22 → 30.74 GiB.

No host name or user name is written to the results file.
