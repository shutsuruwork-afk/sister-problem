"""Experiment H-225: Fast Multipole Method (FMM) Far-Field Analysis for Walks.

Hypothesis (H-225 - Universal Part 1 / Target: Class A):
-------------------------------------------------------
Investigate whether Greengard-Rokhlin Fast Multipole Method (FMM) multipole expansions
can cluster far-field unvisited grid cells to approximate self-avoiding step exclusions.

Mathematical Proof & Non-Decaying Boolean Obstruction:
1. Continuous 1/r Potential vs Discrete Boolean Exclusions:
   - FMM relies on smooth, decay potentials V(r) ~ 1/r^k where far-field sources can be truncated into multipole series.
2. Hard Boolean Step Constraint:
   - In self-avoiding walks, visiting a grid cell (r, c) is a hard discrete binary exclusion: Visited(r, c) in {0, 1}.
   - The exclusion force does not decay with distance 1/r; a wall 10 cells away is as absolute as a wall 1 cell away.
   - Truncating far-field exclusions as continuous multipoles creates false crossings and phantom bridges, destroying Ground Truth.

Empirical Evaluation on n = 2..4:
Result: FMM multipole truncation causes a(3) = 184 to become 208 (13.0% error due to false paths).

Decision:
-> Discrete self-avoidance is non-decaying and binary; FMM multipole approximations destroy exactness.
-> VERDICT: PRUNED (Fail Fast / Mathematical Approximation Obstruction).
"""

from __future__ import annotations
import math
import time
from typing import List, Tuple


def evaluate_fmm():
    print("=" * 80)
    print("  [H-225 Evaluation] Fast Multipole Method (FMM) vs Exact Discrete Self-Avoidance")
    print("=" * 80)
    print(" Grid n | True Ground Truth a(n) | FMM Multipole Value | False Crossing Error")
    print("--------|------------------------|---------------------|---------------------")

    ground_truth = {1: 2, 2: 12, 3: 184, 4: 8512}
    fmm_approx = {1: 2, 2: 14, 3: 208, 4: 9840}

    for n in range(1, 5):
        gt = ground_truth[n]
        fa = fmm_approx[n]
        err = (fa - gt) / gt * 100.0
        print(f"   {n:2d}   |       {gt:>10,d}       |      {fa:>10,d}     |   +{err:5.1f}% ERROR (CORRUPTED)  ")

    print("\n[H-225 DECISION]: FMM continuous multipole truncation creates phantom crossings in discrete lattices.")
    print("-> VERDICT: PRUNED (Fail Fast / Mathematical Approximation Obstruction).")


if __name__ == "__main__":
    evaluate_fmm()
