"""sqlite 工具：只读模式查 schema 与执行只读 SQL。

# 来源：官方 KDD Cup 2026 DataAgent-Bench starter kit（PHASE_1/data_agent_baseline）
# 路径：tools/sqlite.py ｜ 用途：自研 penn_data_agent 可复用工具层
# 基于官方代码直接移植（含 import 适配与注释），非自研新代码
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


def _connect_read_only(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def inspect_sqlite_schema(path: Path) -> dict[str, object]:
    # 注：官方用 `with conn`，那只会自动 commit/rollback 而非 close；
    # Windows 下连接句柄不释放会导致文件占用，故改用 closing 显式关闭。
    with closing(_connect_read_only(path)) as conn:
        rows = conn.execute(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        tables: list[dict[str, object]] = []
        for name, create_sql in rows:
            tables.append(
                {
                    "name": name,
                    "create_sql": create_sql,
                }
            )
    return {
        "path": str(path),
        "tables": tables,
    }


def execute_read_only_sql(path: Path, sql: str, *, limit: int = 200) -> dict[str, object]:
    normalized_sql = sql.lstrip().lower()
    if not normalized_sql.startswith(("select", "with", "pragma")):
        raise ValueError("Only read-only SQL statements are allowed.")

    with closing(_connect_read_only(path)) as conn:
        cursor = conn.execute(sql)
        column_names = [item[0] for item in cursor.description or []]
        rows = cursor.fetchmany(limit + 1)

    truncated = len(rows) > limit
    limited_rows = rows[:limit]
    return {
        "path": str(path),
        "columns": column_names,
        "rows": [list(row) for row in limited_rows],
        "row_count": len(limited_rows),
        "truncated": truncated,
    }
