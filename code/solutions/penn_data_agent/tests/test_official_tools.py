"""官方工具层移植的冒烟测试（unittest 风格，标准库即可运行）。

覆盖：默认注册表解析 / list_context / read_csv_preview / inspect_sqlite_schema /
execute_read_only_sql / answer 提交终态路径。
不依赖 pytest，也不触发真实 python 子进程沙箱（不调用 execute_python_code 子进程）。
运行（在 code/solutions/penn_data_agent 下）：py tests/test_official_tools.py
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# 让本文件可直接运行也能定位到 src 布局下的包
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from penn_data_agent.schema import PublicTask, TaskAssets, TaskRecord  # noqa: E402
from penn_data_agent.tools import create_default_tool_registry  # noqa: E402
from penn_data_agent.tools.registry import ToolExecutionResult  # noqa: E402

EXPECTED_TOOLS = {
    "answer",
    "execute_context_sql",
    "execute_python",
    "inspect_sqlite_schema",
    "list_context",
    "read_csv",
    "read_doc",
    "read_json",
}


def build_task(tmp_root: Path) -> PublicTask:
    """构造最小 context：csv + 文档 + 嵌套目录里的 sqlite，返回 PublicTask。"""
    ctx = tmp_root / "context"
    ctx.mkdir()
    sub = ctx / "nested"
    sub.mkdir()

    (ctx / "sales.csv").write_text(
        "city,amount\nbeijing,10\nshanghai,20\n",
        encoding="utf-8",
    )
    (ctx / "readme.md").write_text("hello context doc", encoding="utf-8")

    db_path = sub / "data.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO users (id, name) VALUES (1, 'alice')")
        conn.execute("INSERT INTO users (id, name) VALUES (2, 'bob')")
        conn.commit()
    finally:
        conn.close()

    return PublicTask(
        record=TaskRecord(task_id="t_smoke", difficulty="easy", question="smoke test"),
        assets=TaskAssets(task_dir=ctx, context_dir=ctx),
    )


class OfficialToolsSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.task = build_task(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_default_registry_has_eight_tools(self) -> None:
        registry = create_default_tool_registry()
        self.assertEqual(len(registry.specs), 8)
        self.assertEqual(set(registry.specs), EXPECTED_TOOLS)
        self.assertEqual(set(registry.handlers), EXPECTED_TOOLS)

    def test_list_context_shows_files_and_nested_dir(self) -> None:
        registry = create_default_tool_registry()
        result: ToolExecutionResult = registry.execute(self.task, "list_context", {"max_depth": 3})
        self.assertTrue(result.ok)
        paths = {entry["path"] for entry in result.content["entries"]}
        self.assertIn("sales.csv", paths)
        self.assertIn("nested/data.db", paths)

    def test_read_csv_preview(self) -> None:
        registry = create_default_tool_registry()
        result: ToolExecutionResult = registry.execute(self.task, "read_csv", {"path": "sales.csv"})
        self.assertTrue(result.ok)
        self.assertEqual(result.content["columns"], ["city", "amount"])
        self.assertEqual(result.content["rows"], [["beijing", "10"], ["shanghai", "20"]])
        self.assertEqual(result.content["row_count"], 2)

    def test_inspect_sqlite_schema(self) -> None:
        registry = create_default_tool_registry()
        result: ToolExecutionResult = registry.execute(
            self.task, "inspect_sqlite_schema", {"path": "nested/data.db"}
        )
        self.assertTrue(result.ok)
        self.assertEqual([t["name"] for t in result.content["tables"]], ["users"])

    def test_execute_context_sql(self) -> None:
        registry = create_default_tool_registry()
        result: ToolExecutionResult = registry.execute(
            self.task,
            "execute_context_sql",
            {"path": "nested/data.db", "sql": "SELECT name FROM users ORDER BY id", "limit": 10},
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.content["columns"], ["name"])
        self.assertEqual(result.content["rows"], [["alice"], ["bob"]])

    def test_execute_context_sql_rejects_write(self) -> None:
        registry = create_default_tool_registry()
        with self.assertRaises(ValueError):
            registry.execute(
                self.task,
                "execute_context_sql",
                {"path": "nested/data.db", "sql": "DROP TABLE users"},
            )

    def test_answer_is_terminal(self) -> None:
        registry = create_default_tool_registry()
        result: ToolExecutionResult = registry.execute(
            self.task,
            "answer",
            {"columns": ["city"], "rows": [["beijing"], ["shanghai"]]},
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.is_terminal)
        self.assertIsNotNone(result.answer)
        assert result.answer is not None
        self.assertEqual(result.answer.columns, ["city"])
        self.assertEqual(result.answer.to_dict()["rows"], [["beijing"], ["shanghai"]])
        self.assertEqual(result.content["row_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
