"""批量跑分：跑一批题 → 落盘产物 → 调官方同口径评分器出分。

用法：
    py scripts/run_benchmark.py --limit 5                 # 先小批量验证链路
    py scripts/run_benchmark.py                           # 全量 50 题
    py scripts/run_benchmark.py --difficulty hard --workers 4
    py scripts/run_benchmark.py --mode react --limit 10   # ReAct 对照基线
    py scripts/run_benchmark.py --task task_11 --task task_330
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass

from penn_data_agent.config import config_from_yaml, default_config  # noqa: E402
from penn_data_agent.runner import (  # noqa: E402
    BenchmarkRunner,
    format_report,
    list_tasks,
    make_run_id,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = (
    ROOT / "competitions" / "kddcup2026-data-agents-starter-kit" / "PHASE_1" / "data" / "public"
)
DEFAULT_CONFIG = (
    ROOT / "competitions" / "kddcup2026-data-agents-starter-kit" / "PHASE_1" / "configs" / "qwen36_flash.yaml"
)
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "artifacts" / "runs"


def main() -> int:
    parser = argparse.ArgumentParser(description="批量跑分 penn_data_agent")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--input-root", default=str(DEFAULT_DATA / "input"))
    parser.add_argument("--output-root", default=str(DEFAULT_DATA / "output"))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--mode", choices=["plan-execute", "react"], default="plan-execute")
    parser.add_argument("--difficulty", default="", help="easy/medium/hard/extreme")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--task", action="append", default=[], help="指定 task_id，可重复")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=16, help="react 模式步数上限")
    parser.add_argument("--react-env-card", action="store_true")
    parser.add_argument("--no-score", action="store_true", help="跑完不自动评分")
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    cfg = config_from_yaml(Path(args.config)) if Path(args.config).exists() else default_config()
    input_root = Path(args.input_root)
    task_ids = list_tasks(
        input_root, difficulty=args.difficulty, limit=args.limit, only=args.task or None
    )
    if not task_ids:
        print("没有匹配的任务，检查 --input-root / --difficulty")
        return 1

    print(f"模式={args.mode} 模型={cfg.llm.model} 任务数={len(task_ids)} 并发={args.workers}")
    runner = BenchmarkRunner(
        input_root,
        Path(args.output_root),
        cfg,
        mode=args.mode,
        react_max_steps=args.max_steps,
        react_with_env_card=args.react_env_card,
    )

    outcomes = runner.run(task_ids, workers=args.workers)
    run_id = args.run_id or make_run_id()
    run_dir = Path(args.out_dir) / run_id
    runner.write_outputs(run_dir, outcomes)

    submitted = sum(1 for o in outcomes if o.submitted)
    print(f"\n提交 {submitted}/{len(outcomes)}，产物: {run_dir}")
    for outcome in outcomes:
        if not outcome.submitted:
            print(f"  [未提交] {outcome.task_id}: {outcome.failure_reason}")

    if not args.no_score:
        report = runner.score(run_dir, task_ids=task_ids)
        print("\n=== 评分（官方同口径，λ=0.5）===")
        print(format_report(report))
        print(f"明细: {run_dir / 'evaluation_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
