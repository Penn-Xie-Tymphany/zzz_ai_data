"""跑单题：Plan-and-Execute 或 ReAct 对照。

用法：
    py scripts/run_task.py task_11
    py scripts/run_task.py task_11 --mode react --max-steps 16
    py scripts/run_task.py task_11 --score          # 顺便与 gold 对照出分
    py scripts/run_task.py task_11 --print-trace    # 打印全阶段轨迹
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
from penn_data_agent.dataset import load_gold  # noqa: E402
from penn_data_agent.runner import BenchmarkRunner, load_scoring  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = (
    ROOT / "competitions" / "kddcup2026-data-agents-starter-kit" / "PHASE_1" / "data" / "public"
)
DEFAULT_CONFIG = (
    ROOT / "competitions" / "kddcup2026-data-agents-starter-kit" / "PHASE_1" / "configs" / "qwen36_flash.yaml"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="单题运行 penn_data_agent")
    parser.add_argument("task_id")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="yaml 配置（含 model/api_key）")
    parser.add_argument("--input-root", default=str(DEFAULT_DATA / "input"))
    parser.add_argument("--output-root", default=str(DEFAULT_DATA / "output"))
    parser.add_argument("--mode", choices=["plan-execute", "react"], default="plan-execute")
    parser.add_argument("--max-steps", type=int, default=16, help="react 模式的步数上限")
    parser.add_argument("--react-env-card", action="store_true", help="react 模式也喂环境卡片（强基线）")
    parser.add_argument("--score", action="store_true", help="与 gold 对照出分")
    parser.add_argument("--print-trace", action="store_true")
    parser.add_argument("--out-dir", default="", help="(可选) 产物目录，默认不落盘")
    args = parser.parse_args()

    cfg = config_from_yaml(Path(args.config)) if Path(args.config).exists() else default_config()
    runner = BenchmarkRunner(
        Path(args.input_root),
        Path(args.output_root),
        cfg,
        mode=args.mode,
        react_max_steps=args.max_steps,
        react_with_env_card=args.react_env_card,
    )

    outcome = runner.run_one(args.task_id)
    print(f"task={outcome.task_id} 难度={outcome.difficulty} 耗时={outcome.elapsed_seconds}s")
    print(f"提交={'是' if outcome.submitted else '否'}  失败原因={outcome.failure_reason or '-'}")
    if outcome.submitted:
        print("答案表:")
        print("  " + ", ".join(outcome.columns))
        for row in outcome.rows[:20]:
            print("  " + ", ".join(str(v) for v in row))

    if args.score and outcome.submitted:
        gold = load_gold(Path(args.output_root), args.task_id)
        if gold is None:
            print("未找到 gold.csv，跳过评分")
        else:
            scoring = load_scoring()
            result = scoring.score_task(outcome.columns, outcome.rows, gold[0], gold[1])
            print("评分: " + json.dumps(result, ensure_ascii=False))

    if args.print_trace:
        print("\n--- trace ---")
        print(json.dumps(outcome.trace, ensure_ascii=False, indent=2, default=str))

    if args.out_dir:
        run_dir = Path(args.out_dir)
        runner.write_outputs(run_dir, [outcome])
        print(f"\n产物已写入: {run_dir / args.task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
