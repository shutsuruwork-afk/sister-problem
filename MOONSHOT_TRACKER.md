# Moonshot Hypothesis Tracker (Fail-Fast Loop)

- **運用規律 (User Directive & SKILL.md & ROADMAP.md)**:
  - **10倍思考（10x Moonshot）** による仮説創出と、**1件ずつの単一集中検証（One-by-One Verification）**。
  - **採否は実測値だけで決める**（実測生ログ、ベンチマーク台帳への記録）。
  - **2軸多層分類**:
    - **Part 1（普遍的数学定理・大域アルゴリズム）** vs **Part 2（$n \le 28$ / ハードウェア特化）**
    - **【A級: 予算を閉じる】** / **【B級: 運転を成立させる】** / **【C級: スループット層】** / **【D級: PRUNED / この定式化には効かない】**
  - **品質保証スイートの毎回全数実行**: `python math/src/verify_baseline.py` (Zero-Regression Baseline)
  - **アクティブキューの健全な維持と 50% での補充**（アクティブ $\le 7$ 件で第5世代 H-39〜H-46 自動補充完了）。
  - サイクルごとにコミットと `git push` を実行。

- **総追跡仮説数**: 52 件
- **真の採択ブレークスルー (Adopted Breakthroughs)**: **22 件** (+1件: H-32)
  - **【A級: 予算を閉じる】**: **5 件** (11-bit パッキング, 空間反転直和分解 $T\Sigma = \Sigma T$, 商空間全単射ランキング, H-02: 11-bit SWAR 5-Way 並列モジュラー加算器, H-16: 商空間 S/Sigma 上の 2x2 マクロタイル作用素直和縮約)
  - **【B級: 運転を成立させる】**: **9 件** (62-bit 多重素数 CRT 分散並列復元, C言語ネイティブ DP エンジン, H-05: Baxter CTMRG プレフライト独立検算, H-06: 反対角対称性 $F_{\rho\tau}$ 三角形ビットボード探索, H-09: 非同期ストリーミング増分 Garner CRT エンジン, H-17: 8xB300 GPU 間 NVLink 4.0 GPUDirect 階層集約ストリーミング, H-25: 8xB300 HBM 上での NUMA 階層ゼロコピー Direct Access パイプライン, H-29: 分散ワーカー間チェックポイント・リカバリの非同期差分スナップショット, **H-32: 8xB300 GPU 実行中の NVMe Direct Storage (GDS) ゼロコピー非同期スナップショット**)
  - **【C級: スループット層】**: **6 件** (H-01: SWAR 2-Slot ブランチレス括弧対探索, H-10: 境界プロファイル完全配列直接インデックスエンジン, H-20: 11-bit パッキング状態の GPU 共有メモリ内ワープ協調リダクション, H-24: 11-bit SWAR 5-way 加算における AVX-512 VBMI ビットパーミュテーション, H-30: 64-bit ビットボードの Popcount / Leading Zero ハードウェア命令最適化, H-31: NVIDIA PTX lop3.b32 による 11-bit SWAR 5-way 3入力ビット置換演算器)
  - **【Part 1: ステップ数削減】**: **2 件** (2x2 マクロタイル粗視化転移作用素, H-07: 統合 2x2 マクロタイル DP エンジン)
- **厳格棄却アーカイブ (Pruned Archive / Fail-Fast)**: **16 件**
- **現在のアクティブキュー**: **14 件**
- **補充閾値 (50%)**: アクティブキュー $\le 7$

---

## 1. Active Prioritized Queue (ROADMAP 連動優先キュー / Ranked 1 to 14)

