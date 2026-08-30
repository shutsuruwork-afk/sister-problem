"""Experiment H-46 (Roadmap Route B / Multi-GPU AllReduce Topology Optimization):
NCCL Double Binary Tree vs Ring AllReduce for NVLink 4.0 8xB300 Collective Synchronization.

Theoretical Context:
--------------------
On an 8-GPU NVLink 4.0 system with 900 GB/s bidirectional interconnect:
- Ring AllReduce has latency 2*(P - 1)*alpha = 14*alpha and bandwidth term 2*(P - 1)/P * S / beta = 1.75 * S / beta.
- Double Binary Tree AllReduce has latency 2*log2(P)*alpha = 6*alpha and bandwidth term 2 * S / beta.
For small-to-medium frontier synchronization buffers (1 MB - 64 MB per frontier row),
Tree AllReduce drastically reduces step latency (6 hops vs 14 hops), speeding up multi-GPU barriers.

Classification:
---------------
Scope: Part 2 (Specific to 8xB300 NVLink 4.0 Cluster Infrastructure)
Functional Class: [B-Class: Infrastructure] GPU Collective AllReduce Optimization
"""

from __future__ import annotations
import math
import time
from typing import Dict, List, Tuple

KNOWN_A007764: Dict[int, int] = {
    1: 2,
    2: 12,
    3: 184,
    4: 8512,
    5: 1262816,
}


def simulate_ring_allreduce(buffer_size_mb: float, num_gpus: int = 8, link_bw_gbps: float = 900.0, base_latency_us: float = 1.2) -> Tuple[float, float]:
    """Simulate NCCL Ring AllReduce latency and throughput."""
    p = num_gpus
    s_gb = buffer_size_mb / 1024.0
    # Latency: 2 * (p - 1) * alpha
    lat_s = 2 * (p - 1) * (base_latency_us * 1e-6)
    # Bandwidth time: 2 * (p - 1) / p * (S / link_bw)
    bw_time_s = (2.0 * (p - 1) / p) * (s_gb / (link_bw_gbps / 8.0)) # link_bw in GB/s
    total_time_s = lat_s + bw_time_s
    bus_bw = s_gb / total_time_s # GB/s
    return total_time_s, bus_bw


def simulate_tree_allreduce(buffer_size_mb: float, num_gpus: int = 8, link_bw_gbps: float = 900.0, base_latency_us: float = 1.2) -> Tuple[float, float]:
    """Simulate NCCL Double Binary Tree AllReduce latency and throughput."""
    p = num_gpus
    s_gb = buffer_size_mb / 1024.0
    # Latency: 2 * log2(p) * alpha
    lat_s = 2 * math.log2(p) * (base_latency_us * 1e-6)
    # Bandwidth time: 2 * (S / link_bw) (tree splits bandwidth between two trees)
    bw_time_s = 2.0 * (s_gb / (link_bw_gbps / 8.0))
    total_time_s = lat_s + bw_time_s
    bus_bw = s_gb / total_time_s # GB/s
    return total_time_s, bus_bw


def benchmark_h46() -> bool:
    print("=" * 80)
    print("  EXPERIMENT H-46: NCCL Double Binary Tree vs Ring AllReduce on 8xB300 NVLink 4.0 ")
    print("=" * 80)

    # Frontier buffer sizes across DP steps: 2 MB (early), 16 MB (mid), 64 MB (peak)
    test_sizes_mb = [1.0, 4.0, 16.0, 64.0]
    total_tree_time = 0.0
    total_ring_time = 0.0

    print("\n[Step 1] AllReduce Latency & Effective Bandwidth Comparison across Buffer Sizes:")
    for sz in test_sizes_mb:
        t_ring, bw_ring = simulate_ring_allreduce(sz)
        t_tree, bw_tree = simulate_tree_allreduce(sz)
        total_ring_time += t_ring
        total_tree_time += t_tree
        speedup = t_ring / t_tree
        print(f"  Buffer {sz:4.1f} MB | Ring: {t_ring * 1e6:6.2f} us ({bw_ring:6.2f} GB/s) | Tree: {t_tree * 1e6:6.2f} us ({bw_tree:6.2f} GB/s) -> Speedup: {speedup:.2f}x")

    overall_speedup = total_ring_time / total_tree_time
    print(f"\n[Step 2] Overall Workload Cumulative Sync Latency Speedup: {overall_speedup:.2f}x")

    passed = overall_speedup >= 1.15
    print("\n" + "=" * 80)
    if passed:
        print(f"  DECISION: [ADOPTED] Double Binary Tree AllReduce achieves {overall_speedup:.2f}x speedup.")
        print("  INFRASTRUCTURE ACCELERATION: Reduces NVLink hop latency from 14 hops to 6 hops across 8 GPUs.")
    else:
        print(f"  DECISION: [PRUNED] Speedup ({overall_speedup:.2f}x) below threshold (1.15x).")
    print("=" * 80)
    return passed


if __name__ == "__main__":
    benchmark_h46()
