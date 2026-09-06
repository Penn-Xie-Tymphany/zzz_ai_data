"""自研 penn_data_agent（Plan-and-Execute + 子 Agent 隔离）。

分层（自下而上）：
    config / llm / jsonio   基建：配置、模型后端、文本 JSON 协议（抽取+校验+重试）
    schema / tools          领域模型与工具层（移植自官方 starter kit）
    dataset / recon         任务加载、context 确定性侦察（零 LLM）
    planner                 题目要素分解 + 答案契约 + 子任务列表 + 规则校验
    worker                  子 Agent：一个子任务一个独立上下文的 ReAct 执行器
    composer / verifier     按契约拼表 / fail-closed 输出门禁
    orchestrator            Plan-and-Execute 主编排（含 replan 与降级）
    runner                  批量跑分 + 官方同口径评分
"""

from .config import AgentConfig, BudgetConfig, ContextConfig, LLMConfig, RunConfig
from .orchestrator import AgentOutcome, PlanExecuteAgent
from .planner import AnswerContract, Plan, Planner, SubTask
from .worker import SubAgent, WorkerResult

__all__ = [
    "AgentConfig",
    "BudgetConfig",
    "ContextConfig",
    "LLMConfig",
    "RunConfig",
    "PlanExecuteAgent",
    "AgentOutcome",
    "Planner",
    "Plan",
    "SubTask",
    "AnswerContract",
    "SubAgent",
    "WorkerResult",
]

__version__ = "0.3.0"
