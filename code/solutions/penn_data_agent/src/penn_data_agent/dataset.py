"""任务数据加载：把磁盘上的 task.json + context 目录装配成 PublicTask。

自研实现（对齐官方 `benchmark/dataset.py` 的最小子集）：
- 输入根（input_root）下每个 `task_XX/` 含 `task.json` 与 `context/`；
- gold 根（output_root）下每个 `task_XX/gold.csv` 为标准答案，仅本地评分时读取。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .schema import PublicTask, TaskAssets, TaskRecord


def load_task(input_root: Path, task_id: str) -> PublicTask:
    task_dir = input_root / task_id
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    return PublicTask(
        record=TaskRecord(
            task_id=meta.get("task_id", task_id),
            difficulty=str(meta.get("difficulty", "")),
            question=str(meta.get("question", "")),
        ),
        assets=TaskAssets(task_dir=task_dir, context_dir=task_dir / "context"),
    )


def iter_task_ids(input_root: Path, difficulty: str = "") -> list[str]:
    """列出全部（或指定难度的）task id，保持数字序。"""
    items: list[tuple[int, str]] = []
    for child in input_root.iterdir():
        if not child.is_dir() or not child.name.startswith("task_"):
            continue
        if difficulty:
            meta_path = child / "task.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if str(meta.get("difficulty", "")) != difficulty:
                continue
        try:
            number = int(child.name.split("_", 1)[1])
        except (IndexError, ValueError):
            number = 0
        items.append((number, child.name))
    return [name for _, name in sorted(items)]


def load_gold(output_root: Path, task_id: str) -> tuple[list[str], list[list[str]]] | None:
    path = output_root / task_id / "gold.csv"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.reader(handle) if any(c.strip() for c in r)]
    if not rows:
        return None
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows[0], rows[1:]


def write_prediction(target_dir: Path, columns: list[str], rows: list[list]) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "prediction.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
    return path
