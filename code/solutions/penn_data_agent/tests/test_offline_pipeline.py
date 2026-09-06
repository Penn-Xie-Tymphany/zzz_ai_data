"""离线冒烟：用 ScriptedLLM 回放固定回复，验证 Recon→Planner→Worker→Composer→Verifier 全链路。

**不调用真实模型**，可在任何环境跑。用真实 task_11 数据（磁盘上的 json + knowledge.md）。

运行：
    py tests/test_offline_pipeline.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from penn_data_agent.config import AgentConfig  # noqa: E402
from penn_data_agent.dataset import load_task  # noqa: E402
from penn_data_agent.jsonio import SchemaError, parse_with_schema, validate  # noqa: E402
from penn_data_agent.llm import ScriptedLLM  # noqa: E402
from penn_data_agent.orchestrator import PlanExecuteAgent  # noqa: E402
from penn_data_agent.planner import plan_from_dict, validate_plan  # noqa: E402
from penn_data_agent.recon import build_env_card, render_env_card  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
INPUT_ROOT = (
    ROOT / "competitions" / "kddcup2026-data-agents-starter-kit" / "PHASE_1" / "data" / "public" / "input"
)

PLAN_REPLY = json.dumps(
    {
        "question_factors": ["血栓程度为 severe 的患者", "输出 ID / 性别 / 诊断"],
        "answer_contract": {
            "restated_question": "列出 severe 血栓患者的 ID、性别与诊断",
            "expected_columns": [
                {"name": "ID", "semantic": "患者 ID", "dtype": "text"},
                {"name": "SEX", "semantic": "性别", "dtype": "text"},
                {"name": "Diagnosis", "semantic": "诊断结果", "dtype": "text"},
            ],
            "row_grain": "一名患者一行",
            "expected_row_count": None,
        },
        "subtasks": [
            {
                "id": "T1",
                "goal": "从 Patient.json / Examination.json 找出 severe 血栓患者的 ID、性别、诊断",
                "depends_on": [],
                "inputs": ["json/Patient.json"],
                "acceptance": "给出患者列表及其 ID/性别/诊断",
                "suggested_tools": ["execute_python"],
                "max_steps": 5,
            }
        ],
        "risks": ["两个 json 需要按患者 ID 关联"],
    },
    ensure_ascii=False,
)

WORKER_REPLY = json.dumps(
    {
        "thought": "已用 python 聚合出结果",
        "action": "finish",
        "action_input": {
            "status": "success",
            "findings": ["severe 患者共 3 人"],
            "artifacts": {"rows": [["163109", "F", "SLE"], ["2803470", "F", "SLE"]]},
            "evidence": ["execute_python 输出前 5 行"],
            "notes": "",
        },
    },
    ensure_ascii=False,
)

COMPOSER_REPLY = json.dumps(
    {
        "columns": ["ID", "SEX", "Diagnosis"],
        "rows": [["163109", "F", "SLE"], ["2803470", "F", "SLE"]],
        "notes": "",
    },
    ensure_ascii=False,
)

VERIFIER_REPLY = json.dumps(
    {"passed": True, "issues": [], "fixed_columns": ["ID", "SEX", "Diagnosis"],
     "fixed_rows": [["163109", "F", "SLE"], ["2803470", "F", "SLE"]], "suggestion": "submit"},
    ensure_ascii=False,
)


class TestJsonIO(unittest.TestCase):
    def test_extract_and_validate(self):
        text = '前面有废话\n```json\n{"a": 1, "b": ["x"]}\n```\n后面也有'
        obj = parse_with_schema(text, {
            "type": "object",
            "required": ["a", "b"],
            "properties": {"a": {"type": "int"}, "b": {"type": "list", "items": {"type": "str"}}},
        })
        self.assertEqual(obj["a"], 1)

    def test_missing_field_raises(self):
        with self.assertRaises(SchemaError):
            parse_with_schema('{"a": 1}', {"type": "object", "required": ["b"]})

    def test_enum_check(self):
        errors = validate("maybe", {"type": "str", "enum": ["success", "failed"]})
        self.assertTrue(errors)


class TestPlanValidation(unittest.TestCase):
    def test_cycle_detected(self):
        data = {
            "question_factors": ["x"],
            "answer_contract": {
                "restated_question": "r",
                "expected_columns": [{"name": "c", "semantic": "s"}],
                "row_grain": "g",
            },
            "subtasks": [
                {"id": "T1", "goal": "g", "acceptance": "a", "depends_on": ["T2"]},
                {"id": "T2", "goal": "g", "acceptance": "a", "depends_on": ["T1"]},
            ],
        }
        plan = plan_from_dict(data)
        issues = validate_plan(plan, AgentConfig().budget)
        self.assertTrue(any("环" in i for i in issues))

    def test_unknown_tool_detected(self):
        data = {
            "question_factors": ["x"],
            "answer_contract": {
                "restated_question": "r",
                "expected_columns": [{"name": "c", "semantic": "s"}],
                "row_grain": "g",
            },
            "subtasks": [
                {"id": "T1", "goal": "g", "acceptance": "a", "suggested_tools": ["not_a_tool"]}
            ],
        }
        issues = validate_plan(plan_from_dict(data), AgentConfig().budget)
        self.assertTrue(any("未知工具" in i for i in issues))


class TestRecon(unittest.TestCase):
    def test_env_card_on_real_task(self):
        if not (INPUT_ROOT / "task_11").exists():
            self.skipTest("缺少 demo 数据集")
        task = load_task(INPUT_ROOT, "task_11")
        card = build_env_card(task, AgentConfig().context)
        text = render_env_card(card)
        self.assertIn("knowledge.md", text)
        self.assertIn("Patient.json", text)


class TestOfflinePipeline(unittest.TestCase):
    def test_full_pipeline(self):
        if not (INPUT_ROOT / "task_11").exists():
            self.skipTest("缺少 demo 数据集")
        llm = ScriptedLLM(replies=[PLAN_REPLY, WORKER_REPLY, COMPOSER_REPLY, VERIFIER_REPLY])
        agent = PlanExecuteAgent(llm, AgentConfig())
        outcome = agent.run(load_task(INPUT_ROOT, "task_11"))
        self.assertTrue(outcome.submitted, msg=outcome.failure_reason)
        self.assertEqual(outcome.answer.columns, ["ID", "SEX", "Diagnosis"])
        self.assertEqual(outcome.trace.get("plan_issues"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
