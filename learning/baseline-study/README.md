# 官方 Baseline 源码精读（baseline-study/）

> 对象：`code/competitions/kddcup2026-data-agents-starter-kit/`
> 方法：边读边记，所有结论必须带 `文件路径:行号`，方便回跳。
>
> ⚠️ 先读 [01-patches-for-deepseek.md](01-patches-for-deepseek.md)：我们为接 DeepSeek 打了 8 处补丁，
> 精读时注意区分"官方原逻辑"与"本机修改"。

## 精读清单

| # | 模块 | 要回答的问题 | 文件 | 状态 |
| --- | --- | --- | --- | --- |
| 01 | 项目结构总览 | 入口在哪？数据怎么加载？CLI 怎么用？ | `00-project-structure.md` | ☐ |
| 02 | Agent 主循环 | thought→action→observation 如何驱动？何时终止？ | `01-agent-loop.md` | ☐ |
| 03 | 工具系统 | 每个工具的输入/输出协议？工具结果如何截断回灌？ | `02-tools.md` | ☐ |
| 04 | Prompt 工程 | system prompt 结构？JSON 输出协议如何约束与解析容错？ | `03-prompting.md` | ☐ |
| 05 | 评测流程 | multiset 列比对实现？micro/macro 计算？罚分逻辑？ | `04-evaluation.md` | ☐ |

## 通用笔记模板

```markdown
# 0X · 模块名
## 职责一句话
## 关键代码走读（带 文件:行号）
## 数据流（上游是谁 / 下游是谁）
## 设计亮点
## 可改进点（→ 自研方案的改进项）
```
