# my-data-agent — 自研 Data Agent

> 目标：从零实现一个能在 DataAgent-Bench demo 上跑通的自研 agent，再逐步叠加改进。
> 不 fork 官方代码，自己写，官方 starter kit 仅作参照与评测对照。

## 版本路线

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.1 | 最小 ReAct loop：LLM + 工具调用 + JSON 协议解析，端到端跑通 1 个 task | ☐ |
| v0.2 | 工具增强：schema 摘要、文档分块读取、执行结果截断策略 | ☐ |
| v0.3 | 显式任务分解：先产出 DAG 计划（并行子任务 + 汇合），再逐节点执行 | ☐ |
| v0.4 | 自我反思：SQL/Python 报错自动查 schema、数据清洗重试、答案自校验 | ☐ |
| v0.5 | 评测驱动迭代：失败 case 归因 → 针对性优化 prompt / 工具 / 规划 | ☐ |

## 目录规划（随实现逐步充实）

```
my-data-agent/
├── README.md            # 本文件
├── pyproject.toml       # 依赖管理
├── src/
│   └── my_data_agent/
│       ├── __init__.py
│       ├── agent.py         # Agent 主循环（v0.1）
│       ├── llm.py           # LLM 后端封装（OpenAI 兼容 API）
│       ├── tools/           # 工具注册与实现
│       │   └── __init__.py
│       └── protocol.py      # ReAct JSON 输出协议的约束与解析
├── prompts/
│   └── system.md            # system prompt 模板
├── scripts/
│   └── run_task.py          # 单题运行入口
└── tests/
    └── __init__.py
```
