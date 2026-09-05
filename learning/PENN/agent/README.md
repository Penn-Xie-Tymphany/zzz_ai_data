# agent — Penn 自研 Data Agent 项目说明

> **是什么**：我的自研 agent（`code/solutions/penn_data_agent/`）的设计、路线与复盘。
> **当前状态**：代码骨架已建（v0.1 进行中）；官方 REACT 模型已完成机制拆解，作为设计输入的第一篇文档。

## 已有文档

- [x] [react-teardown.md](react-teardown.md)：**官方 REACT 模型拆解**——代码架构（分层/数据流/主循环）+ 设计取舍 + "任务是怎么被隐性拆解的"，自研各版本（v0.1~四阶段）的改动方向已映射到文末。

## 规划中的文档

- [ ] 设计文：为什么用 Function Calling、工具集怎么选（v0.1 落笔时补）
- [ ] 架构文：自研 agent 的组件 / 数据流 / 控制流
- [ ] 路线复盘：v0.1~v0.5 每版的取舍与实测对比

## 核心参考

- 代码：`code/solutions/penn_data_agent/`
- 路线的设计输入：`../baseline/deep-dive.md`、`../baseline/patches.md`
- 官方 REACT 机制拆解（自研前必读）：`react-teardown.md`
- 版本目标与对标分数：`../00-progress.md`
- 通识基础：`../basics/`

---

> 复现提示：想了解我在做什么，直接看代码目录的 `README.md`。