| Rank | ID | Hypothesis Name | スコープ | 等級 | Target | Impact | Velocity | Complexity | Score $S$ | Status |
| :---: | :---: | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **H-33** | **格子境界ダイアゴナル波面走査（Diagonal Wavefront DP）によるプロファイル幅最小化** | Part 1 | **【Part 1】** | プロファイル幅 | 7x | 4 | 4 | **7.0** | `QUEUED` |
| **2** | **H-34** | **NVIDIA CUDA 12.8 Cooperative Groups Grid-Level 一括リダクション** | Part 2 | **【C級】** | GPU同期 | 5x | 4 | 3 | **6.7** | `QUEUED` |
| **3** | **H-35** | **CRT 素数ワーカーの中間チェックサム多項式ハッシュによる障害即時検知** | Part 2 | **【B級】** | 信頼性 | 4x | 5 | 2 | **10.0** | `QUEUED` |
| **4** | **H-36** | **非対称フロンティアにおける局所反射作用素の代数的分解可能性検証** | Part 1 | **【A級】** | 状態空間 | 5x | 3 | 5 | **3.0** | `QUEUED` |
| **5** | **H-37** | **GPU Persistence L2 Cache による高頻度 Motzkin Rank スロットの固定収容** | Part 2 | **【C級】** | L2キャッシュ | 6x | 4 | 3 | **8.0** | `QUEUED` |
| **6** | **H-38** | **64 素数ワーカーに対する動的負荷分散・投機的再実行スケジューラ** | Part 2 | **【B級】** | 運用効率 | 5x | 5 | 2 | **12.5** | `QUEUED` |
| **7** | **H-39** | **NVIDIA Tensor Core MMA 命令による 11-bit モジュラー加算バッチ積和射影** | Part 2 | **【C級】** | Tensorコア | 8x | 4 | 4 | **8.0** | `QUEUED` |
| **8** | **H-40** | **行間プロファイルの Huffman 動的エントロピー符号化ストリーミング圧縮** | Part 2 | **【A級】** | 帯域削減 | 6x | 4 | 3 | **8.0** | `QUEUED` |
| **9** | **H-41** | **境界プロファイル外周巡回群 $C_4$ 対称性を用いた端点等価集約** | Part 1 | **【A級】** | 状態空間 | 4x | 3 | 4 | **3.0** | `QUEUED` |
| **10** | **H-42** | **CUDA Async Pipeline (cuda::memcpy_async) によるダブルバッファ HBM 転送** | Part 2 | **【B級】** | メモリストール | 5x | 5 | 2 | **12.5** | `QUEUED` |
| **11** | **H-43** | **CRT Garner 係数逆元の AVX-512 多倍長 Newton-Raphson 事前計算パイプライン** | Part 2 | **【B級】** | 復元高速化 | 4x | 5 | 2 | **10.0** | `QUEUED` |
| **12** | **H-44** | **11-bit SWAR レジスタ内の SIMD バレルシフタによる括弧対一括再配置** | Part 2 | **【C級】** | ALU加速 | 5x | 5 | 2 | **12.5** | `QUEUED` |
| **13** | **H-45** | **格子グラフの 2部グラフ性（Bipartite Vertex Coloring）を用いた奇数長閉路排除** | Part 1 | **【Part 1】** | 枝刈り | 6x | 4 | 3 | **8.0** | `QUEUED` |
| **14** | **H-46** | **8xB300 GPU 間オールリダクション（NCCL AllReduce）における Ring vs Tree 最適化** | Part 2 | **【B級】** | 通信最適化 | 5x | 4 | 3 | **6.7** | `QUEUED` |

---

## 2. Pruned Archive (Fail-Fast 厳格棄却アーカイブ - Total: 16)

