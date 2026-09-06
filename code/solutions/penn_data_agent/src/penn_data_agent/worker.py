"""Worker（子 Agent）：**一个子任务一个独立上下文**的 ReAct 执行器。

信息隔离的实现：
- 子 agent 看不到主 agent 的 Planner 对话，也看不到其它子任务的探索过程；
- 它拿到的只有：原题、答案契约、**本**子任务描述、前置子任务交回的**结构化结果**、
  以及环境卡片（事实，不含推理）；
- 结束时只回传结构化 `WorkerResult`（findings / artifacts / evidence），不回传轨迹。
  这样主上下文不会被任一子任务的探索噪声撑爆（官方 17 步即 15K tokens 的根因）。

工具集：官方 8 个工具中去掉 `answer`（子 agent 无权直接提交答案），
换成 `finish`（结构化交回结果）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .config import BudgetConfig, ContextConfig
from .jsonio import SchemaError, parse_with_schema
from .llm import LLMClient
from .planner import AnswerContract, SubTask
from .prompting import load_prompt
from .schema import PublicTask
from .tools import create_default_tool_registry
from .tools.registry import ToolExecutionResult, ToolRegistry, ToolSpec

STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["thought", "action", "action_input"],
    "properties": {
        "thought": {"type": "str"},
        "action": {"type": "str", "min_len": 1},
        "action_input": {"type": "dict"},
    },
}

FINISH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["status", "findings"],
    "properties": {
        "status": {"type": "str", "enum": ["success", "partial", "failed"]},
        "findings": {"type": "list", "items": {"type": "str"}},
        "artifacts": {"type": "dict"},
        "evidence": {"type": "list", "items": {"type": "str"}},
        "notes": {"type": "str"},
    },
}


@dataclass(slots=True)
class WorkerResult:
    task_id: str
    status: str
    findings: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    notes: str = ""
    steps: int = 0

    def ok(self) -> bool:
        return self.status == "success"

    def render_summary(self, max_chars: int = 1500) -> str:
        payload = {
            "task_id": self.task_id,
            "status": self.status,
            "findings": self.findings,
            "artifacts": self.artifacts,
            "evidence": self.evidence[:5],
            "notes": self.notes,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=1)
        return text if len(text) <= max_chars else text[:max_chars] + " …(截断)"


def build_worker_registry() -> ToolRegistry:
    """官方工具集 - answer + finish。"""
    base = create_default_tool_registry()
    specs = {k: v for k, v in base.specs.items() if k != "answer"}
    handlers = {k: v for k, v in base.handlers.items() if k != "answer"}

    specs["finish"] = ToolSpec(
        name="finish",
        description=(
            "Finish this sub-task and report structured results. "
            'action_input = {"status": "success|partial|failed", '
            '"findings": ["..."], "artifacts": {...}, "evidence": ["..."], "notes": "..."}'
        ),
        input_schema={
            "status": "success",
            "findings": ["观察到的结论"],
            "artifacts": {"key": "结构化结果"},
            "evidence": ["来自哪次观察"],
            "notes": "",
        },
    )

    def _finish(_task: PublicTask, action_input: dict[str, Any]) -> ToolExecutionResult:
        return ToolExecutionResult(ok=True, content=dict(action_input), is_terminal=True)

    handlers["finish"] = _finish
    return ToolRegistry(specs=specs, handlers=handlers)


def render_tool_menu(registry: ToolRegistry) -> str:
    lines = []
    for name in sorted(registry.specs):
        spec = registry.specs[name]
        lines.append(f"- {name}: {spec.description}")
        lines.append(f"  input_schema: {json.dumps(spec.input_schema, ensure_ascii=False)}")
    return "\n".join(lines)


class SubAgent:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry | None = None,
        budget: BudgetConfig | None = None,
        context_cfg: ContextConfig | None = None,
    ):
        self.llm = llm
        self.registry = registry or build_worker_registry()
        self.budget = budget or BudgetConfig()
        self.context_cfg = context_cfg or ContextConfig()

    def _system(self) -> str:
        return load_prompt("worker.md").replace("{tool_menu}", render_tool_menu(self.registry))

    def _initial_message(
        self,
        task: PublicTask,
        subtask: SubTask,
        contract: AnswerContract,
        env_card_text: str,
        dep_summaries: list[str],
    ) -> str:
        parts = [
            f"# 原题\n{task.question}",
            "\n# 答案契约（最终答案的形状，你只需提供其中与你相关的部分）",
            contract.render(),
            f"\n# 你的子任务 [{subtask.id}]",
            f"目标: {subtask.goal}",
            f"验收: {subtask.acceptance}",
            f"可用数据: {', '.join(subtask.inputs) or '见环境卡片'}",
            f"建议工具: {', '.join(subtask.suggested_tools) or '自行选择'}",
            f"步数上限: {subtask.max_steps}",
        ]
        if dep_summaries:
            parts.append("\n# 前置子任务结果（其它子任务交回的结构化产出）")
            parts.extend(dep_summaries)
        parts.append(f"\n{env_card_text}")
        parts.append(
            "\n# 开始\n请输出第一步的 JSON（thought/action/action_input）。"
            "完成后用 action=finish 交回结果。"
        )
        return "\n".join(parts)

    def run(
        self,
        task: PublicTask,
        subtask: SubTask,
        contract: AnswerContract,
        env_card_text: str,
        dep_summaries: list[str] | None = None,
        step_budget: int | None = None,
    ) -> tuple[WorkerResult, list[dict]]:
        """执行一个子任务，返回 (结果, 轨迹)。"""
        budget_steps = step_budget if step_budget is not None else self.budget.worker_max_steps
        max_steps = max(1, min(int(subtask.max_steps or budget_steps), budget_steps))
        messages: list[dict] = [
            {"role": "user", "content": self._initial_message(
                task, subtask, contract, env_card_text, dep_summaries or [])}
        ]
        history: list[dict] = []  # 每一步的 (raw, observation) 供消息重建与轨迹落盘
        trace: list[dict] = []

        for step in range(1, max_steps + 1):
            raw = self.llm.complete(self._build_messages(messages, history), system=self._system())
            try:
                step_obj = parse_with_schema(raw, STEP_SCHEMA)
            except SchemaError as exc:
                # 解析失败不消耗工具步数，但计入该步重试（最多 2 次）
                retry_ok = False
                for _ in range(2):
                    messages = messages + [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": "格式错误：" + "；".join(exc.errors[:3])
                         + "。请重新只输出一个 JSON 对象。"},
                    ]
                    raw = self.llm.complete(messages, system=self._system())
                    try:
                        step_obj = parse_with_schema(raw, STEP_SCHEMA)
                        retry_ok = True
                        break
                    except SchemaError as exc2:
                        exc = exc2
                if not retry_ok:
                    history.append({"raw": raw, "observation": "格式错误，已跳过该步"})
                    trace.append({"step": step, "error": exc.errors[:3]})
                    continue

            action = str(step_obj.get("action", ""))
            action_input = step_obj.get("action_input") or {}
            if not isinstance(action_input, dict):
                action_input = {"value": action_input}

            if action == "finish":
                result = self._build_result(subtask, action_input, step, trace)
                history.append({"raw": raw, "observation": "finish 已接收"})
                trace.append({"step": step, "action": "finish", "status": result.status})
                return result, trace

            observation = self._execute(task, action, action_input)
            history.append({"raw": raw, "observation": observation})
            trace.append({
                "step": step,
                "thought": str(step_obj.get("thought", ""))[:400],
                "action": action,
                "action_input": _clip_json(action_input, 600),
                "observation": observation[:600],
            })

        # 步数耗尽：再给一次机会强制收口
        messages = self._build_messages(messages, history) + [
            {"role": "user", "content": "步数已用完，请立即用 action=finish 交回你已确认的结果（status=partial 或 failed）。"}
        ]
        raw = self.llm.complete(messages, system=self._system())
        try:
            step_obj = parse_with_schema(raw, STEP_SCHEMA)
            action_input = step_obj.get("action_input") or {}
            result = self._build_result(subtask, action_input, max_steps, trace)
        except SchemaError:
            result = WorkerResult(
                task_id=subtask.id,
                status="failed",
                findings=[],
                notes=f"步数耗尽且未能产出结构化结果（{max_steps} 步）",
                steps=max_steps,
            )
        trace.append({"step": max_steps, "action": "finish(forced)", "status": result.status})
        return result, trace

    # ------------------------------------------------------------------ 内部
    def _build_messages(self, base: list[dict], history: list[dict]) -> list[dict]:
        """重建消息：近期 observation 完整保留，早期折叠为一行（治线性膨胀）。"""
        keep = self.context_cfg.keep_recent_observations
        messages = list(base)
        total = len(history)
        for index, item in enumerate(history):
            messages.append({"role": "assistant", "content": item["raw"]})
            observation = item["observation"]
            if total - index > keep:
                observation = " ".join(observation.split())[:200] + " …(早期观察已折叠)"
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        return messages

    def _execute(self, task: PublicTask, action: str, action_input: dict) -> str:
        if action not in self.registry.handlers:
            return f"未知工具 '{action}'。可用工具: {sorted(self.registry.specs)}"
        try:
            result = self.registry.execute(task, action, action_input)
        except Exception as exc:  # noqa: BLE001 - 工具异常也要作为观察回灌
            return f"工具异常: {type(exc).__name__}: {exc}"
        payload = {"ok": result.ok, "content": result.content}
        text = json.dumps(payload, ensure_ascii=False, default=str)
        return _clip(text, self.context_cfg.observation_max_chars)

    def _build_result(
        self, subtask: SubTask, action_input: dict, steps: int, trace: list[dict]
    ) -> WorkerResult:
        try:
            from .jsonio import validate

            issues = validate(action_input, FINISH_SCHEMA)
        except Exception:  # noqa: BLE001
            issues = []
        status = str(action_input.get("status", "partial"))
        if status not in ("success", "partial", "failed"):
            status = "partial"
        findings = action_input.get("findings") or []
        if isinstance(findings, str):
            findings = [findings]
        artifacts = action_input.get("artifacts") or {}
        if not isinstance(artifacts, dict):
            artifacts = {"value": artifacts}
        evidence = action_input.get("evidence") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        return WorkerResult(
            task_id=subtask.id,
            status=status,
            findings=[str(f) for f in findings],
            artifacts=artifacts,
            evidence=[str(e) for e in evidence],
            notes=str(action_input.get("notes", "")) + (f" [schema 提示: {issues[:2]}]" if issues else ""),
            steps=steps,
        )


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.7)]
    tail = text[-int(limit * 0.2) :]
    return f"{head}\n…[已截断 {len(text) - limit} 字符]…\n{tail}"


def _clip_json(obj: Any, limit: int) -> str:
    return _clip(json.dumps(obj, ensure_ascii=False, default=str), limit)
