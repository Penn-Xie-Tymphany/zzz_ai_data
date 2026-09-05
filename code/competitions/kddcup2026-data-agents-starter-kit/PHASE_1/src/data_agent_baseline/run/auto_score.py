"""把 benchmark 产物与主仓本地评分器自动衔接。

在 starter-kit 内 `uv run dabench run-benchmark` 跑完后，会自动把本次 run 目录
（artifacts/runs/<run_id>/）的 prediction.csv 与 demo gold.csv 按**官方同口径**对比
打分，结果写入该 run 目录的 evaluation_report.json，方便与排行榜做量化对比。
也可用 `uv run dabench evaluate --run-id <id> --config <yaml>` 对历史 run 复盘，
该命令不调用模型。

设计要点：
- 评分算法「唯一实现」位于主仓 code/competitions/evaluation/scoring.py，本模块运行时
  按目录链动态加载，避免两处维护同一份公式；
- 找不到该文件、或当前数据集没有 gold 时，自动跳过并给出提示，不影响 benchmark 主流程
  （例如以后挂 hidden 测试集只有 input 没有 output 时就是这种情况）。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def find_scoring_module_path() -> Path | None:
    """沿目录链向上查找主仓 code/competitions/evaluation/scoring.py。"""
    cursor = Path(__file__).resolve().parent
    while cursor.parent != cursor:
        candidate = cursor / "evaluation" / "scoring.py"
        if candidate.is_file():
            return candidate
        if cursor.name == "competitions":
            return None
        cursor = cursor.parent
    return None


def _load_scoring() -> Any | None:
    module_path = find_scoring_module_path()
    if module_path is None:
        return None
    spec = importlib.util.spec_from_file_location("_dabench_local_scoring", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001 评分只是附属能力，加载失败仅跳过
        return None
    return module


def resolve_gold_root(dataset_root: Path, gold_root: Path | None = None) -> Path | None:
    """确定 gold 根目录：显式指定优先，否则取 dataset_root 同级的 output/。"""
    candidate = gold_root if gold_root is not None else dataset_root.parent / "output"
    if candidate.is_dir() and any(candidate.glob("task_*/gold.csv")):
        return candidate
    return None


class ScoreOutcome:
    """一次本地评分的结果（轻量对象，不依赖 rich 等展示层）。"""

    def __init__(
        self,
        *,
        ok: bool,
        aggregate: dict[str, Any] | None = None,
        report_path: Path | None = None,
        lam: float = 0.5,
        reason: str = "",
    ) -> None:
        self.ok = ok
        self.aggregate = aggregate
        self.report_path = report_path
        self.lam = lam
        self.reason = reason


def score_run_dir(
    *,
    run_output_dir: Path,
    dataset_root: Path,
    gold_root: Path | None = None,
    lam: float | None = None,
) -> ScoreOutcome:
    """对 run 目录整批评分，并把逐题明细写入 evaluation_report.json。"""
    scoring = _load_scoring()
    if scoring is None:
        return ScoreOutcome(
            ok=False,
            reason="找不到主仓 code/competitions/evaluation/scoring.py，跳过自动本地评分",
        )
    effective_gold_root = resolve_gold_root(dataset_root, gold_root)
    if effective_gold_root is None:
        return ScoreOutcome(
            ok=False,
            reason="未发现含 task_*/gold.csv 的 gold 数据目录，跳过自动本地评分",
        )
    effective_lam = float(lam) if lam is not None else float(getattr(scoring, "DEFAULT_LAMBDA", 0.5))
    try:
        tasks = scoring.score_batch(
            predict_root=run_output_dir,
            gold_root=effective_gold_root,
            input_root=dataset_root,
            lam=effective_lam,
        )
        aggregate = scoring.aggregate(tasks)
    except Exception as exc:  # noqa: BLE001 保证不因评分问题影响主流程
        return ScoreOutcome(ok=False, reason=f"本地评分失败：{exc}")

    report_path = run_output_dir / "evaluation_report.json"
    payload = {"lambda": effective_lam, "aggregate": aggregate, "tasks": tasks}
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ScoreOutcome(ok=True, aggregate=aggregate, report_path=report_path, lam=effective_lam)


def summary_lines(aggregate: dict[str, Any] | None, lam: float) -> list[str]:
    """把聚合结果渲染成若干行纯文本（控制台摘要）。"""
    if not aggregate:
        return []
    overall = aggregate["overall"]
    lines = [
        f"lambda        : {lam:g}",
        f"tasks         : {aggregate['total']} gold tasks, submitted {aggregate['submitted']}",
        f"overall mean  : {overall['mean']:.4f}   (含未提交题按 0 分, 官方 demo 同口径)",
        f"submitted mean: {aggregate['submitted_mean']:.4f}   (仅已产出 prediction.csv)",
        f"perfect       : {overall['perfect']} / {aggregate['total']}",
    ]
    by_diff = aggregate.get("by_difficulty") or {}
    if by_diff:
        parts = ", ".join(
            f"{key}: mean={value['mean']:.3f} (n={value['count']})"
            for key, value in sorted(by_diff.items())
        )
        lines.append(f"by difficulty : {parts}")
    return lines
