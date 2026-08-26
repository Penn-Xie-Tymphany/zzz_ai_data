# 00 · 项目结构总览

> 对象：`code/competitions/kddcup2026-data-agents-starter-kit/PHASE_1/src/data_agent_baseline/`
> 精读日期：2026-08-26（含 8 处本机 DeepSeek 补丁，标注 ⚙️）

## 一图流：一次 run-task 的完整数据流

```
cli.py (run-task 命令, typer+rich)
  └─ load_app_config()          config.py:57    读 YAML → AppConfig
  └─ create_run_output_dir()    runner.py:57    artifacts/runs/<UTC时间戳>/
  └─ run_single_task()          runner.py:194
       └─ _run_single_task_with_timeout()  runner.py:132   ⚙️P4 子进程隔离+超时
            └─ _run_single_task_core()
                 ├─ DABenchPublicDataset.get_task()   dataset.py:58   读 task.json + context/
                 ├─ ReActAgent(...)                   react.py:69
                 │    └─ run(task)                    react.py:97     ★ ReAct 主循环
                 │         ├─ model.complete()        model.py:42     ⚙️P1/P2/P3 调 LLM
                 │         ├─ parse_model_step()      react.py:47     ⚙️P6 解析 JSON
                 │         └─ tools.execute()         registry.py:125 执行工具
                 └─ _write_task_outputs()             runner.py:168   ⚙️P5 写 trace.json/prediction.csv
```

## 模块职责表

| 文件 | 行数级 | 职责 | 精读笔记 |
| --- | --- | --- | --- |
| `benchmark/schema.py` | 56 行 | 数据类定义：PublicTask / AnswerTable / TaskRecord | 本文 |
| `benchmark/dataset.py` | 101 行 | 数据集加载与校验 | 本文 |
| `agents/runtime.py` | 48 行 | StepRecord / AgentRunResult 运行时数据结构 | [01](01-agent-loop.md) |
| `agents/react.py` | 147 行 | **核心**：ReAct 循环 + JSON 协议解析 | [01](01-agent-loop.md) |
| `agents/model.py` | ~90 行 | OpenAI 兼容客户端封装 | [01](01-agent-loop.md) |
| `tools/registry.py` | 193 行 | 8 个工具的注册、描述、分发 | [02](02-tools.md) |
| `tools/filesystem.py` | 87 行 | 文件预览类工具实现（含路径逃逸防护） | [02](02-tools.md) |
| `tools/sqlite.py` | 54 行 | 只读 SQL 工具 | [02](02-tools.md) |
| `tools/python_exec.py` | 146 行 | Python 沙箱执行（子进程+fd 重定向） | [02](02-tools.md) |
| `agents/prompt.py` | 60 行 | 三段式 prompt 构造 | [03](03-prompting.md) |
| `run/runner.py` | 280 行 | 并发调度、超时隔离、产物落盘 | [04](04-evaluation.md) |
| `config.py` / `cli.py` | - | 配置加载 / CLI 入口 | 本文 |

## 设计亮点（初读感受）

1. **极简依赖**：核心逻辑零三方框架（无 langchain），只有 openai/typer/rich/yaml——每个模块都能独立读懂，非常适合学习；
2. **数据类贯穿**：PublicTask → StepRecord → AgentRunResult 全部 frozen dataclass，类型清晰可序列化（`to_dict()` 直接写 trace.json）；
3. **预览哲学**：所有读取类工具都只给"预览"（max_rows=20 / max_chars=4000 + truncated 标志），从设计上防止上下文爆炸；
4. **answer 是唯一出口**：终止权在工具层（`is_terminal=True`），agent 循环本身没有提前退出的歧义。

## 数据集加载的严格性（dataset.py:18-32）

- task.json 必须恰好包含 `{task_id, difficulty, question}` 三个键（:20-26 多一个少一个都报错）
- task_id 必须和目录名一致（:65-66）
- context/ 目录必须存在（:68-70）
- 排序按数字而非字符串（task_2 < task_11，:52）

> 启示：评测型代码要在入口把脏数据全部挡掉，后面才能放心跑。
