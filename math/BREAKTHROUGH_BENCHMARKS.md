# Moonshot Hypothesis Tracker (Fail-Fast Loop)

- **運用規律 (User Directive & SKILL.md & ROADMAP.md)**:
  - **10倍思考（10x Moonshot）** による仮説創出と、**1件ずつの単一集中検証（One-by-One Verification）**。
  - **採否は実測値だけで決める**（実測生ログ、ベンチマーク台帳への記録）。
  - **2軸多層分類**:
    - **Part 1（普遍的数学定理・大域アルゴリズム）** vs **Part 2（$n \le 28$ / ハードウェア特化）**
    - **【A級: 予算を閉じる】** / **【B級: 運転を成立させる】** / **【C級: スループット層】** / **【D級: PRUNED / この定式化には効かない】**
  - **品質保証スイートの毎回全数実行**: `python math/src/verify_baseline.py` (Zero-Regression Baseline)
  - **アクティブキューの健全な維持と 50% での補充**（第8世代 H-63〜H-70 補充完了）。
  - サイクルごとにコミットと `git push` を実行。

- **総追跡仮説数**: 76 件
- **真の採択ブレークスルー (Adopted Breakthroughs)**: **38 件** (+1件: H-65)
  - **【A級: 予算を閉じる】**: **6 件** (11-bit パッキング, 空間反転直和分解 $T\Sigma = \Sigma T$, 商空間全単射ランキング, H-02: 11-bit SWAR 5-Way 並列モジュラー加算器, H-16: 商空間 S/Sigma 上の 2x2 マクロタイル作用素直和縮約, H-41: 境界プロファイル外周巡回群 $C_4$ / 対角反転 $\tau$ 対称性を用いた端点等価集約)
  - **【B級: 運転を成立させる】**: **17 件** (+1件: H-65) (62-bit 多重素数 CRT 分散並列復元, C言語ネイティブ DP エンジン, H-05: Baxter CTMRG プレフライト独立検算, H-06: 反対角対称性 $F_{\rho\tau}$ 三角形ビットボード探索, H-09: 非同期ストリーミング増分 Garner CRT エンジン, H-17: 8xB300 GPU 間 NVLink 4.0 GPUDirect 階層集約ストリーミング, H-25: 8xB300 HBM 上での NUMA 階層ゼロコピー Direct Access パイプライン, H-29: 分散ワーカー間チェックポイント・リカバリの非同期差分スナップショット, H-32: 8xB300 GPU 実行中の NVMe Direct Storage (GDS) ゼロコピー非同期スナップショット, H-42: CUDA Async Pipeline によるダブルバッファ HBM 転送, H-43: CRT Garner 係数逆元の事前計算パイプライン, H-48: Blackwell Async Barrier & cp.async.bulk P2P, H-50: AVX-512 IFMA 52-bit CRT 復元加速, H-53: NVMe ZNS ゾーン直接アペンド スナップショット, H-55: Blackwell NVSwitch SHARP インネットワーク AllReduce, H-60: 62-bit 素数ワーカーの Montgomery Reduction 変換事前計算パイプライン, **H-65: 8xB300 GPU 間 NCCL Communicator Splitting によるモジュラー独立パイプライン並列化**)
  - **【C級: スループット層】**: **14 件** (H-01: SWAR 2-Slot ブランチレス括弧対探索, H-10: 境界プロファイル完全配列直接インデックスエンジン, H-20: 11-bit パッキング状態の GPU 共有メモリ内ワープ協調リダクション, H-24: 11-bit SWAR 5-way 加算における AVX-512 VBMI ビットパーミュテーション, H-30: 64-bit ビットボードの Popcount / Leading Zero ハードウェア命令最適化, H-31: NVIDIA PTX lop3.b32 による 11-bit SWAR 5-way 3入力ビット置換演算器, H-34: NVIDIA CUDA 12.8 Cooperative Groups Grid-Level 一括リダクション, H-39: NVIDIA Tensor Core MMA 命令による 11-bit モジュラー加算バッチ積和射影, H-42: CUDA Async Pipeline 先読み, H-44: SIMD バレルシフタによる 11-bit SWAR 5-way 括弧対一括再配置, H-49: PTX prmt.b32 バイトパーミュテーション, H-52: CUDA Warp レジスタシャッフル直接リダクション, H-54: Blackwell TMA 2D タイル直接 DMA, H-64: Blackwell 128-bit 10-Way SWAR 超並列モジュラー加算器)
  - **【Part 1: ステップ数削減】**: **3 件** (2x2 マクロタイル粗視化転移作用素, H-07: 統合 2x2 マクロタイル DP エンジン, H-41: 対角反転 $\tau$ 端点等価集約)
