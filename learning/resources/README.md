# 外部资源收藏（resources/）

> 收藏格式：`[标题](链接) — 一句话说明它为什么值得看`

## 官方

- [比赛官网](https://dataagent.top/) — 规则、Benchmark 介绍、数据集下载入口
- [官方 Starter Kit](https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit) — ReAct baseline + dataset loader + CLI

## 高分参赛方案开源仓库 ⭐（重点学习材料）

- [kekshibata / 4th-place-solution](https://github.com/kekshibata/kddcup2026-data-agents-4th-place-solution) — **Phase 1 冠军 + Phase 2 第 4 名**完整开源：181 个实验包、139 commits 全历史保留，含失败方案；核心是 PLAN→EXPLORE→ANSWER→VERIFY 四阶段 ReAct + 确定性门控。**最值得精读的一份。**
- [Kosthi / kddcup2026-dataagents](https://github.com/Kosthi/kddcup2026-dataagents) — Phase 1 第 9 名（703 队）"Mamba Agent"，ReAct 改造，结构清晰适合对照学习
- [BrightLiao / KDDCupDataAgent](https://github.com/BrightLiao/KDDCupDataAgent) — 中文复盘仓库，含 baseline 实测数据（micro 0.376）与逐题轨迹分析
- [xyma2003 / kdd-cup](https://github.com/xyma2003/kdd-cup) — 参赛复盘，记录了 baseline ~16% perfect 率 vs 自研 32/50 的对比

## 论文

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — baseline 的核心范式，必读

## 博客 / 复盘

- （待补充：Discord/社区里发现的优质复盘）

## 工具库

- [uv](https://docs.astral.sh/uv/) — starter kit 使用的 Python 包管理器
