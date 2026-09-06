"""提示词模板加载（模板文件放在项目根 `prompts/`）。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# src/penn_data_agent/prompting.py → parents[2] = 项目根
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    path = PROMPT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"缺少提示词模板: {path}")
    return path.read_text(encoding="utf-8")
