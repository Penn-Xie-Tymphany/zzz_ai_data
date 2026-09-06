"""批量跑分：串/并执行任务、落盘产物、调用官方同口径评分器出分。

产物结构（与官方 run 目录保持一致，便于复用既有复盘习惯）：

    <output_dir>/<run_id>/
    ├── task_XX/prediction.csv     # 提交物
    ├── task_XX/trace.json         # 全阶段轨迹（排错核心证据）
    ├── summary.json               # 每题耗时/是否提交/失败原因
    └── evaluation_report.json     # 官方同口径评分明细
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent import ReActAgent
from .config import AgentConfig, LLMConfig
from .dataset import iter_task_ids, load_task, write_prediction
from .llm import LLMClient
from .orchestrator import PlanExecuteAgent
from .recon import build_env_card, render_env_card

# code/competitions/evaluation（官方同口径本地评分器）
EVAL_DIR = Path(__file__).resolve().parents[4] / "competitions" / "evaluation"


def load_scoring():
    if str(EVAL_DIR) not in sys.path:
        sys.path.insert(0, str(EVAL_DIR))
    import scoring  # type: ignore

    return scoring


@dataclass(slots=True)
class TaskOutcome:
    task_id: str
    difficulty: str
    submitted: bool
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    failure_reason: str = ""
    trace: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    def __init__(
        self,
        input_root: Path,
        output_root: Path,
        cfg: AgentConfig,
        mode: str = "plan-execute",
        react_max_steps: int = 16,
        react_with_env_card: bool = False,
    ):
        self.input_root = Path(input_root)
        self.output_root = Path(output_root)
        self.cfg = cfg
        self.mode = mode
        self.react_max_steps = react_max_steps
        self.react_with_env_card = react_with_env_card

    def _new_llm(self) -> LLMClient:
        return LLMClient(self.cfg.llm)

    # ------------------------------------------------------------ 单题
    def run_one(self, task_id: str) -> TaskOutcome:
        timeout = self.cfg.run.task_timeout_seconds or 0

        def _inner() -> TaskOutcome:
            started = time.time()
            task = load_task(self.input_root, task_id)
            llm = self._new_llm()
            try:
                if self.mode == "react":
                    agent = ReActAgent(llm, self.cfg, with_env_card=self.react_with_env_card)
                    env_text = render_env_card(build_env_card(task, self.cfg.context)) \
                        if self.react_with_env_card else ""
                    outcome = agent.run(task, env_text, max_steps=self.react_max_steps)
                    answer = outcome.answer
                    trace: dict[str, Any] = {"mode": "react", "steps": outcome.steps, "trace": outcome.trace}
                    failure = outcome.failure_reason
                else:
                    agent = PlanExecuteAgent(llm, self.cfg)
                    result = agent.run(task)
                    answer = result.answer
                    trace = dict(result.trace)
                    trace["mode"] = "plan-execute"
                    failure = result.failure_reason
                trace["usage"] = {
                    "calls": llm.usage.calls,
                    "prompt_tokens": llm.usage.prompt_tokens,
                    "completion_tokens": llm.usage.completion_tokens,
                }
            except Exception as exc:  # noqa: BLE001 - 单题异常不能拖垮整轮跑分
                return TaskOutcome(
                    task_id=task_id,
                    difficulty=task.difficulty,
                    submitted=False,
                    elapsed_seconds=time.time() - started,
                    failure_reason=f"{type(exc).__name__}: {exc}",
                    trace={"error": str(exc)},
                )

            return TaskOutcome(
                task_id=task_id,
                difficulty=task.difficulty,
                submitted=answer is not None and bool(answer.columns),
                columns=list(answer.columns) if answer else [],
                rows=[list(r) for r in answer.rows] if answer else [],
                elapsed_seconds=round(time.time() - started, 2),
                failure_reason=failure,
                trace=trace,
            )

        # 单题受控超时：超时即判未提交，绝不拖垮整轮跑分（底层线程继续跑但主流程不被阻塞）。
        if timeout and timeout > 0:
            pool = ThreadPoolExecutor(max_workers=1)
            fut = pool.submit(_inner)
            try:
                return fut.result(timeout=timeout)
            except FuturesTimeoutError:
                pool.shutdown(wait=False)
                return TaskOutcome(
                    task_id=task_id,
                    difficulty="",
                    submitted=False,
                    elapsed_seconds=timeout,
                    failure_reason=f"task_timeout({timeout}s)",
                    trace={"error": "task_timeout", "timeout_seconds": timeout},
                )
        return _inner()

    # ------------------------------------------------------------ 批量
    def run(self, task_ids: list[str], workers: int = 1) -> list[TaskOutcome]:
        total = len(task_ids)

        def _progress(done: int, task_id: str, ok: bool) -> None:
            print(f"[{done}/{total}] {task_id} {'OK' if ok else 'FAIL'}", flush=True)

        if workers <= 1:
            out: list[TaskOutcome] = []
            for i, t in enumerate(task_ids, 1):
                r = self.run_one(t)
                _progress(i, t, r.submitted)
                out.append(r)
            return out
        results: list[TaskOutcome] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.run_one, t): t for t in task_ids}
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    r = future.result()
                    results.append(r)
                    _progress(len(results), task_id, r.submitted)
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        TaskOutcome(task_id=task_id, difficulty="", submitted=False,
                                    failure_reason=f"{type(exc).__name__}: {exc}")
                    )
                    _progress(len(results), task_id, False)
        results.sort(key=lambda r: int(r.task_id.split("_")[-1]) if r.task_id.split("_")[-1].isdigit() else 0)
        return results

    # ------------------------------------------------------------ 落盘与评分
    def write_outputs(self, run_dir: Path, outcomes: list[TaskOutcome]) -> Path:
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": run_dir.name,
            "mode": self.mode,
            "model": self.cfg.llm.model,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tasks": [],
        }
        for outcome in outcomes:
            task_dir = run_dir / outcome.task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            if outcome.submitted:
                write_prediction(task_dir, outcome.columns, outcome.rows)
            (task_dir / "trace.json").write_text(
                json.dumps(outcome.trace, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )
            summary["tasks"].append(
                {
                    "task_id": outcome.task_id,
                    "difficulty": outcome.difficulty,
                    "submitted": outcome.submitted,
                    "elapsed_seconds": outcome.elapsed_seconds,
                    "failure_reason": outcome.failure_reason,
                }
            )
        summary["submitted"] = sum(1 for o in outcomes if o.submitted)
        summary["total"] = len(outcomes)
        (run_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return run_dir

    def score(self, run_dir: Path, out_name: str = "evaluation_report.json",
              task_ids: list[str] | None = None) -> dict:
        """评分；传 task_ids 时只按本次跑过的题聚合（子集跑分时 overall 才有意义）。"""
        scoring = load_scoring()
        tasks = scoring.score_batch(run_dir, self.output_root, self.input_root)
        scored = [t for t in tasks if t["task_id"] in set(task_ids)] if task_ids else tasks
        aggregate = scoring.aggregate(scored)
        payload = {
            "lambda": scoring.DEFAULT_LAMBDA,
            "basis": "subset" if task_ids else "full",
            "scored_count": len(scored),
            "aggregate": aggregate,
            "tasks": tasks,
        }
        (run_dir / out_name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return payload


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def list_tasks(input_root: Path, difficulty: str = "", limit: int = 0,
               only: list[str] | None = None) -> list[str]:
    if only:
        return list(only)
    ids = iter_task_ids(input_root, difficulty=difficulty)
    return ids[:limit] if limit and limit > 0 else ids


def format_report(report: dict) -> str:
    agg = report.get("aggregate", {})
    basis = "（仅本次跑过的题）" if report.get("basis") == "subset" else "（全量 50 题）"
    lines = [
        f"统计口径{basis}: "
        f"total={agg.get('total')} submitted={agg.get('submitted')} "
        f"overall={agg.get('overall', {}).get('mean')} "
        f"submitted_mean={agg.get('submitted_mean')} "
        f"perfect={agg.get('overall', {}).get('perfect')}"
    ]
    for diff, stat in (agg.get("by_difficulty") or {}).items():
        lines.append(
            f"  [{diff or '?'}] n={stat['count']} mean={stat['mean']} "
            f"perfect={stat['perfect']} zero={stat['zero']}"
        )
    return "\n".join(lines)
