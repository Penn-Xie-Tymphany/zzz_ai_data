"""运行配置：模型后端、各阶段预算、上下文治理参数。

自研 penn_data_agent 的配置层，**不依赖官方 starter kit**。

配置来源优先级：
1. 命令行 `--config <yaml>`（可直接复用官方 `configs/*.yaml`，含 api_key，本地文件不入库）；
2. 环境变量 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`；
3. 代码内默认值。

只解析「两层缩进 + key: value」的极简 YAML，避免为了读配置引入三方依赖。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 默认后端：阿里云百炼兼容模式（与官方 configs/qwen36_flash.yaml 同端点）
DEFAULT_MODEL = "qwen3.6-flash"
DEFAULT_TEMPERATURE = 0.0


@dataclass(slots=True)
class LLMConfig:
    """模型后端配置。api_key 只从环境或本地 yaml 读取，禁止硬编码。"""

    model: str = DEFAULT_MODEL
    api_base: str = ""
    api_key: str = ""
    temperature: float = DEFAULT_TEMPERATURE
    timeout_seconds: int = 180
    max_retries: int = 2  # 网络层重试（非协议重试）


@dataclass(slots=True)
class BudgetConfig:
    """各阶段的步数 / 重试预算。"""

    planner_retries: int = 2          # Planner 输出不合规时的重解析次数
    max_subtasks: int = 6             # 单个计划允许的子任务上限
    min_subtasks: int = 1
    worker_max_steps: int = 8         # 单个子 agent 的最大工具步数
    worker_total_steps: int = 36      # 一道题所有子 agent 的步数总预算
    replan_budget: int = 1            # Verifier 不通过时允许重规划的次数
    composer_retries: int = 2
    verifier_retries: int = 1


@dataclass(slots=True)
class ContextConfig:
    """上下文治理：observation 截断与环境卡片体积。"""

    observation_max_chars: int = 3000   # 单条 observation 回灌上限（治 413 与线性膨胀）
    keep_recent_observations: int = 3   # 超过该步数后，早期 observation 折叠为一行摘要
    env_card_max_files: int = 60
    csv_preview_rows: int = 3
    csv_header_chars: int = 600
    doc_preview_chars: int = 1200
    knowledge_chars: int = 3000         # knowledge.md 是每题自带的领域说明，优先全量给 Planner
    json_preview_chars: int = 800
    max_rowcount_file_bytes: int = 50 * 1024 * 1024  # 超过该体积不精确统计行数


@dataclass(slots=True)
class RunConfig:
    """批量跑分相关。"""

    output_dir: Path = Path("artifacts/runs")
    max_workers: int = 1
    task_timeout_seconds: int = 1800
    difficulty: str = ""
    limit: int = 0
    dataset_root: str = ""  # 官方 yaml 里的 dataset.root_path（相对路径，仅供参考）


@dataclass(slots=True)
class AgentConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    run: RunConfig = field(default_factory=RunConfig)


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """解析极简 YAML：支持 `key: value`、两空格缩进的二级分组、`#` 注释。"""
    result: dict[str, Any] = {}
    current_group: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if line.startswith(" ") or line.startswith("\t"):
            if current_group is None:
                continue
            key, _, value = stripped.partition(":")
            current_group[key.strip()] = _coerce(value.strip())
        else:
            key, _, value = stripped.partition(":")
            key = key.strip()
            if value.strip() == "":
                current_group = {}
                result[key] = current_group
            else:
                current_group = None
                result[key] = _coerce(value.strip())
    return result


def _coerce(value: str) -> Any:
    if value in ("", '""', "''"):
        return ""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip("'\"")


def config_from_yaml(path: Path) -> AgentConfig:
    """从（官方格式的）yaml 构建配置；api_key 优先取 yaml，其次环境变量。"""
    import os

    data = parse_simple_yaml(path.read_text(encoding="utf-8"))
    agent_section = data.get("agent", {}) or {}
    run_section = data.get("run", {}) or {}
    dataset_section = data.get("dataset", {}) or {}

    llm = LLMConfig(
        model=str(agent_section.get("model") or os.environ.get("LLM_MODEL") or DEFAULT_MODEL),
        api_base=str(agent_section.get("api_base") or os.environ.get("LLM_BASE_URL") or ""),
        api_key=str(agent_section.get("api_key") or os.environ.get("LLM_API_KEY") or ""),
        temperature=float(agent_section.get("temperature", DEFAULT_TEMPERATURE)),
    )
    run = RunConfig(
        output_dir=Path(run_section.get("output_dir", "artifacts/runs")),
        max_workers=int(run_section.get("max_workers", 1)),
        task_timeout_seconds=int(run_section.get("task_timeout_seconds", 1800)),
        dataset_root=str(dataset_section.get("root_path", "")),
    )
    return AgentConfig(llm=llm, run=run)


def default_config() -> AgentConfig:
    """纯环境变量 / 默认值构建配置。"""
    import os

    llm = LLMConfig(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        api_base=os.environ.get("LLM_BASE_URL", ""),
        api_key=os.environ.get("LLM_API_KEY", ""),
    )
    return AgentConfig(llm=llm)
