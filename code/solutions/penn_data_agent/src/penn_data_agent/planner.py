"""Planner：把题目拆成「答案契约 + 子任务列表」，并做**规则级校验**。

为什么先定契约（Answer Contract）：
    本地 50 题归因显示——已提交题中「列数与 gold 一致」mean 0.806（perfect 29/36），
    「多给列」0.167、「少给列」0.056。也就是说**答案的列粒度几乎决定了对错**。
    官方 REACT 把这件事交给模型最后一刻自由发挥（且无任何校验），
    这里把它提到最前面，做成显式产物 + 规则校验 + Verifier 复核的闭环。

Planner 不调工具（环境事实由 Recon 层以代码方式提供），一次调用产出计划；
输出不合规时由 `LLMClient.complete_json` 带错误回灌重试，不消耗工具步数预算。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import BudgetConfig
from .llm import LLMClient
from .prompting import load_prompt
from .schema import PublicTask

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["question_factors", "answer_contract", "subtasks"],
    "properties": {
        "question_factors": {"type": "list", "min_len": 1, "items": {"type": "str"}},
        "answer_contract": {
            "type": "object",
            "required": ["restated_question", "expected_columns", "row_grain"],
            "properties": {
                "restated_question": {"type": "str", "min_len": 1},
                "expected_columns": {
                    "type": "list",
                    "min_len": 1,
                    "items": {
                        "type": "object",
                        "required": ["name", "semantic"],
                        "properties": {
                            "name": {"type": "str", "min_len": 1},
                            "semantic": {"type": "str", "min_len": 1},
                            "dtype": {"type": "str"},
                        },
                    },
                },
                "row_grain": {"type": "str", "min_len": 1},
                "expected_row_count": {"type": "int", "nullable": True},
            },
        },
        "subtasks": {
            "type": "list",
            "min_len": 1,
            "items": {
                "type": "object",
                "required": ["id", "goal", "acceptance"],
                "properties": {
                    "id": {"type": "str", "min_len": 1},
                    "goal": {"type": "str", "min_len": 1},
                    "depends_on": {"type": "list", "items": {"type": "str"}},
                    "inputs": {"type": "list", "items": {"type": "str"}},
                    "acceptance": {"type": "str", "min_len": 1},
                    "suggested_tools": {"type": "list", "items": {"type": "str"}},
                    "max_steps": {"type": "int"},
                },
            },
        },
        "risks": {"type": "list", "items": {"type": "str"}},
    },
}

KNOWN_TOOLS = {
    "list_context",
    "read_csv",
    "read_json",
    "read_doc",
    "inspect_sqlite_schema",
    "execute_context_sql",
    "execute_python",
}


@dataclass(slots=True)
class ColumnSpec:
    name: str
    semantic: str
    dtype: str = ""


@dataclass(slots=True)
class AnswerContract:
    restated_question: str
    expected_columns: list[ColumnSpec]
    row_grain: str
    expected_row_count: int | None = None

    def render(self) -> str:
        cols = "\n".join(
            f"  - {c.name}：{c.semantic}" + (f"（类型 {c.dtype}）" if c.dtype else "")
            for c in self.expected_columns
        )
        count = "未知" if self.expected_row_count is None else self.expected_row_count
        return (
            f"要回答什么：{self.restated_question}\n"
            f"期望列（共 {len(self.expected_columns)} 列）：\n{cols}\n"
            f"一行代表：{self.row_grain}\n"
            f"期望行数：{count}"
        )


@dataclass(slots=True)
class SubTask:
    id: str
    goal: str
    acceptance: str
    depends_on: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    suggested_tools: list[str] = field(default_factory=list)
    max_steps: int = 6


@dataclass(slots=True)
class Plan:
    question_factors: list[str]
    contract: AnswerContract
    subtasks: list[SubTask]
    risks: list[str] = field(default_factory=list)

    def topo_order(self) -> list[SubTask]:
        """按依赖拓扑序返回子任务（依赖在前）；有环时退化为原始顺序。"""
        by_id = {t.id: t for t in self.subtasks}
        remaining = list(self.subtasks)
        ordered: list[SubTask] = []
        seen: set[str] = set()
        while remaining:
            progressed = False
            for task in list(remaining):
                if all(dep in seen or dep not in by_id for dep in task.depends_on):
                    ordered.append(task)
                    seen.add(task.id)
                    remaining.remove(task)
                    progressed = True
            if not progressed:  # 有环，剩余按原序追加
                ordered.extend(remaining)
                break
        return ordered

    def render(self) -> str:
        lines = ["题目要素："]
        lines.extend(f"  - {f}" for f in self.question_factors)
        lines.append("\n答案契约：")
        lines.append("  " + self.contract.render().replace("\n", "\n  "))
        lines.append("\n子任务：")
        for task in self.subtasks:
            deps = ", ".join(task.depends_on) or "无"
            lines.append(f"  - [{task.id}] {task.goal}（依赖: {deps}）")
        if self.risks:
            lines.append("\n风险：")
            lines.extend(f"  - {r}" for r in self.risks)
        return "\n".join(lines)


def plan_from_dict(data: dict) -> Plan:
    contract_raw = data.get("answer_contract", {})
    contract = AnswerContract(
        restated_question=str(contract_raw.get("restated_question", "")),
        expected_columns=[
            ColumnSpec(
                name=str(c.get("name", "")),
                semantic=str(c.get("semantic", "")),
                dtype=str(c.get("dtype", "")),
            )
            for c in contract_raw.get("expected_columns", [])
        ],
        row_grain=str(contract_raw.get("row_grain", "")),
        expected_row_count=contract_raw.get("expected_row_count"),
    )
    subtasks = [
        SubTask(
            id=str(t.get("id", "")),
            goal=str(t.get("goal", "")),
            acceptance=str(t.get("acceptance", "")),
            depends_on=[str(d) for d in t.get("depends_on", []) or []],
            inputs=[str(i) for i in t.get("inputs", []) or []],
            suggested_tools=[str(s) for s in t.get("suggested_tools", []) or []],
            max_steps=int(t.get("max_steps", 6) or 6),
        )
        for t in data.get("subtasks", [])
    ]
    return Plan(
        question_factors=[str(f) for f in data.get("question_factors", [])],
        contract=contract,
        subtasks=subtasks,
        risks=[str(r) for r in data.get("risks", []) or []],
    )


def validate_plan(plan: Plan, budget: BudgetConfig) -> list[str]:
    """规则级校验（不信任模型自律）：返回问题清单，空列表表示通过。"""
    issues: list[str] = []
    if not plan.contract.expected_columns:
        issues.append("契约未定义任何列")
    if not (budget.min_subtasks <= len(plan.subtasks) <= budget.max_subtasks):
        issues.append(
            f"子任务数量 {len(plan.subtasks)} 不在允许范围 "
            f"[{budget.min_subtasks}, {budget.max_subtasks}]"
        )
    ids = [t.id for t in plan.subtasks]
    if len(set(ids)) != len(ids):
        issues.append("子任务 id 存在重复")
    id_set = set(ids)
    for task in plan.subtasks:
        for dep in task.depends_on:
            if dep not in id_set:
                issues.append(f"子任务 {task.id} 依赖了不存在的 id: {dep}")
        unknown = [t for t in task.suggested_tools if t not in KNOWN_TOOLS]
        if unknown:
            issues.append(f"子任务 {task.id} 引用了未知工具: {unknown}")
    # 环检测
    visited: dict[str, int] = {}

    def has_cycle(node: str, stack: set[str]) -> bool:
        if visited.get(node) == 1:
            return False
        if node in stack:
            return True
        stack.add(node)
        task = next((t for t in plan.subtasks if t.id == node), None)
        if task:
            for dep in task.depends_on:
                if dep in id_set and has_cycle(dep, stack):
                    return True
        stack.discard(node)
        visited[node] = 1
        return False

    for task in plan.subtasks:
        if has_cycle(task.id, set()):
            issues.append("子任务依赖存在环")
            break
    return issues


class Planner:
    def __init__(self, llm: LLMClient, budget: BudgetConfig | None = None):
        self.llm = llm
        self.budget = budget or BudgetConfig()

    def build_messages(self, task: PublicTask, env_card_text: str, feedback: str = "") -> list[dict]:
        user = [
            f"# 题目\n{task.question}",
            f"\n# 任务元信息\ntask_id: {task.task_id}\n难度: {task.difficulty or '未知'}",
            f"\n{env_card_text}",
        ]
        if feedback:
            user.append(f"\n# 上一次计划的问题（必须修正）\n{feedback}")
        user.append("\n# 要求\n只输出一个符合结构的 JSON 对象，不要任何解释文字。")
        return [{"role": "user", "content": "\n".join(user)}]

    def run(
        self,
        task: PublicTask,
        env_card_text: str,
        feedback: str = "",
    ) -> tuple[Plan, list[str]]:
        """产出计划，返回 (plan, issues)。issues 非空表示规则校验未通过。"""
        system = load_prompt("planner.md")
        messages = self.build_messages(task, env_card_text, feedback)
        data = self.llm.complete_json(
            messages,
            system=system,
            schema=PLAN_SCHEMA,
            tries=self.budget.planner_retries + 1,
        )
        plan = plan_from_dict(data)
        plan.subtasks = plan.subtasks[: self.budget.max_subtasks]
        for subtask in plan.subtasks:
            subtask.max_steps = max(1, min(int(subtask.max_steps), self.budget.worker_max_steps))
        return plan, validate_plan(plan, self.budget)
