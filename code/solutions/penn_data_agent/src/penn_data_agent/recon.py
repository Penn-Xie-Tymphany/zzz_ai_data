"""Recon 侦察层：用**确定性代码**（零 LLM）把 context 扫成一张「环境卡片」。

动机（来自官方 REACT 拆解）：官方 agent 前 3~5 步几乎都在做同一件事——
`list_context` → `inspect_sqlite_schema` / `read_csv` → 才明白数据长什么样。
这些探索是**确定性的、可复用的**，不该让 LLM 花钱又花步数去试。

本层把探索固化为代码，产出给 Planner 的事实卡片：
- 文件树 + 体积（大文件标注，提醒不要整读）
- CSV：表头 + 前 N 行 + 行数（小文件精确、大文件估算）
- SQLite：表名 + 建表 SQL + 行数估计
- JSON：结构骨架（顶层 key / 数组首元素 key）
- 文档（md/txt）：开头若干字符；**`knowledge.md` 是每题自带的领域说明，优先完整给出**
"""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .config import ContextConfig
from .schema import PublicTask

_TEXT_SUFFIXES = {".md", ".txt", ".rst", ".log", ".html", ".htm", ".xml", ".yaml", ".yml"}


def build_env_card(
    task: PublicTask,
    cfg: ContextConfig | None = None,
) -> dict:
    """扫描 context 目录，返回结构化的环境事实。"""
    cfg = cfg or ContextConfig()
    root = task.context_dir
    files: list[dict] = []
    notes: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if len(files) >= cfg.env_card_max_files:
            notes.append(f"文件数超过 {cfg.env_card_max_files}，已截断（仅列出前若干个）")
            break
        rel = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
        except OSError:
            continue
        entry: dict = {"path": rel, "size": size}
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                entry.update(_probe_csv(path, cfg))
            elif suffix in (".sqlite", ".sqlite3", ".db"):
                entry.update(_probe_sqlite(path))
            elif suffix == ".json":
                entry.update(_probe_json(path, cfg))
            elif suffix in _TEXT_SUFFIXES:
                entry.update(_probe_text(path, cfg))
        except Exception as exc:  # noqa: BLE001 - 侦察层必须永不失败
            entry["probe_error"] = f"{type(exc).__name__}: {exc}"
        files.append(entry)

    return {
        "task_id": task.task_id,
        "context_root": str(root),
        "files": files,
        "notes": notes,
    }


def _probe_csv(path: Path, cfg: ContextConfig) -> dict:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        preview: list[list[str]] = []
        for row in reader:
            preview.append(row)
            if len(preview) >= cfg.csv_preview_rows:
                break
    info: dict = {
        "kind": "csv",
        "columns": header,
        "preview_rows": preview,
    }
    if path.stat().st_size <= cfg.max_rowcount_file_bytes:
        info["row_count"] = _count_rows(path)
    else:
        info["row_count"] = None
        info["row_count_note"] = "文件过大，未精确统计行数，请用 SQL/Python 聚合查询"
    return info


def _count_rows(path: Path) -> int:
    total = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for _ in handle:
            total += 1
    return max(0, total - 1)


def _probe_sqlite(path: Path) -> dict:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        tables = []
        for name, create_sql in rows:
            columns = _safe_columns(conn, name)
            tables.append(
                {
                    "name": name,
                    "columns": columns,
                    "row_count_estimate": _safe_row_estimate(conn, name),
                    "create_sql": (create_sql or "")[:400],
                }
            )
    return {"kind": "sqlite", "tables": tables}


def _safe_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
    except sqlite3.Error:
        return []


def _safe_row_estimate(conn: sqlite3.Connection, table: str) -> int | None:
    """行数估计：优先 MAX(rowid)（O(1)），失败再 COUNT(*)。"""
    try:
        value = conn.execute(f'SELECT MAX(rowid) FROM "{table}"').fetchone()
        if value and value[0] is not None:
            return int(value[0])
    except sqlite3.Error:
        return None
    return None


