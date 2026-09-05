"""数据 schema：任务记录/资产/公开任务/答案表 四个数据类。

# 来源：官方 KDD Cup 2026 DataAgent-Bench starter kit（PHASE_1/data_agent_baseline）
# 路径：benchmark/schema.py ｜ 用途：自研 penn_data_agent 可复用工具层
# 基于官方代码直接移植（含 import 适配与注释），非自研新代码
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    difficulty: str
    question: str


@dataclass(frozen=True, slots=True)
class TaskAssets:
    task_dir: Path
    context_dir: Path


@dataclass(frozen=True, slots=True)
class PublicTask:
    record: TaskRecord
    assets: TaskAssets

    @property
    def task_id(self) -> str:
        return self.record.task_id

    @property
    def difficulty(self) -> str:
        return self.record.difficulty

    @property
    def question(self) -> str:
        return self.record.question

    @property
    def task_dir(self) -> Path:
        return self.assets.task_dir

    @property
    def context_dir(self) -> Path:
        return self.assets.context_dir


@dataclass(frozen=True, slots=True)
class AnswerTable:
    columns: list[str]
    rows: list[list[Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": list(self.columns),
            "rows": [list(row) for row in self.rows],
        }
