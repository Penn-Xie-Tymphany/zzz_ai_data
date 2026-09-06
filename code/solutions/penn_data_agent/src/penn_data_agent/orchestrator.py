"""Plan-and-Execute 主编排（Orchestrator）。

控制流（对应自研文档中的四阶段）：

    Recon（代码，零 LLM） → Planner（一次调用产出契约+子任务）
      → SubAgent 逐个执行（独立上下文，结构化回传）
      → Composer（按契约拼表） → Verifier（fail-closed 门禁）
      → 不通过则 Replan（预算内）→ 仍不通过则按契约裁剪后提交

设计原则：**不信任模型自律**。计划有规则校验、答案有门禁校验、
每一步的失败都有明确的降级路径，而不是"交给下一轮 thought 自己纠正"。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import AgentConfig, ContextConfig
from .composer import Composer
from .llm import LLMClient
from .planner import Plan, Planner
from .recon import build_env_card, render_env_card
from .schema import AnswerTable, PublicTask
from .verifier import Verifier
from .worker import SubAgent, WorkerResult


@dataclass(slots=True)
class AgentOutcome:
    answer: AnswerTable | None
    plan: Plan | None = None
    trace: dict[str, Any] = field(default_factory=dict)
    failure_reason: str = ""

    @property
    def submitted(self) -> bool:
        return self.answer is not None and bool(self.answer.columns)


class PlanExecuteAgent:
    def __init__(self, llm: LLMClient, cfg: AgentConfig | None = None):
        self.llm = llm
        self.cfg = cfg or AgentConfig()
        self.planner = Planner(llm, self.cfg.budget)
        self.worker = SubAgent(llm, budget=self.cfg.budget, context_cfg=self.cfg.context)
        self.composer = Composer(llm, self.cfg.budget)
        self.verifier = Verifier(llm, self.cfg.budget)

    # ---------------------------------------------------------------- 主入口
    def run(self, task: PublicTask) -> AgentOutcome:
        trace: dict[str, Any] = {
            "task_id": task.task_id,
            "difficulty": task.difficulty,
            "question": task.question,
            "model": self.llm.model,
            "stages": [],
        }

        # ① Recon：确定性扫描，零 LLM 成本
        env_card = build_env_card(task, self.cfg.context)
        env_text = render_env_card(env_card)
        trace["env_card_chars"] = len(env_text)
        trace["stages"].append("recon")

        # ② 规划（含规则校验，必要时带反馈重规划）
        plan, issues, plan_attempts = self._plan_with_feedback(task, env_text, trace)
        trace["plan"] = plan.render() if plan else ""
        trace["plan_issues"] = issues
        trace["plan_attempts"] = plan_attempts
        if plan is None:
            return AgentOutcome(
                answer=None, trace=trace, failure_reason=f"规划失败: {issues[:2]}"
            )

        # ③~⑤ 执行 → 组装 → 校验（带 replan 预算）
        replans_left = self.cfg.budget.replan_budget
        feedback = ""
        results: list[WorkerResult] = []
        outcome = AgentOutcome(answer=None, plan=plan, trace=trace)
        step_budget = self.cfg.budget.worker_total_steps

        for attempt in range(replans_left + 1):
            results = self._execute_plan(task, plan, env_text, trace, step_budget)
            trace.setdefault("attempts", []).append(
                {"attempt": attempt + 1, "step_budget": step_budget,
                 "workers": [{"id": r.task_id, "status": r.status, "steps": r.steps} for r in results]}
            )

            composed = self.composer.run(task, plan.contract, results)
            trace["compose_notes"] = composed.notes
            if composed.answer is None:
                outcome.failure_reason = f"组装答案失败: {composed.notes}"
                step_budget = max(4, step_budget // 2)
                if attempt < replans_left:
                    plan, issues, _ = self._plan_with_feedback(
                        task, env_text, trace, feedback="上一次未能组装出答案，请简化子任务并明确每列从哪来。"
                    )
                    if plan is None:
                        break
                    continue
                break

            verified = self.verifier.run(task, plan.contract, composed.answer, results)
            trace["verify"] = {
                "passed": verified.passed,
                "issues": verified.issues,
                "suggestion": verified.suggestion,
            }
            final_answer = verified.fixed_answer or composed.answer
            outcome.answer = final_answer
            outcome.plan = plan
            if verified.passed or verified.suggestion == "submit":
                outcome.failure_reason = "" if verified.passed else "verifier 未通过但已按建议提交"
                return outcome

            # 不通过：看预算决定 replan / 直接提交
            if attempt < replans_left and verified.suggestion in ("replan", "retry"):
                feedback = "\n".join(
                    [
                        "上一次执行未通过校验，问题如下：",
                        verified.issue_text() or "（无具体说明）",
                        "请重新规划：修正答案契约（尤其列的定义与粒度）与子任务。",
                    ]
                )
                plan, issues, _ = self._plan_with_feedback(task, env_text, trace, feedback=feedback)
                step_budget = max(6, step_budget // 2)
                if plan is None:
                    break
                continue

            outcome.failure_reason = "verifier 未通过，已按当前最佳结果提交（fail-closed）"
            return outcome

        if outcome.answer is None:
            outcome.failure_reason = outcome.failure_reason or "未能产出答案"
        return outcome

    # ---------------------------------------------------------------- 内部
    def _plan_with_feedback(
        self,
        task: PublicTask,
        env_text: str,
        trace: dict[str, Any],
        feedback: str = "",
    ) -> tuple[Plan | None, list[str], int]:
        """规划 + 规则校验；不合规时把问题回灌给 Planner 重来一次。"""
        attempts = 0
        plan: Plan | None = None
        issues: list[str] = []
        for _ in range(2):
            attempts += 1
            plan, issues = self.planner.run(task, env_text, feedback=feedback)
            if not issues:
                return plan, issues, attempts
            feedback = "计划未通过规则校验：" + "；".join(issues)
        trace.setdefault("plan_rejects", []).append(issues)
        return plan, issues, attempts

    def _execute_plan(
        self,
        task: PublicTask,
        plan: Plan,
        env_text: str,
        trace: dict[str, Any],
        step_budget: int,
    ) -> list[WorkerResult]:
        """按拓扑序执行子任务，每个子任务一个独立上下文。"""
        remaining = step_budget
        summaries: dict[str, str] = {}
        results: list[WorkerResult] = []
        worker_traces: list[dict] = trace.setdefault("workers", [])

        for subtask in plan.topo_order():
            if remaining <= 0:
                skipped = WorkerResult(
                    task_id=subtask.id, status="failed",
                    notes="全局步数预算耗尽，该子任务未执行", steps=0,
                )
                results.append(skipped)
                summaries[subtask.id] = skipped.render_summary()
                continue
            dep_summaries = [summaries[d] for d in subtask.depends_on if d in summaries]
            result, sub_trace = self.worker.run(
                task,
                subtask,
                plan.contract,
                env_text,
                dep_summaries=dep_summaries,
                step_budget=min(int(subtask.max_steps), remaining),
            )
            remaining -= max(1, result.steps)
            results.append(result)
            summaries[subtask.id] = result.render_summary()
            worker_traces.append(
                {"id": subtask.id, "status": result.status, "steps": result.steps, "trace": sub_trace}
            )
            trace["stages"].append(f"worker:{subtask.id}:{result.status}")
        return results
