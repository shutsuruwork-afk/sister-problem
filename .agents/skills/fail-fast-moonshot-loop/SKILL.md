---
name: fail-fast-moonshot-loop
description: 10倍思考（10x Moonshot）による仮説の大量創出、全件順位付け、単一集中検証、高速切り捨て（Fail Fast）、実測値の定量的記録、および残存数半減時のアイデア自動補充を繰り返す超高速研究開発ループ。
---

# Fail-Fast Moonshot Research Loop Skill

このスキルは、未解決問題（OEIS A007764 等）に対し、10倍以上のブレークスルーをもたらすアイデアを大量創出し、1件ずつ徹底的に集中検証して高速に切り捨てる（Fail Fast）または本採用（Adopt）する研究開発ループの実行手順を定めます。

---

## コア規律 (Mandatory Disciplines)

1. **成果の 2分法分類ルール (Scope Distinction Mandate)**:
   - **Part 1（普遍的数理定理・大域的アルゴリズム）**:
     - 任意の $n \in \mathbb{N}$ で恒常的に成り立つ数学的定理、可換性証明、大域的アルゴリズム（対称直和分解、商空間全単射ランキング、モツキン数公式、並列CRT、行チェックポイント等）は必ず **Part 1** へ分類・記録する。
   - **Part 2（局所最適化・特定境界条件特化技術）**:
     - $n \le 28$（または $n \le 31$）、特定の素数幅（11-bit）、特定のハードウェア構造（64-bit Bitboard, SWAR ALU, L1キャッシュ常駐テーブル, Tensor Core GEMM等）など、**特定の状況でしか成り立たない技術は必ず Part 2** へ分類・記録する。

2. **1件ずつの単一集中検証（One-by-One Verification）**:
   - 複数の仮説をまとめて雑に検証してはならない。
   - 必ずアクティブキュー最上位の **単一仮説（Single Hypothesis）に 100% 集中** し、専用の実験スクリプトを作成して検証する。

3. **実測値による定量的証跡の必須記録（Empirical Benchmark Logging）**:
   - 「良さそうだ」「速くなりそうだ」という定性的な評価は一切禁止する。
   - 必ず **実測値（実行時間、メモリバイト数、スループット ops/sec、削減率、Ground Truth 完全一致ログ）** を測定し、後から誰でも追試できるように `math/BREAKTHROUGH_BENCHMARKS.md` に記録する。

4. **5-Tier 品質保証スイートの都度全数実行（Zero-Regression Baseline）**:
   - 仮説の採用時およびコード変更時は、必ず `python math/src/verify_all.py` を実行し、全 Tier（Tier 0〜5 + Bonus）が欠陥ゼロ（Zero Defects）で通過することを確認する。

5. **高速切り捨て（Fail Fast on Deficiency）**:
   - 10倍の飛躍をもたらさないもの、理論的破綻（エイリアシング、結合次元爆発、素数密度不足等）が判明したものは即座に `PRUNED` アーカイブへ隔離する。

6. **50% 閾値での自動大量補充（Replenishment at 50% Active Threshold）**:
   - アクティブ仮説数が初期値（$M_0 = 30$）の半分（15件）を切った時点で、得られたブレークスルーや幾何学的知見を土台として、新たな 10x 仮説群（15〜20件）を自動大量補充し、全件再スコアリングを行う。

---

## 7フェーズ実行ライフサイクル

```mermaid
graph TD
    P1["Phase 1: 10x Moonshot 大量創出 (30+件)"] --> P2["Phase 2: 全件スコアリング & グローバル順位付け"]
    P2 --> P3["Phase 3: 最上位 1件の単一集中検証"]
    P3 --> P4["Phase 4: 実測値ベンチマーク測定 & 5-Tier 検証"]
    P4 --> P5{"判定: 10x 達成 & 欠陥ゼロ?"}
    P5 -- "Yes" --> P6A["【ADOPTED】本採用 & 実測値ログ記録 & Part1/Part2 目次分類"]
    P5 -- "No" --> P6B["【PRUNED】理由を明記して即座に高速切り捨て"]
    P6A --> P7["Phase 6: 全体波及時の動的再順位付け"]
    P6B --> P7
    P7 --> P8{"残存アクティブ数 ≤ 50% ?"}
    P8 -- "Yes" --> P9["Phase 7: 第2世代 10x 仮説群の自動大量補充"]
    P9 --> P2
    P8 -- "No" --> P3
```

---

## 記録ファイル規約

1. `MOONSHOT_TRACKER.md`: 全仮説の順位、切り捨て、採用状況を動的更新。
2. `math/BREAKTHROUGH_TAXONOMY.md`: **Part 1（普遍的）** と **Part 2（特定状況）** に完全分離したマスター体系。
3. `math/BREAKTHROUGH_BENCHMARKS.md`: 全ブレークスルーの実測値・実行時間・スループット・検証ログ公式記録。
