"""Composer：把各子任务的结构化产出，按答案契约组装成最终答案表。

与官方 REACT 的关键差异：官方由同一个 agent 在最后一步「顺手」输出答案，
没有任何力量保证列粒度合规；这里单独设一层，只做「按契约拼表」，
输入是子任务结果（不是全量历史），输出后还要过 Verifier 门禁。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import BudgetConfig
from .llm import LLMClient
from .planner import AnswerContract
from .prompting import load_prompt
from .schema import AnswerTable, PublicTask
from .worker import WorkerResult

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["columns", "rows"],
    "properties": {
        "columns": {"type": "list", "min_len": 1, "items": {"type": "str"}},
        "rows": {"type": "list", "items": {"type": "list"}},
        "notes": {"type": "str"},
    },
}


@dataclass(slots=True)
class ComposeOutcome:
    answer: AnswerTable | None
    notes: str = ""
    raw: dict | None = None


class Composer:
    def __init__(self, llm: LLMClient, budget: BudgetConfig | None = None):
        self.llm = llm
        self.budget = budget or BudgetConfig()

    def run(
        self,
        task: PublicTask,
        contract: AnswerContract,
        results: list[WorkerResult],
    ) -> ComposeOutcome:
        system = load_prompt("composer.md")
        results_text = "\n\n".join(r.render_summary(max_chars=2000) for r in results) or "（无子任务结果）"
        user = "\n".join(
            [
                f"# 原题\n{task.question}",
                "\n# 答案契约",
                contract.render(),
                "\n# 子任务结果",
                results_text,
                "\n# 要求\n只输出一个 JSON 对象：columns / rows / notes。",
            ]
        )
        try:
            data = self.llm.complete_json(
                [{"role": "user", "content": user}],
                system=system,
                schema=ANSWER_SCHEMA,
                tries=self.budget.composer_retries + 1,
            )
        except Exception as exc:  # noqa: BLE001 - 组装失败也不能中断整题
            return ComposeOutcome(answer=None, notes=f"composer 失败: {type(exc).__name__}: {exc}")

        columns = [str(c) for c in data.get("columns", [])]
        rows = _normalize_rows(data.get("rows", []), len(columns))
        if not columns:
            return ComposeOutcome(answer=None, notes="composer 未产出列", raw=data)
        return ComposeOutcome(
            answer=AnswerTable(columns=columns, rows=rows),
            notes=str(data.get("notes", "")),
            raw=data,
        )


def _normalize_rows(rows: Any, width: int) -> list[list[Any]]:
    """把 rows 规整成矩形表（缺补空、多截断），保证下游不炸。"""
    normalized: list[list[Any]] = []
    if not isinstance(rows, list):
        return normalized
    for row in rows:
        if isinstance(row, list):
            values = list(row)
        else:
            values = [row]
        if len(values) < width:
            values = values + [""] * (width - len(values))
        elif len(values) > width:
            values = values[:width]
        normalized.append([_scalar(v) for v in values])
    return normalized


def _scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
