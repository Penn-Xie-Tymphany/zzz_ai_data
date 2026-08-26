# 基础知识学习笔记（basics/）

一个主题一个文件，按编号排序。**优先级标注：读源码/做自研前必须先看的会标 ⭐。**

| # | 主题 | 文件 | 状态 |
| --- | --- | --- | --- |
| 01 | ReAct 范式：Reasoning + Acting 循环 | `01-react.md` | ✅（结合官方 react.py 实讲） |
| 02 | ⭐ LLM 上下文机制：无状态/messages 重发/KV Cache/Token 计费 | `02-how-llm-context-works.md` | ✅ |
| 03 | ⭐ 采样参数：temperature/max_tokens 与随机性真相 | `03-sampling-and-parameters.md` | ✅ |
| 04 | ⭐ Function Calling：服务端保证结构合法（v0.1 核心升级） | `04-function-calling.md` | ✅ |
| 05 | Python 并发基础：GIL/线程vs进程/Queue 死锁教训 | `05-python-concurrency-basics.md` | ✅ |
| 06 | Text-to-SQL：schema linking、执行反馈修正 | `06-text2sql.md` | ☐（medium 题核心技能） |
| 07 | 非结构化文档理解（长上下文、检索/分块） | `07-document-understanding.md` | ☐（hard/extreme 核心） |
| 08 | Agent 设计模式：规划(DAG)、反思、多智能体 | `08-agent-patterns.md` | ☐ |
| 09 | 沙箱执行与安全 | `09-sandbox.md` | ◐（baseline-study/02-tools.md 已覆盖大半） |

## 阅读建议

刚入门按编号读 01→05（都是结合本项目代码/实测写的，不是抽象教科书）；
06~08 在攻对应难度题目时再补。

## 笔记模板

```markdown
# 0X · 主题名
> 是什么 / 为什么重要 / 和比赛的关联

## 核心概念
## 关键机制（配伪代码或图）
## 在官方 baseline 中如何体现（文件:行号）
## 我的思考与疑问
```
