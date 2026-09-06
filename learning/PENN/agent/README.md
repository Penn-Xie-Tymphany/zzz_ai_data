# agent — Penn 自研 Data Agent 项目说明

> **是什么**：我的自研 agent（`code/solutions/penn_data_agent/`）的设计、路线与复盘。
> **当前状态**：**v0.3 架构已落地可跑**（Plan-and-Execute + 子 Agent 信息隔离），小批量 5 题 4 满分；官方 REACT 机制拆解已完成，作为设计输入的第一篇文档。代码见 `code/solutions/penn_data_agent/`。

## 已有文档

- [x] [REACT机制拆解.md](REACT机制拆解.md)：**官方 REACT 模型拆解**——代码架构（分层/数据流/主循环）+ 设计取舍 + "任务是怎么被隐性拆解的"，自研各版本（v0.1~四阶段）的改动方向已映射到文末。
- [x] [架构设计.md](架构设计.md)：自研 **P-a-E + 子 Agent 架构**——为什么放弃 ReAct、组件/数据流/控制流、五个关键机制（Recon / Answer Contract / SubAgent / Verifier / 文本 JSON 协议）、代码地图、实测。

## 规划中的文档

- [ ] 设计文：为什么选「文本 JSON + 严格校验 + 重试」而非 Function Calling、工具集怎么选
- [ ] 路线复盘：v0.3 首版实测与官方 ReAct 同模型对照（分数/耗时/失败归因对比）

## 核心参考

- 代码：`code/solutions/penn_data_agent/`
- 路线的设计输入：`../baseline/细节深挖.md`、`../baseline/补丁记录.md`
- 官方 REACT 机制拆解（自研前必读）：`REACT机制拆解.md`
- 版本目标与对标分数：`../00-progress.md`
- 通识基础：`../basics/`

---

> 复现提示：想了解我在做什么，直接看代码目录的 `README.md`。
