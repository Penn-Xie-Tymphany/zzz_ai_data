# penn_data_agent — Penn 的自研 Data Agent

> 目标：从零实现一个能在 DataAgent-Bench demo 上跑通的自研 agent，再逐步叠加改进。
> 不 fork 官方代码，自己写，官方 starter kit 仅作参照与评测对照。

> 设计输入来自 baseline 跑通实测，详见 `learning/PENN/baseline/补丁记录.md` 的"启示"一节。

## 版本路线

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

目标：v0.1 对齐官方 → v0.3+ 冲 0.55+。完整目标阶梯见 `learning/PENN/00-progress.md`。

## 目录规划（随实现逐步充实）

```
penn_data_agent/
├── README.md            # 本文件
├── pyproject.toml       # 依赖管理
├── src/
│   └── penn_data_agent/
│       ├── __init__.py
│       ├── agent.py         # Agent 主循环（v0.1）
│       ├── llm.py           # LLM 后端封装（OpenAI 兼容 API）
│       ├── schema.py        # 任务/资产/公开任务/答案表 dataclass（官方移植）
│       ├── tools/           # 可复用工具层（官方移植）
│       │   ├── __init__.py  # 导出 create_default_tool_registry 等
│       │   ├── filesystem.py    # list_context / read_csv|json|doc
│       │   ├── sqlite.py        # inspect_sqlite_schema / execute_read_only_sql
│       │   ├── python_exec.py   # execute_python_code（子进程沙箱）
│       │   └── registry.py      # ToolSpec / ToolRegistry / 默认注册
│       └── protocol.py      # ReAct JSON 输出协议的约束与解析
├── prompts/
│   └── system.md            # system prompt 模板
├── scripts/
│   └── run_task.py          # 单题运行入口
└── tests/
    ├── __init__.py
    └── test_official_tools.py   # 官方工具层冒烟测试
```

## 官方工具层移植

`schema.py` 与 `tools/` 下的 filesystem / sqlite / python_exec / registry **直接移植自官方 starter kit**（KDD Cup 2026 DataAgent-Bench，`PHASE_1/data_agent_baseline` 的 `benchmark/schema.py` 与 `tools/`）。每个源文件模块 docstring 顶部都标注了来源、官方原始相对路径、用途，说明"基于官方代码直接移植（含 import 适配与注释），非自研新代码"。

**移植范围**：只抽取无三方依赖、纯标准库的工具层（registry 依赖链仅涉及 schema 与其余三个 tool 模块），不含官方主循环、LLM 调用与评测逻辑。

**import 适配方式**：官方内部用绝对包名 `data_agent_baseline.*` 引用，移植后统一改为自研包内相对导入，保证复制到其它宿主目录也不依赖包名注册：

| 文件 | 官方 import | 移植后 import |
| --- | --- | --- |
| filesystem.py | `from data_agent_baseline.benchmark.schema import PublicTask` | `from ..schema import PublicTask` |
| registry.py | `from data_agent_baseline.benchmark.schema import ...` 等 | `from ..schema import ...` / `from .filesystem import ...` 等 |
| sqlite.py / python_exec.py | 无内部依赖 | 原样 |

`tools/__init__.py` 从 registry 再导出 `create_default_tool_registry` / `ToolRegistry` / `ToolSpec` / `ToolExecutionResult`，支持最常用入口 `from penn_data_agent.tools import create_default_tool_registry`。`schema.py` 暴露 `TaskRecord / TaskAssets / PublicTask / AnswerTable` 四个 dataclass。

**一处必要健壮性修补**：sqlite 工具官方用 `with sqlite3.connect(...) as conn`，那只会自动 commit/rollback 而**不会 close** 连接；Windows 下连接句柄不释放会导致 db 文件占用（临时目录无法清理）。移植时改用 `contextlib.closing` 显式关闭，行为语义不变。

**验证**：`py -c "...create_default_tool_registry..."` 可解析 8 个工具（answer / execute_context_sql / execute_python / inspect_sqlite_schema / list_context / read_csv / read_doc / read_json）；`py tests/test_official_tools.py` 通过 7 个冒烟用例（不触发真实 python 子进程沙箱）。可运行命令见 `tests/test_official_tools.py` 顶部注释。

**与 v0.1 的关系**：v0.1 主线是用 Function Calling 替代官方自由文本 JSON 主循环（`protocol.py` / `agent.py`）。本移植工具层**先落地为独立可复用层**（v0.2 工具增强可在此之上扩展：schema 摘要、observation 截断、文档分块读取、输出守卫）；待 v0.1 用 Function Calling 重写主循环时，将把 `create_default_tool_registry` 的 8 个工具声明成 function-call tools，仅替换调用入口、不重写工具实现。
