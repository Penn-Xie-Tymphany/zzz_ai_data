"""跑分报告分析：列形状分布 / 按难度 / 失败归因。

用法：
    python scripts/analyze_run.py <run_dir>
    python scripts/analyze_run.py artifacts/runs/20260906T183758Z
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def score_of(t: dict) -> float:
    for key in ("score", "mean", "score_mean"):
        if key in t and t[key] is not None:
            return float(t[key])
    return 0.0


def cls_of(t: dict) -> str:
    gc = t.get("gold_columns", 0) or 0
    pc = t.get("predicted_columns", 0) or 0
    if pc == 0:
        return "no_pred(未提交)"
    if pc > gc:
        return "extra(多给列)"
    if pc < gc:
        return "missing(少给列)"
    return "match(列数一致)"


def main() -> int:
    run_dir = sys.argv[1] if len(sys.argv) > 1 else "artifacts/runs/20260906T183758Z"
    rep_path = Path(run_dir) / "evaluation_report.json"
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    tasks = rep["tasks"]

    print("=== 列形状分布 ===")
    c = Counter(cls_of(t) for t in tasks)
    for k, v in c.most_common():
        print(f"  {k}: {v}")

    print("\n=== 按难度 ===")
    for diff in ("easy", "medium", "hard", "extreme"):
        sub = [t for t in tasks if t.get("difficulty") == diff]
        if not sub:
            continue
        sc = [score_of(t) for t in sub]
        print(
            f"  [{diff}] n={len(sub)} mean={sum(sc)/len(sc):.3f} "
            f"perfect={sum(1 for s in sc if s >= 0.999)} "
            f"zero={sum(1 for s in sc if s <= 0)}"
        )

    print("\n=== 非满分题明细（按分数升序）===")
    for t in sorted(tasks, key=score_of):
        s = score_of(t)
        if s < 0.999:
            print(
                f"  {t['task_id']} [{t.get('difficulty')}] score={s:.3f} "
                f"gc={t.get('gold_columns')} pc={t.get('predicted_columns')} "
                f"recall={t.get('recall')} note={t.get('note','')}"
            )

    print("\n=== 总览 ===")
    agg = rep.get("aggregate", {})
    print(f"  basis={rep.get('basis')} scored_count={rep.get('scored_count')}")
    print(f"  overall={agg.get('overall')}")
    print(f"  submitted_mean={agg.get('submitted_mean')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
