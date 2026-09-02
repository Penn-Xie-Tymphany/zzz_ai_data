# basics — 跨项目通识知识

> 这里放**跟本项目解耦的通识**：去掉 KDD 背景依然成立的知识（ReAct / LLM 上下文 / token / 并发…）。
> 判断标准：一句话，拿去其他 AI 项目也成立 → 放这里。

## 推荐阅读顺序（文件名编号即推荐顺序）

| # | 主题 | 文件 | 状态 |
| --- | --- | --- | --- |
| 01 | ReAct 范式：Reasoning + Acting 循环 | [01-react.md](01-react.md) | ✅ |
| 02 | LLM 上下文机制：无状态 / messages 重发 / KV Cache / Token 计费 | [02-how-llm-context-works.md](02-how-llm-context-works.md) | ✅ |
| 03 | 采样参数：temperature / max_tokens 与随机性真相 | [03-sampling-and-parameters.md](03-sampling-and-parameters.md) | ✅ |
| 04 | Function Calling：服务端保证结构合法 | [04-function-calling.md](04-function-calling.md) | ✅ |
| 05 | Python 并发基础：GIL / 线程 vs 进程 / Queue 死锁 | [05-python-concurrency-basics.md](05-python-concurrency-basics.md) | ✅ |

## 备查资料（按需翻看）

| 主题 | 文件 |
| --- | --- |
| KDD Cup 2026 比赛规则与赛制 | [competition-overview.md](competition-overview.md) |
| 任务的人类视角白话解释 | [task-walkthrough.md](task-walkthrough.md) |
| 高分开源方案收藏夹 | [resources.md](resources.md) |

> 顺序说明：01~05 是"读任何 agent 源码前的地基"；备查三篇涉及具体比赛背景，不进编号。