# A007764 — frontier DP engine (v1, v2)

For running on your own machine see `../local/README.md`.

Self-contained Kaggle notebook plus the sources it embeds.

| file | role |
|---|---|
| `a007764_core.py` | Motzkin tables, bijective profile ranking, two independent CPU reference DPs |
| `a007764_kernel.h` | device code shared verbatim by the CPU test and the CUDA kernel |
| `a007764_cuda.cu` | CUDA kernels (`dp_step`, `row_end`, `terminal_sum`) |
| `a007764_v2.h` | v2 device code: incremental ranking (research r05/r06), shared by CPU and CUDA |
| `a007764_cuda_v2.cu` | CUDA entry point for v2 (`v2_step`) |
| `a007764_cpu.c` | CPU/OpenMP driver for v2; same chunk decomposition as the GPU |
| `a007764_gpu.py` | CuPy driver (v1 and v2), CRT, multi-GPU prime scheduling |
| `cuda_syntax_check.py` | compiles the exact CUDA source with g++ against a shim (no GPU needed) |
| `build_notebook.py` | regenerates the notebook by embedding the four files above |
| `a007764_t4x2.ipynb` | the notebook to upload to Kaggle (GPU T4 x2) |

## Running it

Upload `a007764_t4x2.ipynb`, set the accelerator to **GPU T4 x2**, run all.
The notebook writes its own sources, so nothing else needs to be uploaded.

`TARGET_N` in section 7 defaults to **20**. `21` also fits a single T4
(10.86 GiB of the 15 GiB); `22` needs 30.74 GiB and does not fit.

## What is verified

Run locally without a GPU:

```
python3 -c "import sys; sys.path.insert(0,'kaggle'); import a007764_core as c; \
  [print(n, c.a_n_dense(n) == c.KNOWN_A007764[n]) for n in range(1,10)]"
gcc -O2 -Ikaggle -o /tmp/tk kaggle/test_kernel.c && /tmp/tk 1 12  # device code on CPU
```

- profile ranking is bijective onto `[0, B(n))` — exhaustive round-trip, n ≤ 8
- the dense array is exactly `2*B(n)` long and **100% occupied**
- both CPU DPs and the device code reproduce all twelve known OEIS terms

## What is not claimed

`a(28)` is not computed and cannot be on this hardware. Section 9 extrapolates
from the measured rate only. See `../AUDIT_PHASE1_PHASE2.md`.
