"""ReAct 对照基线（自研实现，用于与 Plan-and-Execute 做同模型对照）。

与官方 baseline 的差别：
- 协议同样是「文本 JSON + 每步一动作」，但解析走 `jsonio` 严格 schema 校验 + 错误回灌，
  解析失败不再计一步（官方会白烧步数预算）；
- observation 有截断与历史折叠（官方全量回灌，17 步即 15K tokens）；
- 默认**不**给环境卡片（与官方同口径）；需要更公平的"强基线"时可用 `with_env_card=True`。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .config import AgentConfig
from .jsonio import SchemaError, parse_with_schema
from .llm import LLMClient
from .prompting import load_prompt
from .schema import AnswerTable, PublicTask
from .tools import create_default_tool_registry
from .tools.registry import ToolRegistry
from .worker import STEP_SCHEMA, _clip, render_tool_menu

REACT_SCHEMA = STEP_SCHEMA


@dataclass(slots=True)
class ReactOutcome:
    answer: AnswerTable | None
    steps: int = 0
    trace: list[dict] = field(default_factory=list)
    failure_reason: str = ""


class ReActAgent:
    def __init__(
        self,
        llm: LLMClient,
        cfg: AgentConfig | None = None,
        registry: ToolRegistry | None = None,
        with_env_card: bool = False,
    ):
        self.llm = llm
        self.cfg = cfg or AgentConfig()
        self.registry = registry or create_default_tool_registry()
        self.with_env_card = with_env_card

    def _system(self) -> str:
        base = load_prompt("system.md")
        menu = render_tool_menu(self.registry)
        return (
            base
            + "\n\n# 可用工具\n"
            + menu
            + "\n\n# 输出格式\n每一步只输出一个 JSON 对象：\n"
            + '{"thought": "...", "action": "<工具名>", "action_input": {...}}\n'
            + "完成时使用 answer 工具提交表格：action_input = {\"columns\": [...], \"rows\": [[...]]}。"
        )

    def run(self, task: PublicTask, env_card_text: str = "", max_steps: int = 16) -> ReactOutcome:
        user = f"# 题目\n{task.question}\n\n# context 目录\n{task.context_dir}"
        if self.with_env_card and env_card_text:
            user += f"\n\n{env_card_text}"
        messages: list[dict] = [{"role": "user", "content": user}]
        history: list[dict] = []
        trace: list[dict] = []

        for step in range(1, max_steps + 1):
            raw = self.llm.complete(self._rebuild(messages, history), system=self._system())
            try:
                step_obj = parse_with_schema(raw, REACT_SCHEMA)
            except SchemaError as exc:
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": "格式错误：" + "；".join(exc.errors[:3]) + "。请只输出一个 JSON 对象。"},
                ]
                continue

            action = str(step_obj.get("action", ""))
            action_input = step_obj.get("action_input") or {}
            if not isinstance(action_input, dict):
                action_input = {"value": action_input}

            if action not in self.registry.handlers:
                observation = f"未知工具 '{action}'。可用: {sorted(self.registry.specs)}"
                history.append({"raw": raw, "observation": observation})
                trace.append({"step": step, "action": action, "observation": observation[:300]})
                continue

            try:
                result = self.registry.execute(task, action, action_input)
            except Exception as exc:  # noqa: BLE001
                observation = f"工具异常: {type(exc).__name__}: {exc}"
                history.append({"raw": raw, "observation": observation})
                trace.append({"step": step, "action": action, "observation": observation[:300]})
                continue

            if result.is_terminal and result.answer is not None:
                trace.append({"step": step, "action": "answer", "status": "submitted"})
                return ReactOutcome(answer=result.answer, steps=step, trace=trace)

            observation = _clip(
                json.dumps({"ok": result.ok, "content": result.content}, ensure_ascii=False, default=str),
                self.cfg.context.observation_max_chars,
            )
            history.append({"raw": raw, "observation": observation})
            trace.append({"step": step, "action": action, "observation": observation[:300]})

        return ReactOutcome(
            answer=None,
            steps=max_steps,
            trace=trace,
            failure_reason=f"{max_steps} 步内未提交答案",
        )

    def _rebuild(self, base: list[dict], history: list[dict]) -> list[dict]:
        keep = self.cfg.context.keep_recent_observations
        messages = list(base)
        total = len(history)
        for index, item in enumerate(history):
            messages.append({"role": "assistant", "content": item["raw"]})
            observation = item["observation"]
            if total - index > keep:
                observation = " ".join(observation.split())[:200] + " …(早期观察已折叠)"
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        return messages
