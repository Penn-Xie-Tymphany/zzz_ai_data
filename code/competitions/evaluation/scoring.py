"""DataAgent-Bench 本地评分器（Phase 1 官方口径复现）。

依据官网（https://dataagent.top/ "Scoring & Evaluation"）与社区对官方规则 6.2/6.3 的
复现实现整理，用于把本地跑出的 prediction.csv 与 demo 的 gold.csv 对比，得到与
排行榜同口径的分数。

评分规则（官方口径）：
    Score = max(0, Recall − λ · (Extra Columns / Predicted Columns))
    - 列匹配：按「列内容签名」匹配——列内每个值先归一化，再统计成多重集 Counter，
      签名 = tuple(sorted(Counter.items()))；签名完全一致的列才认为匹配；
    - 忽略列名、忽略行序、忽略列序；
    - Recall  = matched / gold_columns
    - Extra   = predicted_columns − matched（一对一匹配下即未命中的预测列数）
    - λ：官方规则仅公开符号 λ，未公开数值。社区基线复现（BrightLiao 复盘、本仓库
      早期文档）均采用 0.5；某冠军内部自测脚本采用 0.1。本实现默认 0.5，
      可用 --lam 调整对齐。

值归一化优先级（normalize_value）：
    None / NaN → ""
    float       → 四舍五入保留 2 位小数 → 去尾零 → 去尾部小数点（空则回退 "0"）
    bool        → True→"1", False→"0"（必须在 int 之前判断）
    int         → str(int)
    字符串空/小写为 nan|none|null|n/a → ""
    字符串可解析为数字：无小数点且无指数 → 整数字面量；否则走 float 的 2 位小数规则
    字符串是日期 YYYY[-/.]M[-/.]D（可带 T/空格时间后缀）→ ISO YYYY-MM-DD
    其余文本 → strip + 折叠连续空白（" ".join(s.split())）

用法：
    py scoring.py --predict-root <runs/<run_id>> --gold-root <data/public/output>
                  [--input-root <data/public/input>] [--lam 0.5] [--out report.json]
    py scoring.py --pred <task_XX/prediction.csv> --gold <task_XX/gold.csv>  # 单题
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

# 评分罚分系数默认值（社区复现官方 demo 基线口径；见模块 docstring）
DEFAULT_LAMBDA = 0.5

_ISO_DATE_RE = re.compile(
    r"^\s*(?P<y>\d{4})[-/.]"
    r"(?P<m>\d{1,2})[-/.]"
    r"(?P<d>\d{1,2})"
    r"(?P<rest>[T ].*)?\s*$"
)
_NULLISH = {"", "nan", "none", "null", "n/a"}


def _fmt_float(x: float) -> str:
    """浮点归一：四舍五入 2 位 → 强制 2 位小数 → 去尾零 → 去尾部小数点。"""
    return f"{round(x, 2):.2f}".rstrip("0").rstrip(".") or "0"


def normalize_value(v: Any) -> str:
    """单值归一化，返回规范化字符串（对齐社区官方复现实现）。"""
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return ""
        return _fmt_float(v)
    if isinstance(v, bool):  # 必须在 int 之前：bool 是 int 子类
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if not isinstance(v, str):
        v = str(v)
    s = v.strip()
    if s.lower() in _NULLISH:
        return ""
    # 数字字符串
    try:
        x = float(s)
    except ValueError:
        pass
    else:
        if "." not in s and "e" not in s.lower():
            return str(int(x))
        return _fmt_float(x)
    # 日期（数字解析失败后才判断）
    m = _ISO_DATE_RE.match(s)
    if m:
        return f"{int(m.group('y')):04d}-{int(m.group('m')):02d}-{int(m.group('d')):02d}"
    return " ".join(s.split())


def column_signature(values: Iterable[Any]) -> tuple:
    """列签名：该列全部归一化值的多重集，排序后的 (值, 次数) 元组。"""
    return tuple(sorted(Counter(normalize_value(v) for v in values).items()))


# ---------------------------------------------------------------------------
# CSV 读取
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """读取 CSV：返回 (表头, 数据行)。列宽统一到最大列数，缺列补 ""。"""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    if not rows:
        return [], []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = [c.strip() for c in rows[0]]
    return header, rows[1:]


# ---------------------------------------------------------------------------
# 单任务评分
# ---------------------------------------------------------------------------

def score_task(
    pred_header: list[str] | None,
    pred_rows: list[list[str]] | None,
    gold_header: list[str] | None,
    gold_rows: list[list[str]] | None,
    lam: float = DEFAULT_LAMBDA,
) -> dict:
    """对单个任务的预测表与 gold 表评分。

    返回 dict：matched / gold_columns / predicted_columns / recall / extra /
    score（0 下限）。pred/gold 任一为空表（无可比数据）时按 note 记 0 分。
    """
    note = ""
    if pred_header is None:
        note = "no prediction.csv"
    elif gold_header is None:
        note = "no gold.csv"
    elif not gold_header or not any(gold_header):
        note = "empty gold header"
    elif len(gold_rows) == 0:
        note = "empty gold rows"

    if note:
        return {
            "note": note, "matched": 0, "gold_columns": 0, "predicted_columns": 0,
            "recall": 0.0, "extra": 0, "score": 0.0,
        }

    # 空表头但 gold 有数据的情况上面已挡；gold 列数按数据行宽度计算
    gold_cols = len(gold_header)
    pred_cols = len(pred_header) if pred_header else 0

    # 列签名按列（数据行，不含表头）
    gold_sigs = Counter(column_signature([row[c] for row in gold_rows]) for c in range(gold_cols))
    matched = 0
    if pred_rows:
        for c in range(pred_cols):
            sig = column_signature([row[c] for row in pred_rows])
            if gold_sigs[sig] > 0:
                gold_sigs[sig] -= 1
                matched += 1
    extra = pred_cols - matched
    recall = matched / gold_cols if gold_cols else 0.0
    extra_ratio = (extra / pred_cols) if pred_cols else 0.0
    score = max(0.0, recall - lam * extra_ratio)
    return {
        "note": note or "", "matched": matched, "gold_columns": gold_cols,
        "predicted_columns": pred_cols, "recall": round(recall, 6),
        "extra": max(extra, 0), "score": round(score, 6),
    }


def _load_table(path: Path | None) -> tuple[list[str] | None, list[list[str]] | None]:
    if path is None or not path.exists():
        return None, None
    header, rows = _read_csv(path)
    return header, rows


# ---------------------------------------------------------------------------
# 批量与聚合
# ---------------------------------------------------------------------------

def _round(x: float, n: int = 6) -> float:
    return round(float(x), n)


def aggregate(tasks: list[dict]) -> dict:
    """按难度聚合：mean（全部任务含 0 分）、submitted mean、perfect/零分统计。"""
    by_diff: dict[str, list[dict]] = {}
    for t in tasks:
        by_diff.setdefault(t.get("difficulty", "?"), []).append(t)

    def _stats(items: list[dict]) -> dict:
        scores = [t["score"] for t in items]
        perfect = sum(1 for t in items if t["score"] >= 0.999)
        zero = sum(1 for t in items if t["score"] <= 0.0 and t.get("note"))
        return {
            "count": len(items),
            "mean": _round(sum(scores) / len(scores)) if items else 0.0,
            "perfect": perfect,
            "zero": zero,
        }

    return {
        "total": len(tasks),
        "submitted": sum(1 for t in tasks if t.get("note") != "no prediction.csv"),
        "overall": _stats(tasks),  # 含未提交任务（0 分）的整体平均
        "submitted_mean": _round(
            sum(t["score"] for t in tasks if t.get("note") != "no prediction.csv")
            / max(1, sum(1 for t in tasks if t.get("note") != "no prediction.csv"))
        ),
        "by_difficulty": {k: _stats(v) for k, v in sorted(by_diff.items())},
    }


def score_batch(
    predict_root: Path,
    gold_root: Path,
    input_root: Path | None = None,
    lam: float = DEFAULT_LAMBDA,
) -> list[dict]:
    """扫描 predict_root 下全部 task_*/prediction.csv，与 gold_root 下同名 gold.csv 对比。"""
    gold_dirs = sorted(
        d for d in gold_root.glob("task_*") if (d / "gold.csv").exists()
    )
    if not gold_dirs:
        raise FileNotFoundError(f"gold_root 下没有 task_*/gold.csv: {gold_root}")
    tasks = []
    for gd in gold_dirs:
        name = gd.name
        pred_p = predict_root / name / "prediction.csv"
        gold_p = gd / "gold.csv"
        ph, pr = _load_table(pred_p)
        gh, gr = _load_table(gold_p)
        row = score_task(ph, pr, gh, gr, lam=lam)
        row["task_id"] = name
        row["difficulty"] = _read_difficulty(gd, input_root)
        tasks.append(row)
    return tasks


def _read_difficulty(gold_dir: Path, input_root: Path | None) -> str:
    if input_root is None:
        return ""
    tj = input_root / gold_dir.name / "task.json"
    if not tj.exists():
        return ""
    try:
        return json.loads(tj.read_text(encoding="utf-8")).get("difficulty", "")
    except Exception:
        return ""


def _fmt_table(tasks: list[dict], agg: dict) -> str:
    lines = [
        f"{'task':<10}{'diff':<10}{'gold':>5}{'pred':>5}{'match':>6}"
        f"{'recall':>9}{'extra':>6}{'score':>9}  note",
        "-" * 78,
    ]
    for t in sorted(tasks, key=lambda x: x["task_id"]):
        lines.append(
            f"{t['task_id']:<10}{str(t.get('difficulty', '')):<10}"
            f"{t['gold_columns']:>5}{t['predicted_columns']:>5}{t['matched']:>6}"
            f"{t['recall']:>9.3f}{t['extra']:>6}{t['score']:>9.4f}  {t['note']}"
        )
    lines.append("-" * 78)
    lines.append(f"total={agg['total']} submitted={agg['submitted']} "
                 f"overall_mean={agg['overall']['mean']:.4f} "
                 f"submitted_mean={agg['submitted_mean']:.4f} "
                 f"perfect={agg['overall']['perfect']}")
    for d, s in agg["by_difficulty"].items():
        lines.append(f"  [{d or '?'}] n={s['count']} mean={s['mean']:.4f} "
                     f"perfect={s['perfect']} zero={s['zero']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DataAgent-Bench Phase 1 本地评分器")
    ap.add_argument("--predict-root", type=Path, help="预测产物根（含 task_*/prediction.csv）")
    ap.add_argument("--gold-root", type=Path, help="gold 根（含 task_*/gold.csv）")
    ap.add_argument("--input-root", type=Path, default=None, help="(可选) input 根，读 task.json 难度")
    ap.add_argument("--pred", type=Path, help="单题 prediction.csv")
    ap.add_argument("--gold", type=Path, help="单题 gold.csv")
    ap.add_argument("--lam", type=float, default=DEFAULT_LAMBDA, help="罚分系数，默认 0.5")
    ap.add_argument("--out", type=Path, default=None, help="(可选) 写 JSON 报告")
    args = ap.parse_args(argv)

    if args.pred or args.gold:
        if not (args.pred and args.gold):
            ap.error("--pred 与 --gold 需同时给出")
        ph, pr = _load_table(args.pred)
        gh, gr = _load_table(args.gold)
        row = score_task(ph, pr, gh, gr, lam=args.lam)
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    if not (args.predict_root and args.gold_root):
        ap.error("需要 --predict-root/--gold-root 或 --pred/--gold")
    tasks = score_batch(args.predict_root, args.gold_root, args.input_root, lam=args.lam)
    agg = aggregate(tasks)
    print(_fmt_table(tasks, agg))
    if args.out:
        payload = {"lambda": args.lam, "aggregate": agg, "tasks": tasks}
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"\n报告已写入: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
