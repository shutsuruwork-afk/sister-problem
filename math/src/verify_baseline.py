#!/usr/bin/env python3
"""A007764 の基本形検証 — 何もかもの照合相手になる参照実装。

速度ではなく**明白な正しさ**を優先する。最適化された各エンジンは、最終的にこの実装と
一致することで正当性を主張する。ここが崩れたら、他のどの数字も意味を持たない。

やること:
  1. a(n) を厳密に計算し、OEIS A007764 の既知値と照合する
  2. 境界状態数の閉形式 B(n) = M_{n+2} - M_{n+1} を、実測の状態数と照合する
     （この実装は閉形式を仮定していないので、一致は独立な確認になる）
  3. スループットを実測し、n=28 での実寸を出す（実寸表の実測アンカー）

  python verify_baseline.py              # 既定 n<=8（約 1 秒）
  python verify_baseline.py --max-n 10   # 約 30 秒
  python verify_baseline.py --sheet      # 実寸表を出力

終了コード: 0 = 全一致 / 1 = 1 つでも不一致。
"""
from __future__ import annotations

import argparse
import sys
import time

# OEIS A007764: (n+1)x(n+1) 格子点上の (0,0) -> (n,n) 自己回避経路数
KNOWN_A007764 = {
    1: 2, 2: 12, 3: 184, 4: 8512, 5: 1262816, 6: 575780564,
    7: 789360053252, 8: 3266598486981642, 9: 41044208702632496804,
    10: 1568758030464750013214100,
    11: 182413291514248049241470885236,
    12: 64528039343270018963357185158482118,
}

PRODUCTION_N = 28          # 律速のある本番規模
STORED_STATES_28 = 1_489_362_193_002   # ROADMAP の main+blocked 実測