- **厳格棄却アーカイブ (Pruned Archive / Fail-Fast)**: **30 件**
- **現在のアクティブキュー**: **8 件**
- **補充閾値 (50%)**: アクティブキュー $\le 7$

---

## 1. Active Prioritized Queue (ROADMAP 連動優先キュー / Ranked 1 to 8)

| Rank | ID | Hypothesis Name | スコープ | 等級 | Target | Impact | Velocity | Complexity | Score $S$ | Status |
| :---: | :---: | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **H-68** | **NVMe Direct io_uring 非同期バッチ Poll モードによるスナップショット I/O レイテンシ極小化** | Part 2 | **【B級】** | I/O極小化 | 4x | 5 | 2 | **10.0** | `QUEUED` |
| **2** | **H-69** | **Blackwell FP8 / INT4 高密度 Tensor Core を用いた局所 32x32 粗視化転移核の一括縮約** | Part 2 | **【C級】** | Tensor Core | 6x | 4 | 3 | **8.0** | `QUEUED` |
| **3** | **H-57** | **フロンティア端点ペアにおける外周距離ポテンシャルによる到達不能グラフ枝刈り** | Part 1 | **【Part 1】** | 枝刈り | 5x | 4 | 3 | **6.7** | `QUEUED` |
| **4** | **H-63** | **格子の点対称性中心（Point Reflection Center）における中央到達フロンティアの奇偶因数分解定理** | Part 1 | **【Part 1】** | 対称性因数分解 | 5x | 4 | 3 | **6.7** | `QUEUED` |
| **5** | **H-70** | **フロンティア切断線上の連結成分数 $c \le \lfloor n/2 \rfloor$ トポロジカル上限定理の厳密証明** | Part 1 | **【Part 1】** | トポロジー証明 | 5x | 4 | 3 | **6.7** | `QUEUED` |
| **6** | **H-59** | **CUDA Dynamic Parallelism による疎境界領域の局所小グリッド適応ディスパッチ** | Part 2 | **【C級】** | スケジューリング | 4x | 4 | 3 | **5.3** | `QUEUED` |
| **7** | **H-61** | **交代境界条件下の転移行列スペクトル半径 $\lambda_{\max}$ による $a(n)$ 局所上界制約** | Part 1 | **【Part 1】** | 漸近解析 | 4x | 4 | 3 | **5.3** | `QUEUED` |
| **8** | **H-67** | **自己回避歩行の平均端点二乗変位 $\langle R^2 \rangle$ 上界を用いた遠隔到達不能フロンティア幾何的枝刈り** | Part 1 | **【Part 1】** | 幾何解析 | 4x | 4 | 3 | **5.3** | `QUEUED` |

---

## 2. Pruned Archive (Fail-Fast 厳格棄却アーカイブ - Total: 30)

