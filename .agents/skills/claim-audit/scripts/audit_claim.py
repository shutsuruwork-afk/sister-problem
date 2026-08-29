#!/usr/bin/env python3
"""主張と計算の接続を検査する監査ゲート。

成果を台帳に記録する前に実行する。各ゲートは「その主張が、主張している計算に
接続されているか」を機械的に確かめる。人手の読みでは 453 件のうち 276 件の
定数演算を見逃したため、判定は自動化されている。

  python audit_claim.py --src math/src                    # 全件を静的検査
  python audit_claim.py exp_h175_*.py --run               # 1件を実行込みで検査
  python audit_claim.py --src math/src --json > audit.json

終了コード: 0 = 全ゲート通過 / 1 = 1件以上が不合格。
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import subprocess
import sys

# 「この計算は問題本体に触れているか」を判定する識別子。
# 別プロジェクトへ移すときは、ここだけ差し替える。
DEFAULT_MARKERS = r"KNOWN_A007764|run_bitboard_dp|solve_exact|frontier|state_engine|motzkin|rank_valid"

RATIO = re.compile(r"([0-9][0-9,]*\.?[0-9]*)\s*[x倍]", re.IGNORECASE)


def parse(path: str):
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        return src, ast.parse(src)
    except SyntaxError:
        return src, None


def g1_connection(src: str, markers: re.Pattern) -> tuple[bool, str]:
    """主張の対象である計算に、実際に触れているか。"""
    hits = sorted(set(markers.findall(src)))
    if hits:
        return True, f"参照: {', '.join(hits[:3])}"
    return False, "問題本体の識別子を1つも参照していない"


def _const_derived_names(tree) -> set[str]:
    """数値定数から辿れる名前を集める（デフォルト引数 → self 属性 → 中間変数）。

    H-475 は `50.0 / 0.005` を直接は書かず、デフォルト引数 → self 属性 →
    中間変数の順に流していた。定数どうしの除算だけを見ると通過してしまう。
    """
    names: set[str] = set()

    def target_name(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def is_const_expr(node) -> bool:
        if isinstance(node, ast.Constant):
            return isinstance(node.value, (int, float))
        if isinstance(node, (ast.Name, ast.Attribute)):
            return target_name(node) in names
        if isinstance(node, ast.BinOp):
            return is_const_expr(node.left) and is_const_expr(node.right)
        if isinstance(node, ast.UnaryOp):
            return is_const_expr(node.operand)
        return False

    # デフォルト引数に数値を持つ仮引数は定数由来
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = n.args.args[len(n.args.args) - len(n.args.defaults):]
            for arg, d in zip(args, n.args.defaults):
                if isinstance(d, ast.Constant) and isinstance(d.value, (int, float)):
                    names.add(arg.arg)

    # 代入を数回なめて伝播させる（順序に依存しないよう反復）
    for _ in range(4):
        before = len(names)
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                value = n.value
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if value is not None and is_const_expr(value):
                    for t in targets:
                        nm = target_name(t)
                        if nm:
                            names.add(nm)
        if len(names) == before:
            break
    return names


def g2_provenance(tree) -> tuple[bool, str]:
    """見出しの倍率が、測定ではなく定数から作られていないか。

    定数から辿れる値どうしの除算を不合格とする。測定値どうしの除算
    （実行時間 / 実行時間 など）は正当なので通す。
    """
    if tree is None:
        return False, "構文解析できない"
    const_names = _const_derived_names(tree)

    def const_side(node) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return repr(node.value)
        if isinstance(node, ast.Name) and node.id in const_names:
            return node.id
        if isinstance(node, ast.Attribute) and node.attr in const_names:
            return node.attr
        if isinstance(node, ast.BinOp):
            l, r = const_side(node.left), const_side(node.right)
            return f"{l}·{r}" if l and r else None
        return None

    manufactured = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            l, r = const_side(node.left), const_side(node.right)
            if l and r:
                manufactured.append(f"{l} / {r}")
    if manufactured:
        return False, f"定数由来の値どうしの除算で倍率を生成: {manufactured[:2]}"
    return True, "倍率は測定値から導出されている"


def g3_scale(src: str, production_n: int) -> tuple[bool, str]:
    """測定した規模が記録されているか。本番規模との差を必ず可視化する。"""
    ns: list[int] = []
    for m in re.finditer(r"for\s+\w+\s+in\s+range\(\s*(\d+)\s*,\s*(\d+)", src):
        ns.append(int(m.group(2)) - 1)
    for m in re.finditer(r"for\s+\w+\s+in\s+\[([0-9,\s]+)\]", src):
        vals = [int(x) for x in m.group(1).split(",") if x.strip().isdigit()]
        ns += [v for v in vals if v < 10_000]  # 素数定数などを除く
    if not ns:
        return False, "試験した n が読み取れない（規模を明記すること）"
    top = max(ns)
    if top >= production_n:
        return True, f"n={top} まで測定（本番 n={production_n} に到達）"
    return False, f"n={top} 止まり。本番 n={production_n} との差 {production_n - top} ステップを併記すること"


def g4_consistency(path: str, timeout: int) -> tuple[bool, str]:
    """出力表の倍率と、結論文の倍率が一致するか（--run 時のみ）。"""
    try:
        p = subprocess.run(
            [sys.executable, path], capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False, f"{timeout}s で終了しない"
    out = p.stdout
    if not out.strip():
        return False, "出力なし"
    lines = out.splitlines()
    concl = [l for l in lines if re.search(r"Conclusion|結論", l)]
    if not concl:
        return True, "結論文なし（照合対象なし）"
    idx = lines.index(concl[0])
    table = {r.replace(",", "") for l in lines[:idx] for r in RATIO.findall(l)}
    stated = {r.replace(",", "") for l in lines[idx:] for r in RATIO.findall(l)}
    orphan = {s for s in stated if s not in table}
    if orphan:
        return False, f"結論の倍率が表に無い: {sorted(orphan)[:3]}"
    return True, "表と結論が一致"


def g5_prior_refutation(src: str, pruned_text: str) -> tuple[bool, str]:
    """既に棄却済みの根本原因を再提出していないか。"""
    if not pruned_text:
        return True, "棄却アーカイブ未指定（照合スキップ）"
    doc = src.lower()
    hits = []
    for line in pruned_text.splitlines():
        m = re.search(r"[（(]([^）)]+)[）)]\s*$", line.strip())
        if not m:
            continue
        for kw in re.findall(r"[ぁ-んァ-ヶ一-龠A-Za-z]{4,}", m.group(1)):
            if kw.lower() in doc:
                hits.append(f"{kw} ← {line.strip()[:44]}")
                break
    if hits:
        return False, f"棄却済みの原因と一致: {hits[0]}"
    return True, "棄却アーカイブと衝突なし"


GATES = ["G1 接続", "G2 由来", "G3 規模", "G4 整合", "G5 既知の否定"]


def audit(path, markers, production_n, pruned_text, run, timeout):
    src, tree = parse(path)
    res = {
        "file": os.path.basename(path),
        "G1 接続": g1_connection(src, markers),
        "G2 由来": g2_provenance(tree),
        "G3 規模": g3_scale(src, production_n),
        "G4 整合": g4_consistency(path, timeout) if run else (None, "未実行（--run で有効）"),
        "G5 既知の否定": g5_prior_refutation(src, pruned_text),
    }
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="検査するファイル")
    ap.add_argument("--src", help="ディレクトリを一括検査（exp_h*.py）")
    ap.add_argument("--markers", default=DEFAULT_MARKERS, help="問題本体を示す識別子の正規表現")
    ap.add_argument("--production-n", type=int, default=28, help="本番規模の n")
    ap.add_argument("--pruned", help="棄却アーカイブの md ファイル（G5 用）")
    ap.add_argument("--run", action="store_true", help="実行して G4 を検査")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="不合格のみ表示")
    a = ap.parse_args()

    targets = list(a.files)
    if a.src:
        targets += sorted(glob.glob(os.path.join(a.src, "exp_h*.py")))
    if not targets:
        ap.error("検査対象がない（--src かファイル名を指定）")

    markers = re.compile(a.markers)
    pruned_text = open(a.pruned, encoding="utf-8").read() if a.pruned else ""

    results = [audit(p, markers, a.production_n, pruned_text, a.run, a.timeout) for p in targets]

    if a.json:
        print(json.dumps(results, ensure_ascii=False, default=str, indent=2))
    else:
        tally = {g: [0, 0, 0] for g in GATES}  # pass, fail, skip
        for r in results:
            bad = [g for g in GATES if r[g][0] is False]
            for g in GATES:
                ok = r[g][0]
                tally[g][0 if ok else (2 if ok is None else 1)] += 1
            if bad and not a.quiet or bad:
                print(f"\n■ {r['file']}")
                for g in GATES:
                    ok, why = r[g]
                    mark = "OK  " if ok else ("--  " if ok is None else "NG  ")
                    print(f"   {mark}{g}: {why}")
        print("\n" + "=" * 72)
        print(f"{'ゲート':<16}{'合格':>6}{'不合格':>8}{'未実行':>8}")
        print("-" * 72)
        for g in GATES:
            p, f, s = tally[g]
            print(f"{g:<16}{p:>6}{f:>8}{s:>8}")
        failed = sum(1 for r in results if any(r[g][0] is False for g in GATES))
        print("-" * 72)
        print(f"検査 {len(results)} 件中、{failed} 件が1つ以上のゲートで不合格")

    return 1 if any(r[g][0] is False for r in results for g in GATES) else 0


if __name__ == "__main__":
    sys.exit(main())
