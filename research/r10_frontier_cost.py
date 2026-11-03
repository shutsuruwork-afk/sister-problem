"""r10: cost model for the unsolved frontier, n = 27 (OEIS a(28)).

Everything here is either measured in this repository or exact arithmetic;
the one quantity NOT known is how much faster a data-centre GPU runs this
kernel than the GTX 1660 SUPER, so compute is reported in
"GTX 1660 SUPER hours" (G-hours) and left for that ratio to convert.

  states        2B(27) = 771,439,013,240                (exact, F1/F18)
  work / sweep  (n+1)^2 * 2B(n) slot updates            (exact)
  rate          1.873 G slots/s at n=19 (v5, run 5), falling ~2%/n -> ~1.5 at n=27
  bits needed   a(27) ~ 586 bits (fit to published n<=26), budget 600
  memory        one residue plane of b bits costs 2B(n)*b/8 bytes per buffer
  inter-GPU     ~1-3% of writes leave their GPU with 8 rank-range shards (r09)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kaggle'))
from a007764_core import motzkin_numbers, oeis_known

M = motzkin_numbers(32)
n = 27
S = 2 * (M[n + 2] - M[n + 1])
work = (n + 1) ** 2 * S
known = oeis_known()
bits = [known[k].bit_length() for k in range(20, 27)]
step = bits[-1] - bits[-2]
est = bits[-1] + step + 2
rate = 1.873e9 * 0.98 ** (n - 19)
sweep_h = work / rate / 3600
print(f"n=27: 2B = {S:,} states, {work:.3e} slot updates per sweep")
print(f"published bit lengths n=20..26: {bits}  ->  a(27) ~ {est} bits; budget 600")
print(f"one sweep at the extrapolated GTX 1660 SUPER rate ({rate / 1e9:.2f} G/s): {sweep_h:,.0f} G-hours\n")

TiB = 2 ** 40
print(f"{'memory budget':>22} {'buffers':>8} {'bits/state':>10} {'sweeps':>7} {'G-hours':>10}")
for label, mem in (("8xB300 (1.97 TiB)", 2013 * 2 ** 30), ("2 nodes (3.93 TiB)", 2 * 2013 * 2 ** 30),
                   ("NVL72-class (13.5 TB)", 13.5e12)):
    for buffers in (2, 1):                         # ping-pong vs in-place
        b = int(mem * 8 / (buffers * S))           # residue bits that fit per state
        if b < 9:
            print(f"{label:>22} {buffers:>8} {b:>10}   too small (9-bit CRT floor, F7)")
            continue
        planes = -(-b // 31)                        # v6 planes, each a prime below 2^31
        carried = planes * (b // planes)            # prime width floor(b/planes) bits each
        sweeps = -(-600 // carried)
        print(f"{label:>22} {buffers:>8} {b:>10} {sweeps:>7} {sweeps * sweep_h:>10,.0f}")


# --------------------------------------------------------------------------
# v2 of the model (2026-11-03): real storage formats instead of ideal bits.
#   v7 packs a record of K residues x b bits (W = K*b <= 64) into 64-bit words,
#   f = floor(64/W) records per word  ->  64/f bits per state per buffer.
#   In place (r12, exact for n<=14): one buffer plus spill entries of about
#   0.105 x 2B(n) at peak; an entry is (offset in chunk, value).  Two spill
#   encodings: simple 64-bit entries, or packed 32-bit (20-bit offset + value,
#   needs b <= 12) -- the latter assumed only where it fits.
# --------------------------------------------------------------------------
SPILL = 0.105
print("\nwith real formats (v7 packing, r12 in-place spill):")
print(f"{'memory budget':>22} {'mode':>14} {'K x b':>7} {'bits/state':>10} {'CRT bits/sweep':>14} {'sweeps':>7} {'G-hours':>9}")
for label, mem in (("8xB300 (1.97 TiB)", 2013 * 2 ** 30), ("2 nodes (3.93 TiB)", 2 * 2013 * 2 ** 30),
                   ("NVL72-class (13.5 TB)", 13.5e12)):
    budget = mem * 8 / S                                     # bits per state, all buffers together
    for mode in ("ping-pong", "in-place"):
        best = None
        for K in range(1, 9):
            for b in range(9, 33):
                W = K * b
                if W > 64:
                    break
                slot = 64 / (64 // W)
                if mode == "ping-pong":
                    need = 2 * slot
                else:
                    entry = 32 if b <= 12 else 64
                    need = slot + SPILL * entry
                if need > budget:
                    continue
                carried = K * (b - 0.02)                     # moduli just below 2^b
                sweeps = -(-600 // int(carried))
                if best is None or sweeps < best[0]:
                    best = (sweeps, K, b, need, carried)
        if best:
            sw, K, b, need, carried = best
            print(f"{label:>22} {mode:>14} {K:>3} x {b:<2} {need:>10.1f} {carried:>14.1f} {sw:>7} {sw * sweep_h:>9,.0f}")