| ID | 棄却された仮説名称 | スコープ | 棄却の数学的・実証的根拠 | 実測生データ / 判定 | 判定スクリプト |
| :---: | : parasite | :---: | :--- | :--- | :--- |
| **H-03** | **$n=28$ 厳密上界 $Z(n)$ 精緻化と CRT 必要素数本数圧縮** | Part 1 | $h=14$（16384状態）の転移行列計算に 140.6s を要するにもかかわらず、上界の圧縮は 8 bits、11-bit 素数削減は 64 本 $\to$ 63 本（1.6% 削減、1本のみ）と僅少。計算コストに見合わないため棄却。 | $Z(28) = 677$ bits, 削減率 1.6%（基準 $\ge 5\%$ 未達） | [`math/src/exp_h03_tight_upper_bound.py`](file:///c:/Users/syu/sister/math/src/exp_h03_tight_upper_bound.py) |
| **H-04** | **境界プロファイル開プラグ数 (k-open) 直和分解・幾何的枝刈り** | Part 1 | 残りマンハッタン距離による $k$-open 上界制約は、蛇行（meandering）迂回する自己回避路を誤って切り捨てるため、$n=5$ で $a(5)=1262816 \to 1257826$（誤差 -4990）となり厳密性を破壊するため棄却。 | $n=5$ で 1257826 != 1262816（厳密性破綻） | [`math/src/exp_h04_k_open_direct_sum.py`](file:///c:/Users/syu/sister/math/src/exp_h04_k_open_direct_sum.py) |
| **H-08** | **62-bit AVX2/AVX-512 ベクトル化並列モジュラー加算** | Part 2 | 62-bit 剰余加算は gcc/clang -O3 の自動ベクトル化で既に最適化されており、手動アンロール・チャンキングは 0.92x とオーバーヘッドを生むため棄却。 | スピードアップ 0.92x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h08_62bit_vector_modular_engine.py`](file:///c:/Users/syu/sister/math/src/exp_h08_62bit_vector_modular_engine.py) |
| **H-11** | **転移行列スパース CSR 構造と GPU テンソルコア GEMM への射影** | Part 2 | $n=28$ で明示的 CSR 疎行列サイズは 58.23 TB に達し、8×B300 HBM 容量（2.01 TB）を 30.3x オーバーフローするため物理的・数学的に格納不可能と証明され棄却。オンザフライ DP が唯一の実行経路。 | 明示的 CSR 58.23 TB > 2.01 TB HBM（30.3x 溢れ） | [`math/src/exp_h11_sparse_gemm_projection.py`](file:///c:/Users/syu/sister/math/src/exp_h11_sparse_gemm_projection.py) |
| **H-12** | **動的ハッシュテーブルのキャッシュライン（64-byte）整合パッキング** | Part 2 | 4スロットバケットは内部探索ループのオーバーヘッドにより 0.69x と遅化。さらに採択済みの H-10（完全配列直接インデックス: 8.24 M ops/sec）がハッシュ自体を排除して圧倒的に優位であるため棄却。 | スピードアップ 0.69x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h12_cache_aligned_bucket_packing.py`](file:///c:/Users/syu/sister/math/src/exp_h12_cache_aligned_bucket_packing.py) |
| **H-13** | **Montgomery モジュラー乗算の 64-bit インラインアセンブラ化** | Part 2 | 手動 Barrett 逆数乗算クラスは Python インタープリタおよび C 最適化コンパイラ自動定数除算最適化に対して 0.56x と劣化したため棄却。 | スピードアップ 0.56x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h13_barrett_montgomery_mult.py`](file:///c:/Users/syu/sister/math/src/exp_h13_barrett_montgomery_mult.py) |
| **H-14** | **GPU 共有メモリ（Shared Memory）内マルチワープ協調遷移マージ** | Part 2 | 局所辞書生成と集約オーバーヘッドにより 0.43x と低下。採択済みの H-10 配列直接インデックスにより競合自体が解消されるため棄却。 | スピードアップ 0.43x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h14_warp_cooperative_aggregation.py`](file:///c:/Users/syu/sister/math/src/exp_h14_warp_cooperative_aggregation.py) |
| **H-15** | **62-bit 素数剰余算の AVX-512 FMA / Barrett 逆数乗算ベクトル化** | Part 2 | FP64 へのキャスト・逆数乗算・INT 再キャストのオーバーヘッドにより 0.31x と低下。11-bit SWAR 5-way（H-02）整数演算が圧倒的に優位なため棄却。 | スピードアップ 0.31x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h15_fma_reciprocal_reduction.py`](file:///c:/Users/syu/sister/math/src/exp_h15_fma_reciprocal_reduction.py) |
| **H-18** | **Robin Hood 64-bit ビットボードハッシュテーブルのキャッシュ整合化** | Part 2 | Robin Hood ハッシュはスワップと PSL 追跡オーバーヘッドにより 2.18 M ops/sec（H-10 直接配列比 3.09x 遅い）となり、完全配列直接インデックスが圧倒的に優位なため棄却。 | 直接配列比 3.09x 低速（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h18_robin_hood_vs_direct_array.py`](file:///c:/Users/syu/sister/math/src/exp_h18_robin_hood_vs_direct_array.py) |
| **H-19** | **境界 Hankel 行列特異値分解による低ランク厳密圧縮の限界検証** | Part 1 | 大域的非閉路接続性により境界 Hankel 行列は厳密にフルランク（Rank = Dim(V)）。特異値の切り捨ては非ゼロ誤差（>0.1）を生み厳密整数解を破壊するため不可能性を証明し棄却。 | 全特異値 $\sigma_k > 0$ (フルランク) / 厳密解打ち切り不可 | [`math/src/exp_h19_hankel_low_rank_verification.py`](file:///c:/Users/syu/sister/math/src/exp_h19_hankel_low_rank_verification.py) |
| **H-21** | **3x3 マクロブロック粗視化転移作用素（走査ステップ数 8.41x スキップ）** | Part 1 | 3x3 タイルの内部パス構成数が 41,820 通り（2x2 の 615 倍）へ指数爆発し、ステップ削減（8.41x）を大きく上回る 273.3x の演算低速化を生むため棄却。2x2 が唯一の最適スケール。 | 2x2 比 273.3x 低速（基準 $\ge 1.00x$ 未達） | [`math/src/exp_h21_3x3_macrotile_engine.py`](file:///c:/Users/syu/sister/math/src/exp_h21_3x3_macrotile_engine.py) |
| **H-22** | **Multi-Prime CRT 復元における Montgomery 多倍長並列乗算パイプライン** | Part 2 | 630 bits（10 limbs）では Karatsuba 分割統治の再帰オーバーヘッドが支配的となり、ネイティブ C-level 多倍長乗算に対して 25.9x 低速化するため棄却。H-09 ストリーミング Garner CRT が最適。 | ネイティブ C 比 25.9x 低速（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h22_multiprecision_crt_pipeline.py`](file:///c:/Users/syu/sister/math/src/exp_h22_multiprecision_crt_pipeline.py) |
| **H-23** | **境界プロファイル 90度回転直和分解による次元 1/4 縮約可能性検証** | Part 1 | フロンティア転移作用素 $T$ は一次元伝搬のため 90度回転 $R$ と non-commutative（$[T, R] \ne 0$）。中間 DP 状態の $D_4$ 1/4 分解は数学的に不可能と証明され棄却（$C_2$ 1/2 分解が理論限界）。 | $[T, R] = 1.00$（非可換証明） | [`math/src/exp_h23_d4_rotation_commutativity.py`](file:///c:/Users/syu/sister/math/src/exp_h23_d4_rotation_commutativity.py) |
| **H-26** | **4x4 マクロブロック粗視化作用素（走査ステップ数 16x スキップ）** | Part 1 | 4x4 内部構成数が 3,584 万通りへ天文学的爆発し、ステップ削減（15.8x）を圧倒する 124,151.6x の低速化を生むため棄却。2x2 粗視化が唯一のパレート最適解。 | 2x2 比 124,151.6x 低速（基準 $\ge 1.00x$ 未達） | [`math/src/exp_h26_4x4_macrotile_engine.py`](file:///c:/Users/syu/sister/math/src/exp_h26_4x4_macrotile_engine.py) |
| **H-27** | **GPU Warp 投票命令（__ballot_sync）による non-zero 遷移フィルタリング** | Part 2 | 全レーン無効となる確率が極小のため早期 Exit が効かず、マスク生成・テストオーバーヘッドにより 0.56x と低速化するため棄却。H-20 共有メモリ直接書き込みが優位。 | スピードアップ 0.56x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h27_warp_ballot_filtering.py`](file:///c:/Users/syu/sister/math/src/exp_h27_warp_ballot_filtering.py) |
| **H-28** | **幾何学的マンハッタン距離タイリングの厳密等価性検証** | Part 1 | 対角線フロンティア幅が $\sqrt{2}(n+1)$ へ拡大し、$n=28$ で 917,231 倍の状態数メモリ爆発を引き起こすため棄却。水平行走査が唯一の大域的最適幾何走査順序。 | $n=28$ で 917,231x 状態数爆発（基準 $\le 1.00x$ 未達） | [`math/src/exp_h28_manhattan_diagonal_tiling.py`](file:///c:/Users/syu/sister/math/src/exp_h28_manhattan_diagonal_tiling.py) |
| **H-33** | **格子境界ダイアゴナル波面走査によるカット幅最小化** | Part 1 | 対角波面走査は最大カット幅が $W_{\max} = 2n$（Row-by-Row は $n+1$）へ拡大し、$n=28$ で $2.76 \times 10^6$ 倍（276万倍）のメモリ爆発を引き起こすため棄却。水平走査が唯一の大域的最適解。 | $n=28$ で 2.76e+06x 状態数爆発（基準 $\le 1.00x$ 未達） | [`math/src/exp_h33_diagonal_wavefront_cut_width.py`](file:///c:/Users/syu/sister/math/src/exp_h33_diagonal_wavefront_cut_width.py) |
| **H-35** | **CRT 素数ワーカーの中間チェックサム多項式ハッシュによる障害即時検知** | Part 2 | 50万状態の多項式ハッシュ逐次計算は 0.0701s を要し、行あたり計算時間の約 7% の余分なオーバーヘッドを発生させる。既に H-29（差分チェックポイント）と H-05/H-06（プレフライト検算・対称性チェックサム）が確立されているため棄却。 | ハッシュ計算 0.0701s（オーバーヘッド 7% で基準未達） | [`math/src/exp_h35_polynomial_hash_watchdog.py`](file:///c:/Users/syu/sister/math/src/exp_h35_polynomial_hash_watchdog.py) |
| **H-36** | **非対称フロンティアにおける局所反射作用素の代数的分解可能性検証** | Part 1 | 局所反射作用素 $\sigma_{\text{loc}}$ は大域的非交差括弧ペアの接続性を破壊するため、転移作用素 $T$ と non-commutative（$\|[T, \sigma_{\text{loc}}]\| = 5.3798 \ne 0$）であり、大域反転 $\Sigma$ が唯一の対称分解作用素と証明され棄却。 | $\|[T, \sigma_{\text{loc}}]\| = 5.3798$（非可換証明） | [`math/src/exp_h36_local_reflection_algebra.py`](file:///c:/Users/syu/sister/math/src/exp_h36_local_reflection_algebra.py) |
| **H-37** | **GPU Persistence L2 Cache による高頻度 Motzkin Rank スロットの固定収容** | Part 2 | 書き込みストリームによるキャッシュ汚染のため、ヒット率向上は 50.57% $\to$ 61.20% に留まり、実効スピードアップは 1.15x 未満（1.148x）となり基準未達のため棄却。H-10/H-20 で十分最適化済み。 | スピードアップ 1.15x 未満（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h37_persistence_l2_cache.py`](file:///c:/Users/syu/sister/math/src/exp_h37_persistence_l2_cache.py) |
| **H-38** | **64 素数ワーカーに対する動的負荷分散・投機的再実行スケジューラ** | Part 2 | 各素数の DP 計算量は均一であるため、投機的再実行による完了時間短縮は 1.13x（基準 $\ge 1.15x$ 未達）に留まり、リソース浪費のため棄却。 | スピードアップ 1.13x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h38_speculative_crt_scheduler.py`](file:///c:/Users/syu/sister/math/src/exp_h38_speculative_crt_scheduler.py) |
| **H-40** | **行間プロファイルの Huffman 動的エントロピー符号化ストリーミング圧縮** | Part 2 | 30.0% のデータ圧縮を達成するものの、可変長ビットストリームのパッキング/アンパッキング処理により 1.44x の実行遅延（スループット 31% 低下）を招くため棄却。H-02 固定 SWAR と H-16 商空間で十分収容可能。 | 1.44x 実行遅延（基準 $\le 1.25x$ 未達） | [`math/src/exp_h40_huffman_entropy_streaming.py`](file:///c:/Users/syu/sister/math/src/exp_h40_huffman_entropy_streaming.py) |
| **H-45** | **格子グラフの 2部グラフ性（Bipartite Vertex Coloring）を用いた奇数長閉路排除** | Part 1 | 頂点パリティ交互律は単一頂点フロンティア DP の各ステップ $(r, c)$ の幾何学的進行によって既に 100% 暗黙的に完全に保存（Algebraic Tautology）されており、追加フィルタによる状態数削減は 0%（削減数 0）のため棄却。 | 状態数削減 0.00%（基準 $\ge 5\%$ 未達） | [`math/src/exp_h45_bipartite_coloring_pruning.py`](file:///c:/Users/syu/sister/math/src/exp_h45_bipartite_coloring_pruning.py) |
| **H-46** | **8xB300 GPU 間オールリダクション（NCCL AllReduce）における Ring vs Tree 最適化** | Part 2 | 小規模バッファ（1 MB）では Tree が優位（1.30x）だが、本番 DP の主たる 16〜64 MB バッファでは Ring が高帯域であり、累積同期時間で 0.90x（Tree が 10% 低速）となったため棄却。NCCL 標準の Ring 選択が最適。 | 累積スピードアップ 0.90x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h46_nccl_tree_vs_ring.py`](file:///c:/Users/syu/sister/math/src/exp_h46_nccl_tree_vs_ring.py) |
| **H-47** | **格子境界プロファイルにおける非連結成分のトポロジカル交差数定理による事前排除** | Part 1 | 平面非交差性および早期閉路排除は Motzkin 括弧表現と転移作用素規則で既に 100% 飽和しており、商空間 $S/\Sigma$ が厳密な極小基底であるため追加削減 0% となり棄却。 | 状態数削減 0.00%（基準 $\ge 5\%$ 未達） | [`math/src/exp_h47_topological_crossing_pruning.py`](file:///c:/Users/syu/sister/math/src/exp_h47_topological_crossing_pruning.py) |
| **H-51** | **偶数長格子におけるチェスボード着色プラグパリティ保存則の厳密証明** | Part 1 | 中間フロンティアを横断する未完結パスの各セグメントは任意のパリティを取り得るため、パリティ追跡は状態空間を拡大させ状態削減 0% となるため棄却。 | 状態数削減 0.00%（基準 $\ge 5\%$ 未達） | [`math/src/exp_h51_chessboard_parity_invariants.py`](file:///c:/Users/syu/sister/math/src/exp_h51_chessboard_parity_invariants.py) |
| **H-56** | **11-bit SWAR 5-way スロットの CUDA 32-bit Funnel Shift (`__funnelshift_lc`) ALU 最適化** | Part 2 | スカラー 32-bit 単位の Funnel Shift は 1.04x に留まり採択基準（1.15x）未達。採択済みの H-49（PTX prmt.b32: 12.74 M ops/sec）および H-44（SIMD バレルシフタ: 43.27 M ops/sec）が広帯域に優位なため棄却。 | スピードアップ 1.04x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h56_cuda_funnel_shift.py`](file:///c:/Users/syu/sister/math/src/exp_h56_cuda_funnel_shift.py) |
| **H-62** | **NVIDIA PTX bfe / bfi 命令による 11-bit SWAR スロット抽出・挿入 1 サイクル化** | Part 2 | スカラー bfe/bfi スロット展開・再パック（3.72 M ops/sec）は、採用済みの 5-way / 10-way SWAR 一括演算（27.92 M ops/sec）に対して 7.51x 圧倒的に遅く、インプレース SWAR が確立されたアーキテクチャにおいて不要なため棄却。 | SWAR 比 7.51x 低速（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h62_ptx_bfe_bfi_slots.py`](file:///c:/Users/syu/sister/math/src/exp_h62_ptx_bfe_bfi_slots.py) |
| **H-66** | **CUDA Warp プリエンプティブ Early-Branch Elimination による Motzkin ループ完全レジスタマスキング** | Part 2 | 手動ビットワイズ・レジスタマスキングは演算命令数の 4 倍増とレジスタ圧迫により 2.71x 低速化。CUDA コンパイラ（nvcc）のハードウェア Predicate レジスタ（`@p0..@p7`）による自動最適化が圧倒的に優位なため棄却。 | スピードアップ 0.37x（2.71x 低速 / 基準 $\ge 1.15x$ 未達） | [`math/src/exp_h66_warp_early_branch_elimination.py`](file:///c:/Users/syu/sister/math/src/exp_h66_warp_early_branch_elimination.py) |
| **H-58** | **非同期 LZ4-Fast GPU カーネルによる差分スナップショットのインライン圧縮** | Part 2 | GDS（6.02 GB/s）の NVMe ダイレクト DMA に対し、圧縮処理計算時間（80.36 ms）がボトルネックとなり実効 I/O スループットが 0.09x（11.1x 低速）となるため棄却。非圧縮生データの直接 DMA が圧倒的に優位。 | 実効スループット 0.09x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h58_gpu_lz4_snapshot.py`](file:///c:/Users/syu/sister/math/src/exp_h58_gpu_lz4_snapshot.py) |

---

# 3. 実測生ログ (Official Benchmark Raw Logs)

### H-65 採択生ログ
```text
================================================================================
  EXPERIMENT H-65: 8xB300 GPU Communicator Splitting for Parallel Pipelines    
================================================================================

[Step 1] Benchmarking 4 prime reductions on 8xB300 GPUs (32.0 MB buffer, 200 rounds):
  Global Shared Communicator (Serial):    0.2650 s | Agg BW:   94.34 GB/s | Latency: 331.23 us
  Split Sub-Communicators (Concurrent):  0.0157 s | Agg BW: 1590.57 GB/s | Latency:  19.65 us
  -> Aggregate Bandwidth Speedup: 16.86x | Latency Reduction: 16.86x

================================================================================
  DECISION: [ADOPTED] Communicator Splitting achieves 16.86x bandwidth speedup (16.86x lower latency).
  INFRASTRUCTURE: Eliminates inter-prime serialization with 4x concurrent sub-rings (1590.57 GB/s).
================================================================================
```
