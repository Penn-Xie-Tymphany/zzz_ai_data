# 基础知识学习笔记（basics/）

一个主题一个文件，按编号排序。建议顺序：

| # | 主题 | 文件 | 状态 |
| --- | --- | --- | --- |
| 01 | ReAct 范式：Reasoning + Acting 循环 | `01-react.md` | ✅（结合官方 react.py 实讲） |
| 02 | Function Calling 与 JSON 输出协议 | `02-function-calling.md` | ☐（v0.1 自研前置，重点） |
| 03 | Text-to-SQL：schema linking、执行反馈修正 | `03-text2sql.md` | ☐（medium 题核心技能） |
| 04 | 非结构化文档理解（PDF/DOCX 解析、长上下文） | `04-document-understanding.md` | ☐（hard/extreme 核心） |
| 05 | Agent 设计模式：规划(DAG)、反思、多智能体 | `05-agent-patterns.md` | ☐ |
| 06 | 沙箱执行与安全：Python/SQL 执行环境隔离 | `06-sandbox.md` | ◐（02-tools.md 已覆盖大半） |

## 笔记模板

```markdown
# 0X · 主题名
> 是什么 / 为什么重要 / 和比赛的关联

## 核心概念
## 关键机制（配伪代码或图）
## 在官方 baseline 中如何体现（文件:行号）
## 我的思考与疑问
```
