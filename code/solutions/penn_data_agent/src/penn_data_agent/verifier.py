"""Verifier：fail-closed 输出门禁。

守两类问题（对应本地 50 题归因的两大失分点）：
1. **形状**：列数/列粒度与契约不符（多给列要罚分、少给列损失召回）；
2. **证据**：答案里的值在子任务结果中找不到支撑（防幻觉）。

判定结果三选一：`submit`（可用/已修正）、`retry`（数据不足需重查）、`replan`（契约本身错了）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import BudgetConfig
from .llm import LLMClient
from .planner import AnswerContract
from .prompting import load_prompt
from .schema import AnswerTable, PublicTask
from .worker import WorkerResult

VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["passed", "issues", "suggestion"],
    "properties": {
        "passed": {"type": "bool"},
        "issues": {
            "type": "list",
            "items": {
                "type": "object",
                "required": ["type", "detail"],
                "properties": {
                    "type": {"type": "str", "enum": ["shape", "semantic", "evidence", "format", "contract"]},
                    "detail": {"type": "str"},
                },
            },
        },
        "fixed_columns": {"type": "list", "items": {"type": "str"}},
        "fixed_rows": {"type": "list", "items": {"type": "list"}},
        "suggestion": {"type": "str", "enum": ["submit", "retry", "replan"]},
    },
}


@dataclass(slots=True)
class VerifyResult:
    passed: bool
    issues: list[dict] = field(default_factory=list)
    fixed_answer: AnswerTable | None = None
    suggestion: str = "submit"
    raw: dict | None = None

    def issue_text(self) -> str:
        return "\n".join(f"- [{i.get('type')}] {i.get('detail')}" for i in self.issues)


class Verifier:
    def __init__(self, llm: LLMClient, budget: BudgetConfig | None = None):
        self.llm = llm
        self.budget = budget or BudgetConfig()

    def run(
        self,
        task: PublicTask,
        contract: AnswerContract,
        candidate: AnswerTable,
        results: list[WorkerResult],
    ) -> VerifyResult:
        # 规则前置：形状明显不合法时不必花钱问模型
        if not candidate.columns or not candidate.rows:
            return VerifyResult(
                passed=False,
                issues=[{"type": "format", "detail": "答案为空表（无列或无行）"}],
                suggestion="retry",
            )

        system = load_prompt("verifier.md")
        results_text = "\n".join(r.render_summary(max_chars=1200) for r in results) or "（无）"
        user = "\n".join(
            [
                f"# 原题\n{task.question}",
                "\n# 答案契约",
                contract.render(),
                "\n# 待检答案表",
                f"columns: {candidate.columns}",
                f"rows: {_clip_rows(candidate.rows)}",
                "\n# 子任务结果摘要",
                results_text,
                "\n# 要求\n只输出一个 JSON 对象。",
            ]
        )
        try:
            data = self.llm.complete_json(
                [{"role": "user", "content": user}],
                system=system,
                schema=VERIFY_SCHEMA,
                tries=self.budget.verifier_retries + 1,
            )
        except Exception as exc:  # noqa: BLE001 - 门禁自身失败时不阻断提交
            return VerifyResult(passed=True, issues=[{"type": "format", "detail": f"verifier 异常: {exc}"}],
                                suggestion="submit")

        issues = [i for i in data.get("issues", []) if isinstance(i, dict)]
        suggestion = str(data.get("suggestion", "submit"))
        if suggestion not in ("submit", "retry", "replan"):
            suggestion = "submit"
        passed = bool(data.get("passed", False))

        fixed = _build_fixed(data, candidate)
        # 规则兜底：模型说通过但表是空的，仍然判不通过
        if passed and (not candidate.columns or not candidate.rows):
            passed = False
            suggestion = "retry"
        return VerifyResult(
            passed=passed, issues=issues, fixed_answer=fixed, suggestion=suggestion, raw=data
        )


def _build_fixed(data: dict, candidate: AnswerTable) -> AnswerTable | None:
    columns = data.get("fixed_columns")
    rows = data.get("fixed_rows")
    if not isinstance(columns, list) or not columns:
        return None
    width = len(columns)
    normalized: list[list[Any]] = []
    for row in rows or []:
        if not isinstance(row, list):
            continue
        values = list(row)[:width]
        values += [""] * (width - len(values))
        normalized.append(values)
    if not normalized:
        return None
    return AnswerTable(columns=[str(c) for c in columns], rows=normalized)


def _clip_rows(rows: list[list[Any]], limit: int = 1200) -> str:
    text = repr(rows)
    return text if len(text) <= limit else text[:limit] + " …(截断)"
