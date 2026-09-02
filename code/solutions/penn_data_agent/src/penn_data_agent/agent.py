"""ReAct agent loop (v0.1 skeleton)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from .llm import LLMClient
from .protocol import parse_action


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[[dict], object]


@dataclass
class AgentState:
    question: str = ""
    history: list[dict] = field(default_factory=list)
    steps: int = 0


class ReActAgent:
    def __init__(self, llm: LLMClient, tools: list[Tool], system_prompt: str, max_steps: int = 20):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.system_prompt = system_prompt
        self.max_steps = max_steps

    def tool_descriptions(self) -> str:
        return "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())

    def run(self, question: str, context_dir: str) -> str:
        state = AgentState(question=question)
        state.history.append({"role": "user", "content": f"Question: {question}\nContext dir: {context_dir}"})

        while state.steps < self.max_steps:
            text = self.llm.complete(state.history, system=self.system_prompt + "\n\nTools:\n" + self.tool_descriptions())
            parsed = parse_action(text)
            if parsed is None:
                state.history.append({"role": "user", "content": "Invalid format. Reply with a JSON object containing 'thought', 'action', 'action_input'."})
                continue

            action, action_input = parsed["action"], parsed.get("action_input", {})
            if action == "answer":
                return str(action_input.get("final_answer", ""))

            tool = self.tools.get(action)
            if tool is None:
                observation = f"Unknown tool '{action}'. Available: {sorted(self.tools)}"
            else:
                try:
                    observation = json.dumps(tool.fn(action_input), ensure_ascii=False, default=str)
                except Exception as exc:
                    observation = f"Tool error: {exc}"

            state.steps += 1
            state.history.append({"role": "assistant", "content": text})
            state.history.append({"role": "user", "content": f"Observation:\n{observation}"})

        raise RuntimeError("max steps exceeded without answer")
