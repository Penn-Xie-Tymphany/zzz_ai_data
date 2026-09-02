# baseline 学习索引

> 目标：看懂官方 starter kit"是怎么跑起来的"，为自研 agent 提供参照。
> 阅读原则：**先架构层，再细节**。架构讲不清楚的才去 `deep-dive.md`。

| 文件 | 讲什么 | 读者 |
| --- | --- | --- |
| [architecture.md](architecture.md) | **必读**。整体架构、数据流、控制流（全 Mermaid） | 所有人 |
| [deep-dive.md](deep-dive.md) | 架构层讲不清的细节：主循环 / 工具 / 提示词 / 评测，自上而下 | 想做自研时 |
| [ops.md](ops.md) | 运维实操：环境配置、单题跑法、跑分、看产物 | 要动手跑时 |
| [patches.md](patches.md) | 本机为接 DeepSeek 打的补丁（重克隆必读） | 重搭环境时 |

## 卡片速览

- **一句话**：官方 baseline 是一个"零框架"的 ReAct agent，用 8 个工具 + LLM 逐题推理，产出 `prediction.csv`。
- **架构**：思考简单、工具强劲、评测独立。见 architecture.md 的三张图。
- **成绩**：demo 实测 micro≈0.376；推理越强模型，分越高。

---

> 建议顺序：`architecture.md` 一遍 → 想动手跑就看 `ops.md` → 想自研就看 `deep-dive.md`。
