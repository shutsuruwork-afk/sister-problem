"""Compile the exact CUDA source with g++ against a tiny CUDA shim.

No GPU or nvcc needed.  Catches typos, type errors and undeclared names in
the device code before it ever reaches NVRTC.  It does not check CUDA
semantics (launch bounds, shared-memory limits, warp behaviour).

    python kaggle/cuda_syntax_check.py
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a007764_gpu  # noqa: E402

SHIM = r"""
#include <cstdint>
#include <cstddef>
#define __device__
#define __global__
#define __forceinline__ inline
#define __shared__
#define __syncthreads()
#define __CUDACC__ 1
struct Dim3 { unsigned x, y, z; };
static Dim3 threadIdx{0,0,0}, blockIdx{0,0,0}, blockDim{1,1,1}, gridDim{1,1,1};
static inline unsigned atomicCAS(unsigned* a, unsigned c, unsigned v){ unsigned o=*a; if(o==c)*a=v; return o; }
static inline unsigned long long atomicAdd(unsigned long long* a, unsigned long long v){ unsigned long long o=*a; *a=o+v; return o; }
"""


def main() -> int:
    src = a007764_gpu.cuda_source()
    import re
    src = re.sub(r"extern __shared__ u64 (\w+)\[\];", r"static u64 \1[65536];", src)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "cuda_syntax.cpp")
        with open(path, "w") as f:
            f.write(SHIM + "\n" + src)
        r = subprocess.run(["g++", "-std=c++11", "-fsyntax-only", "-Wall", "-Wextra",
                            "-Wno-unused-parameter", "-Wno-unused-variable", path],
                           capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    print(out if out else "CUDA source: syntax OK, no warnings")
    return r.returncode or (1 if out else 0)


if __name__ == "__main__":
    sys.exit(main())