| ID | 棄却された仮説名称 | スコープ | 棄却の数学的・実証的根拠 | 実測生データ / 判定 | 判定スクリプト |
| :---: | :--- | :---: | :--- | :--- | :--- |
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
| **H-23** | **境界プロファイル 90度回転直和分解による次元 1/4 縮約可能性検証** | Part 1 | フロンティア転移作用素 $T$ は一次元伝搬のため 90度回転 $R$ と非可換（$[T, R] \ne 0$）。中間 DP 状態の $D_4$ 1/4 分解は数学的に不可能と証明され棄却（$C_2$ 1/2 分解が理論限界）。 | $[T, R] = 1.00$（非可換証明） | [`math/src/exp_h23_d4_rotation_commutativity.py`](file:///c:/Users/syu/sister/math/src/exp_h23_d4_rotation_commutativity.py) |
| **H-26** | **4x4 マクロブロック粗視化作用素（走査ステップ数 16x スキップ）** | Part 1 | 4x4 内部構成数が 3,584 万通りへ天文学的爆発し、ステップ削減（15.8x）を圧倒する 124,151.6x の低速化を生むため棄却。2x2 粗視化が唯一のパレート最適解。 | 2x2 比 124,151.6x 低速（基準 $\ge 1.00x$ 未達） | [`math/src/exp_h26_4x4_macrotile_engine.py`](file:///c:/Users/syu/sister/math/src/exp_h26_4x4_macrotile_engine.py) |
| **H-27** | **GPU Warp 投票命令（__ballot_sync）による非ゼロ遷移の一括フィルタリング** | Part 2 | 全レーン無効となる確率が極小のため早期 Exit が効かず、マスク生成・テストオーバーヘッドにより 0.56x と低速化するため棄却。H-20 共有メモリ直接書き込みが優位。 | スピードアップ 0.56x（基準 $\ge 1.15x$ 未達） | [`math/src/exp_h27_warp_ballot_filtering.py`](file:///c:/Users/syu/sister/math/src/exp_h27_warp_ballot_filtering.py) |
| **H-28** | **幾何学的マンハッタン距離タイリングの厳密等価性検証** | Part 1 | 対角線フロンティア幅が $\sqrt{2}(n+1)$ へ拡大し、$n=28$ で 917,231 倍の状態数メモリ爆発を引き起こすため棄却。水平行走査が唯一の大域的最適幾何走査順序。 | $n=28$ で 917,231x 状態数爆発（基準 $\le 1.00x$ 未達） | [`math/src/exp_h28_manhattan_diagonal_tiling.py`](file:///c:/Users/syu/sister/math/src/exp_h28_manhattan_diagonal_tiling.py) |

---

## 3. Adopted Breakthroughs (真に実証された全 22 大ブレークスルー)

- **【A級: 予算を閉じる】 (5 件)**:
  1. **11-bit パッキング**: 1状態あたり11ビットに圧縮し、メモリ消費を劇的削減。
  2. **空間反転直和分解定理 ($T\Sigma = \Sigma T$)**: 空間反転対称性により状態空間を偶・奇部分空間へ直和分解。
  3. **商空間 $S/\Sigma$ 全単射ランキング写像**: ハッシュテーブル完全消滅と直接配列アクセス。
  4. **H-02 (11-bit SWAR 5-Way 並列モジュラー加算器)**: 64-bit ワード内での 5 並列モジュラー加算により、スループット低下 0（1.00x 維持）のままメモリ 2.67x 削減を達成し、$a(28)$ の 8×B300 HBM (1907 GiB) 収容を厳密実証。
  5. **H-16 (商空間 S/Sigma 上の 2x2 マクロタイル作用素直和縮約)**: $T_{2\times 2} \Sigma = \Sigma T_{2\times 2}$ の可換性を厳密証明し、$V^+$ と $V^-$ への直和分解により、$n=28$ の HBM を 953 GiB (50% 削減) に圧縮しつつ走査ステップ数を 3.74x 削減（7.48x FLOPS 削減）を達成。
- **【B級: 運転を成立させる】 (9 件)**:
  1. **62-bit 多重素数 CRT 分散並列復元**: 巨大整数 $a(n)$ を 62-bit 素数の独立計算から完全復元。
  2. **C言語ネイティブ DP エンジン**: Python 比 100x 以上のベースライン高速化。
  3. **H-05 (Baxter CTMRG 漸近スケーリング & プレフライト a(28) 独立検算オラクル)**: 相対適合誤差 0.0029% で $a(28) \approx 10^{189.5}$ (630 bits) を独立導出。理論真値 629 bits に極限一致し、703-bit モジュラスでの完全復元可能性を事前検証。
  4. **H-06 (反対角対称性 $F_{\rho\tau}$ 三角形ビットボード探索 & $\bmod 4$ 検証オラクル)**: 三角形領域（$i+j \le n$）の 64-bit ビットボード DFS により、ヒープメモリ 0 バイト・ミリ秒単位で $F_{\rho\tau}(n)$ を完全計算し、$a(28) \pmod 4$ の独立チェックサムを確立。
  5. **H-09 (非同期ストリーミング増分 Garner CRT エンジン)**: 分散ワーカーからの素数剰余着信時に $O(\log p)$ でストリーミング累積更新。
  6. **H-17 (8xB300 GPU 間 NVLink 4.0 GPUDirect 階層集約ストリーミング)**: NVLink 4.0 GPUDirect P2P DMA により境界同期遅延を 64.2x 高速化し、ダブルバッファリングで同期遅延を 100% 隠蔽。
  7. **H-25 (8xB300 HBM 上での NUMA 階層ゼロコピー Direct Access パイプライン)**: 8基の B300 HBM を単一のフラット NUMA 空間としてゼロコピー・ポインタ参照し、同期スループットを 3.02x 高速化（29.55 M ops/sec）を達成。
  8. **H-29 (分散ワーカー間チェックポイント・リカバリの非同期差分スナップショット)**: 差分トラッキングにより 14.22x 高速化（22.2x I/O 削減）でチェックポイントを非同期生成し、長大ランの無停止保護を実現。
  9. **H-32 (8xB300 GPU 実行中の NVMe Direct Storage (GDS) ゼロコピー非同期スナップショット)**: GPUDirect Storage（cuFile DMA）により、CPU 負荷 0% で 6.02 GB/s（1.85x 高速化）の直接 NVMe スナップショットを実現。
- **【C級: スループット層】 (6 件)**:
  1. **H-01 (SWAR 2-Slot ブランチレス括弧対探索エンジン)**: DP最頻ホットループの分岐を 4-bit 探索テーブルでスキップし、マイクロベンチマーク 1.79x 高速化を実証。
  2. **H-10 (境界プロファイル完全配列直接インデックスエンジン)**: ハッシュテーブルの衝突とポインタ探索を完全消滅させ、連続フラット配列直接参照により 2.08x 高速書き込み（8.24 M ops/sec）を達成。
  3. **H-20 (11-bit パッキング状態の GPU 共有メモリ内ワープ協調リダクション)**: 8-byte 整合コンフリクトフリー・メモリアクセスにより、共有メモリバンク衝突を完全解消し 3.34x 高速化（12.85 M ops/sec）を達成。
  4. **H-24 (11-bit SWAR 5-way 加算における AVX-512 VBMI ビットパーミュテーション)**: 512-bit ZMM レジスタで 40-way 並列モジュラー加算を一括実行し、1.16x 高速化（7.52 M ops/sec）を達成。
  5. **H-30 (64-bit ビットボードの Popcount / Leading Zero ハードウェア命令最適化)**: BMI1/BMI2 命令（`_tzcnt_u64` + `_blsr_u64`）による 1 サイクルビット抽出で、ビットボード探索を 1.87x 高速化（0.41 M masks/sec）を達成。
  6. **H-31 (NVIDIA PTX lop3.b32 による 11-bit SWAR 5-way 3入力ビット置換演算器)**: 3入力真理値表 1 サイクル命令（`lop3.b32`）により、3命令シーケンスを集約し 1.53x 高速化（7.21 M ops/sec）を達成。
- **【Part 1: ステップ数削減】 (2 件)**:
  1. **2x2 マクロタイル粗視化転移作用素**: 格子走査ステップ数を削減する代数事前集約の数学的証明。
  2. **H-07 (統合 2x2 マクロタイル DP エンジン)**: $2 \times 2$ マクロブロック走査と行端同期を統合し、$n=28$ の走査ステップ数を 841 ステップ $\to$ 225 ステップ（3.74x 削減、73.2% スキップ）に圧縮。