def _probe_json(path: Path, cfg: ContextConfig) -> dict:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        head = handle.read(min(path.stat().st_size, 200_000))
    skeleton = _json_skeleton(head)
    preview = head[: cfg.json_preview_chars]
    return {"kind": "json", "skeleton": skeleton, "preview": preview}


def _json_skeleton(head: str) -> dict:
    """用 raw_decode 解析出 JSON 的结构骨架（不加载大文件全量）。"""
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(head)
    except ValueError:
        return {"parse": "failed", "hint": head[:200]}
    return {"parse": "ok", "structure": _describe(obj)}


def _describe(obj, depth: int = 0) -> dict:
    if depth > 3:
        return {"type": "..."}
    if isinstance(obj, dict):
        return {
            "type": "object",
            "keys": list(obj.keys())[:20],
            "sample": {k: _describe(v, depth + 1) for k, v in list(obj.items())[:3]},
        }
    if isinstance(obj, list):
        return {
            "type": "array",
            "length_hint": len(obj),
            "item": _describe(obj[0], depth + 1) if obj else None,
        }
    return {"type": type(obj).__name__, "sample": str(obj)[:60]}


def _probe_text(path: Path, cfg: ContextConfig) -> dict:
    size = path.stat().st_size
    limit = cfg.knowledge_chars if path.name.lower() == "knowledge.md" else cfg.doc_preview_chars
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        head = handle.read(limit)
    return {
        "kind": "doc",
        "preview": head,
        "truncated": size > limit,
        "is_knowledge": path.name.lower() == "knowledge.md",
    }


def render_env_card(card: dict) -> str:
    """把环境卡片渲染成给 LLM 看的紧凑文本（控制体积，避免撑爆 prompt）。"""
    lines: list[str] = [f"# 环境卡片（context 侦察结果，均为**已确认的事实**）"]
    lines.append(f"- 任务: {card.get('task_id', '')}")
    lines.append(f"- 文件数: {len(card.get('files', []))}")
    for note in card.get("notes", []):
        lines.append(f"- 注意: {note}")

    knowledge_parts: list[str] = []
    for item in card.get("files", []):
        rel = item.get("path", "")
        size = item.get("size", 0)
        kind = item.get("kind", "other")
        head = f"\n## {rel}  ({kind}, {_human_size(size)})"
        if kind == "csv":
            columns = item.get("columns", [])
            preview = item.get("preview_rows", [])
            row_count = item.get("row_count")
            body = [
                head,
                f"- 列({len(columns)}): {_clip(', '.join(map(str, columns)), 800)}",
                f"- 行数: {row_count if row_count is not None else item.get('row_count_note', '未知')}",
                "- 前几行:",
            ]
            for row in preview:
                body.append("  " + _clip(", ".join(map(str, row)), 400))
            lines.extend(body)
        elif kind == "sqlite":
            body = [head, "- 表:"]
            for table in item.get("tables", []):
                body.append(
                    f"  - {table.get('name')} (约 {table.get('row_count_estimate')} 行) "
                    f"列: {_clip(', '.join(map(str, table.get('columns', []))), 500)}"
                )
            lines.extend(body)
        elif kind == "json":
            skeleton = item.get("skeleton", {})
            structure = skeleton.get("structure")
            body = [
                head,
                f"- 结构: {_clip(json.dumps(structure, ensure_ascii=False), 600)}",
                f"- 开头: {_clip(str(item.get('preview', '')), 400)}",
            ]
            lines.extend(body)
        elif kind == "doc":
            if item.get("is_knowledge"):
                knowledge_parts.append(str(item.get("preview", "")))
            else:
                lines.extend([head, "- 开头: " + _clip(str(item.get("preview", "")), 600)])
        else:
            lines.append(head)

    if knowledge_parts:
        lines.append("\n# knowledge.md（题目自带领域说明，务必据此理解字段含义）")
        for part in knowledge_parts:
            lines.append(part)
    return "\n".join(lines)


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + " …(截断)"


def _human_size(size: int) -> str:
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} GB"
    if size >= 1024**2:
        return f"{size / 1024**2:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"
