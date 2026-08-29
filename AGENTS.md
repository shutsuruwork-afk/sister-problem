# Agent Directives for Sister-Problem Project

This project aims to conquer the unsolved frontier of counting self-avoiding walks on square grids (OEIS A007764 / $a(28)$).

## Core Principles

1. **Fail-Fast Moonshot Skill Execution**:
   - Activate and strictly adhere to `.agents/skills/fail-fast-moonshot-loop/SKILL.md`.
   - Never settle for small incremental tweaks when 10x breakthroughs are possible.
   - Maintain the active hypothesis queue, prioritize rigorously, verify one by one, prune aggressively, re-rank dynamically, and replenish when below 50%.

2. **Mandatory 5-Tier Verification Baseline**:
   - Every code change, algorithmic implementation, and theoretical claim MUST satisfy all 5 tiers defined in `VERIFICATION.md` via `python math/src/verify_all.py`.
   - Zero regression and zero untested code allowed.

3. **Branch Hygiene**:
   - All experimental work and contributions are developed on `Antigravity/` branches.
