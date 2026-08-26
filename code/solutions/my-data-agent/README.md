# my-data-agent — 自研 Data Agent

> 目标：从零实现一个能在 DataAgent-Bench demo 上跑通的自研 agent，再逐步叠加改进。
> 不 fork 官方代码，自己写，官方 starter kit 仅作参照与评测对照。

## 版本路线

> 设计输入来自 baseline 跑通实测，详见 `learning/baseline-study/01-patches-for-deepseek.md` 的"启示"一节。

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.1 | 最小 ReAct loop：**用 Function Calling 替代自由文本 JSON**（服务端保证结构合法，直接消灭官方 baseline 的 6 类解析故障），端到端跑通 task_11 对齐官方成绩 | ☐ |
| v0.2 | 工具增强：schema 摘要、observation 截断/摘要（官方回灌 17 步膨胀到 15K tokens）、文档分块读取、输出守卫（列数校验防 Extra Columns 罚分） | ☐ |
| v0.3 | 显式任务分解：先产出 DAG 计划（并行子任务 + 汇合），再逐节点执行；参考冠军方案 PLAN→EXPLORE→ANSWER→VERIFY 四阶段 + 确定性门控 | ☐ |
| v0.4 | 自我反思：SQL/Python 报错自动查 schema、数据清洗重试、答案自校验（VERIFY 阶段独立化） | ☐ |
| v0.5 | 评测驱动迭代：50 题全量跑分 vs 官方基线对比，失败 case 归因 → 针对性优化 | ☐ |

## 对标基准

| 参照 | 分数 |
| --- | --- |
| 官方裸 baseline（demo 实测） | micro ≈ 0.376 |
| Phase 1 冠军 KOBUSHI | A-board 0.5965 / hidden B-board 0.6812 |

目标：v0.1 对齐官方 → v0.3+ 冲 0.55+。完整目标阶梯见 `learning/competition-notes/02-progress-and-targets.md`。

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