def motzkin(k: int) -> list[int]:
    m = [1, 1]
    for i in range(2, k + 1):
        m.append(((2 * i + 1) * m[i - 1] + 3 * (i - 1) * m[i - 2]) // (i + 2))
    return m


def boundary_states(n: int) -> int:
    """境界状態数の閉形式 B(n) = M_{n+2} - M_{n+1}。"""
    m = motzkin(n + 2)
    return m[n + 2] - m[n + 1]


def _canon(plugs) -> tuple:
    """通常成分（2 以上）を出現順に振り直す。1 は始点断片の自由端なので固定。"""
    remap, nxt, out = {}, 2, []
    for v in plugs:
        if v <= 1:
            out.append(v)
        else:
            if v not in remap:
                remap[v] = nxt
                nxt += 1
            out.append(remap[v])
    return tuple(out)


def solve(n: int, record_rows: bool = False):
    """a(n) を厳密に返す。record_rows=True なら行境界ごとの状態数も返す。

    状態は長さ n+2 のタプル。0..n が各列の下向きプラグ、n+1 が右向き（水平）プラグ。
    値: 0 = プラグなし / 1 = 始点 (0,0) を含む断片の自由端 / k>=2 = 通常断片
    （同じラベルが必ず 2 個あり、断片の 2 つの自由端を表す）。

    各頂点の次数は 0 か 2。ただし (0,0) と (n,n) だけは 1。
    自己回避性は「次数 <= 2」から、非閉路性は「同一断片の両端を繋がない」から従う。
    """
    W = n + 1
    cur = {tuple([0] * (W + 1)): 1}
    rows: list[int] = []

    for i in range(W):
        for j in range(W):
            nxt: dict[tuple, int] = {}
            is_start = (i == 0 and j == 0)
            is_goal = (i == n and j == n)
            can_down, can_right = i < n, j < n

            for st, cnt in cur.items():
                up, left = st[j], st[W]
                base = list(st)

                def put(down_v, right_v, _b=base, _c=cnt, _n=nxt):
                    s = list(_b)
                    s[j] = down_v
                    s[W] = right_v
                    k = _canon(s)
                    _n[k] = _n.get(k, 0) + _c

                if is_start:
                    if up or left:
                        continue
                    if can_down:
                        put(1, 0)
                    if can_right:
                        put(0, 1)
                    continue

                if is_goal:
                    # 次数 1。到着するのは始点を含む断片（ラベル 1）でなければならない
                    if up and left:
                        continue
                    if (up or left) != 1:
                        continue
                    s = list(base)
                    s[j] = 0
                    s[W] = 0
                    if any(s):          # 取り残された断片があれば経路にならない
                        continue
                    k = tuple(s)
                    nxt[k] = nxt.get(k, 0) + cnt
                    continue

                if up == 0 and left == 0:
                    put(0, 0)                                    # 次数 0（この頂点を通らない）
                    if can_down and can_right:
                        m = max(base) + 1 if max(base) >= 2 else 2
                        put(m, m)                                # 新しい断片を作る
                elif up == 0 or left == 0:
                    v = up or left
                    if can_down:
                        put(v, 0)                                # 下へ伸ばす
                    if can_right:
                        put(0, v)                                # 右へ伸ばす
                else:
                    if up == left:
                        continue                                 # 閉路になる → 禁止
                    s = list(base)
                    if up == 1 or left == 1:                     # 始点断片と通常断片の合流
                        other = left if up == 1 else up
                        for t in range(W + 1):
                            if s[t] == other:
                                s[t] = 1
                    else:                                        # 通常断片どうしの合流
                        for t in range(W + 1):
                            if s[t] == left:
                                s[t] = up
                    s[j] = 0
                    s[W] = 0
                    k = _canon(s)
                    nxt[k] = nxt.get(k, 0) + cnt

            cur = nxt
        if record_rows and i < n:
            rows.append(len(cur))

    total = cur.get(tuple([0] * (W + 1)), 0)
    return (total, rows) if record_rows else total


def run_checks(max_n: int) -> tuple[bool, list[dict]]:
    print("=" * 74)
    print("  基本形検証 — 参照実装 vs OEIS A007764 / 境界状態数の閉形式")
    print("=" * 74)
    print(f"{'n':>3} {'a(n)':>26} {'照合':>6} {'実測状態数':>12} {'閉形式 B(n)':>12} {'一致':>5} {'秒':>7}")
    print("-" * 74)

    ok, samples = True, []
    for n in range(1, max_n + 1):
        t0 = time.perf_counter()
        a, rows = solve(n, record_rows=True)
        el = time.perf_counter() - t0

        gt = KNOWN_A007764.get(n)
        a_ok = (gt is None) or (a == gt)
        obs = max(rows) if rows else 0
        pred = boundary_states(n)
        b_ok = (obs == pred) if obs else True
        ok = ok and a_ok and b_ok

        print(f"{n:>3} {a:>26,d} {'OK' if a_ok else 'NG':>6} {obs:>12,d} {pred:>12,d} "
              f"{'OK' if b_ok else 'NG':>5} {el:>7.2f}")
        if n >= 5:
            samples.append({"n": n, "sec": el, "states": pred})
    return ok, samples


def sheet(samples: list[dict]) -> None:
    """実寸表 — 各行に「定義 / 実測 / 外挿」を付ける。投影を結果として読ませないため。"""
    if not samples:
        print("\n実測アンカーが取れていない（--max-n を 5 以上に）")
        return
    anchor = samples[-1]
    # 状態あたりの所要時間を実測から出し、状態数は閉形式（定義）で伸ばす
    sec_per_state = anchor["sec"] / anchor["states"]
    proj_sec = sec_per_state * STORED_STATES_28
    floor_gib = STORED_STATES_28 / 8 / 2**30          # 1 bit/state の物理下限

    print("\n" + "=" * 74)
    print(f"  実寸表 (n = {PRODUCTION_N})")
    print("=" * 74)
    rows = [
        ("状態数（DP が保持）", f"{STORED_STATES_28:,d}", "定義", "—"),
        ("メモリ下限（1 bit/state）", f"{floor_gib:,.0f} GiB", "定義", "これを割る主張は誤り"),
        ("メモリ（11-bit パッキング）", f"{STORED_STATES_28*11/8/2**30:,.0f} GiB", "定義",
         f"下限の {STORED_STATES_28*11/8/2**30/floor_gib:.1f} 倍"),
        (f"実測アンカー: n={anchor['n']} の所要", f"{anchor['sec']:.3f} 秒", "実測", "この参照実装での値"),
        ("1 状態あたり", f"{sec_per_state*1e6:.3f} マイクロ秒", "実測", "—"),
        (f"n={PRODUCTION_N} の所要（参照実装）", f"{proj_sec/3600/24/365:,.0f} 年", "外挿",
         "最適化前の桁を示すだけの値"),
    ]
    print(f"{'項目':<32}{'値':>22}  {'由来':<6}{'注'}")
    print("-" * 74)
    for k, v, src, note in rows:
        print(f"{k:<32}{v:>22}  {src:<6}{note}")
    print("-" * 74)
    print("外挿の行は投影であって測定ではない。実測アンカーの行だけが測定である。")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-n", type=int, default=8, help="検証する上限 n（既定 8、10 で約 30 秒）")
    ap.add_argument("--sheet", action="store_true", help="実寸表を出力する")
    a = ap.parse_args()

    ok, samples = run_checks(a.max_n)
    print("-" * 74)
    print("全一致（ZERO DEFECTS）" if ok else "不一致あり — 参照実装かエンジンのどちらかが壊れている")
    if a.sheet:
        sheet(samples)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
