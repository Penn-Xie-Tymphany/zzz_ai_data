"""LLM 后端封装（OpenAI 兼容 API）+ 带 schema 校验的结构化调用。

关键点：
- `complete_json()` 把「抽取 → 校验 → 失败回灌重试」封装成一次调用：
  校验失败**不计入工具步数预算**，只消耗 `tries`，这正是针对官方
  「解析失败白烧步数」的修复；
- 所有 agent（Planner / Worker / Composer / Verifier）统一使用同一模型实例，
  便于对照实验时整体换模型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from .config import LLMConfig
from .jsonio import SchemaError, dumps_compact, parse_with_schema


@dataclass(slots=True)
class Usage:
    """累计 token 用量（用于复盘成本）。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    def add(self, usage_obj: Any) -> None:
        if usage_obj is None:
            return
        self.calls += 1
        self.prompt_tokens += int(getattr(usage_obj, "prompt_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage_obj, "completion_tokens", 0) or 0)


class LLMClient:
    def __init__(self, cfg: LLMConfig | None = None):
        self.cfg = cfg or LLMConfig()
        if not self.cfg.api_key:
            raise RuntimeError(
                "缺少 LLM_API_KEY：请在 --config 指向的 yaml 里填写，或设置环境变量 LLM_API_KEY。"
            )
        self.client = OpenAI(
            api_key=self.cfg.api_key,
            base_url=self.cfg.api_base or None,
            timeout=self.cfg.timeout_seconds,
            max_retries=self.cfg.max_retries,
        )
        self.model = self.cfg.model
        self.usage = Usage()

    # ------------------------------------------------------------------ 基础
    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        temperature: float | None = None,
    ) -> str:
        full = ([{"role": "system", "content": system}] if system else []) + list(messages)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=full,
            temperature=self.cfg.temperature if temperature is None else temperature,
        )
        self.usage.add(getattr(resp, "usage", None))
        return resp.choices[0].message.content or ""

    # ------------------------------------------------------ 结构化（带校验重试）
    def complete_json(
        self,
        messages: list[dict[str, str]],
        system: str,
        schema: dict[str, Any],
        tries: int = 3,
        temperature: float | None = None,
        on_error: Any = None,
    ) -> dict:
        """反复调用直到产出符合 schema 的 JSON。

        失败时把具体错误作为一条 user 消息追加（而不是让它自由发挥），
        这样模型知道错在哪、下一次通常能改对。
        """
        convo = list(messages)
        last_errors: list[str] = []
        for attempt in range(max(1, tries)):
            text = self.complete(convo, system=system, temperature=temperature)
            try:
                return parse_with_schema(text, schema)
            except SchemaError as exc:
                last_errors = exc.errors
                if on_error:
                    on_error(attempt + 1, last_errors, text)
                convo.append({"role": "assistant", "content": text})
                convo.append(
                    {
                        "role": "user",
                        "content": (
                            "你的回复不符合要求的结构，错误如下：\n"
                            + "\n".join(f"- {e}" for e in last_errors)
                            + "\n请只输出一个修正后的 JSON 对象，不要任何解释文字。"
                        ),
                    }
                )
        raise SchemaError(last_errors or ["多次尝试后仍未产出合规 JSON"])

    # ------------------------------------------------------------------ 兜底
    @staticmethod
    def render_json_block(obj: Any) -> str:
        return dumps_compact(obj)


@dataclass(slots=True)
class ScriptedLLM:
    """测试替身：按预设脚本回放回复，便于离线跑通全链路。"""

    replies: list[str] = field(default_factory=list)
    index: int = 0
    usage: Usage = field(default_factory=Usage)

    @property
    def model(self) -> str:
        return "scripted"

    def complete(self, messages: list[dict[str, str]], system: str | None = None,
                 temperature: float | None = None) -> str:
        if self.index >= len(self.replies):
            return "{}"
        reply = self.replies[self.index]
        self.index += 1
        return reply

    def complete_json(self, messages, system, schema, tries=3, temperature=None, on_error=None) -> dict:
        from .jsonio import parse_with_schema

        return parse_with_schema(self.complete(messages, system=system), schema)
