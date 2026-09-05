# 进度与目标总控（持续更新）

> **这份文档回答三个问题：现在做了什么？还需要做什么？要优化到什么程度？**
> 每次重大进展后更新本文件。最后更新：2026-09-06

> 🎯 **当前目标（2026-09-05 起）**：只参加 **Phase 1**（单一主赛道公共榜）并尽量拿高分。
> Phase 2 的 Leaderboard Subtrack（图像/视频新模态）与 Creative Subtrack **均不参加**
> （视频多模态赛道做不了）；`PHASE_2/` 官方源码已从仓库删除，相关文档仅作背景存档。

---

## 一、已经做了什么（时间线）

| 日期 | 里程碑 | 产出 |
| --- | --- | --- |
| 08-25 | 工作区框架搭建（learning/PENN + code 双区结构） | git 初始提交，GitHub 同步 |
| 08-25 | 比赛调研：规则/评分/难度分级整理 | [basics/比赛总览.md](basics/比赛总览.md) |
| 08-25 | 官方 starter kit 克隆 + uv 环境 | PHASE_1 可运行 |
| 08-25 | Phase 1 demo 数据集落地（50 题） | `dabench status` 验证通过 |
| 08-25 | SSH key + GitHub 仓库推送 | github.com/Penn-Xie-Tymphany/zzz_ai_data |
| 08-26 | DeepSeek 接入 + **8 处兼容补丁**（死锁/编码/JSON 解析等） | [baseline/补丁记录.md](baseline/补丁记录.md) |
| 08-26 | **官方 baseline 单题跑通：task_11 答案与 gold 完全一致**（22 步/72s） | 详细复盘已并入本文档时间线 |
| 08-27 | 源码精读五篇（结构/主循环/工具/prompt/评测） | 已整合进 [baseline/](baseline/README.md) |
| 09-02 | 切到阿里云百炼 qwen3.8-flash（开箱即用、无速率限制） | task_11 17 步全对 |
| 09-02 | 目录重构：learning → `PENN/`（baseline/agent/basics 三分区） | 本仓库当前结构 |
| 09-05 | **官方 REACT 模型机制拆解**（代码架构/设计取舍/任务隐性拆解 + 自研映射） | [agent/REACT机制拆解.md](agent/REACT机制拆解.md) |
| 09-05 | PENN 学习文档文件名中文化（内容文档改中文名，UTF-8，同步全部交叉引用） | [PENN 总入口](README.md) |
| 09-06 | 目标收敛落库：删除 PHASE_2 官方源码（25 文件），文档统一口径「只打 Phase 1」 | 提交 907565e |
| 09-06 | **官方同口径本地评分器落地**（列签名匹配 + λ 罚分、上限防作弊、18 条单测） | [evaluation/](../../code/competitions/evaluation/)，提交 5cf4500 |
| 09-06 | **评分器融合 benchmark**：`run-benchmark` 跑完自动出分（明细写 `evaluation_report.json`）+ 新增 `dabench evaluate` 复盘历史 run（不调模型） | PHASE_1 本地补丁 + README 同步 |
| 09-06 | 用历史 run 交叉验证：`evaluate` 与独立 `scoring.py` 同参数结果完全一致（submitted 6 题 mean 0.6667、perfect 4） | 链路闭环验证通过 |

## 二、还需要做什么（按优先级）

### 近期（本周）— 把 baseline 的底摸清

- [x] **官方同口径本地评分闭环**（评分器 + `run-benchmark` 自动出分 + `dabench evaluate` 复盘）——已具备，跑分随时可出报告
- [ ] **小批量验证**：`run-benchmark --limit 5`（easy 题），确认链路稳定、观察通过率（跑完即自动出分）
- [ ] **全量 50 题跑分**：得到我们环境下的 baseline 基线分（micro/macro/perfect 数），报告自动落在 run 目录 `evaluation_report.json`
- [ ] **失败 case 归因**：按难度分层统计，每题记录"挂在哪一步"（解析？工具？推理？步数？）
- [ ] 精读笔记查漏补缺（架构层已梳理完，细节随用随补）

### 中期（1~2 周）— 自研 agent 迭代

- [ ] penn_data_agent v0.1：脱离官方代码复刻最小 ReAct loop（用 Function Calling 替代自由文本 JSON —— 直接消灭官方 6 类解析故障）
- [ ] v0.2 工具增强：schema 摘要、observation 截断策略（上下文线性膨胀问题）、文档分块读取
- [ ] v0.3 显式规划：先产出计划再执行
- [ ] 对照实验：同一批题，自研 vs 官方 baseline 分数对比

### 远期（持续）— 向高分架构演进

- [ ] 借鉴冠军方案的 **PLAN→EXPLORE→ANSWER→VERIFY 四阶段架构**（见第 3 节）
- [ ] 确定性门控（不信任模型自律）：EXPLORE 达标前禁止 ANSWER、答案形状校验、fail-closed 输出守卫
- [ ] 难度专项：medium(Text-to-SQL 多源)、hard/extreme(长文档推理) 各自的针对性策略

## 三、要优化到什么程度（参考基准与目标）

### 评分机制回顾（官方口径，详见 `code/competitions/evaluation/`）

`Score = max(0, Recall − λ × (Extra Columns / Predicted Columns))`，λ=0.5（复现口径，官方只公开符号 λ）。
列按**内容签名**匹配（值归一化后多重集，忽略列名/行序/列序，一对一），负分截 0。
**含义：答案宁缺勿滥——多给的列会被罚；少给列只损失 recall。**
> 本地已实现官方同口径评分器 `code/competitions/evaluation/`，并融合进 starter-kit：
> `run-benchmark` 跑完自动出分（明细写入 `artifacts/runs/<run_id>/evaluation_report.json`），
> 复盘历史 run 用 `uv run dabench evaluate <run_id> --config <yaml>`（不调模型）；独立 CLI 仍可用 `--lam` 调 λ。

### 外部参照系（真实数据）

| 参照 | 成绩 | 来源 |
| --- | --- | --- |
| 官方裸 baseline（ReAct，强模型后端） | demo 上 micro ≈ **0.376**；有参赛者实测 perfect 率仅 ~16% | BrightLiao/xyma2003 复盘仓库 |
| **Phase 1 冠军**（Team KOBUSHI） | A-board **0.5965** / B-board(hidden) **0.6812** / Final **0.6685**，1/700+ 队 | kekshibata 开源仓库 |
| Phase 1 第 9 名 | Mamba Agent（ReAct 改造版） | Kosthi 开源仓库 |
| 冠军关键架构 | **PLAN→EXPLORE→ANSWER→VERIFY 四阶段** + 确定性阶段门控 + 按阶段裁剪工具可见性 + fail-closed 输出守卫 | 同上 |

> 冠军队细节值得深挖：他们用被指定的 Qwen3.5-35B-A3B（非顶级闭源模型）+ 16 CPU 无 GPU，
> 说明**架构和工程比模型 brute-force 更重要**——这正是本比赛的学习价值所在。

### 我们的目标阶梯

| 阶段 | 目标 | 验收标准 |
| --- | --- | --- |
| G1 ✅ | 跑通单题 | task_11 全对（已达成） |
| G2 | 摸清基线 | 50 题全量跑分，得到自己环境的 baseline 分数曲线 |
| G3 | 不低于官方 baseline | 自研 v0.x 在 demo 上 ≥ 官方裸 baseline（≈0.376 或实测值） |
| G4 | 进入优秀区间 | demo ≥ **0.55~0.60**（相当于 Phase 1 冠军 A-board 水平） |
| G5 | 极限挑战 | hidden-set 思维：抗干扰文档、fail-closed 设计（视频模态不做——Phase 2 不在范围） |

### 优化方向的优先级判断（基于评分公式）

1. **减少 Extra Columns 罚分** > 提升 Recall：输出守卫（列数/形状校验）是性价比最高的改动；
2. easy→medium→hard 逐层攻克：easy 是纯代码生成，medium 加 Text-to-SQL，hard 考长文档——先保证低难度题零失误；
3. 步数预算与上下文管理是工程瓶颈（observation 回灌线性膨胀，17 步已 15K tokens）。

## 四、相关资源索引

- 高分开源方案（学习材料）：[basics/参考资源收藏.md](basics/参考资源收藏.md)
- 环境与跑法：`baseline/运维实操.md`；DeepSeek 补丁：`baseline/补丁记录.md`
- 本地评分器（官方同口径，对比排行榜/基线用）：`code/competitions/evaluation/`；已融合 `run-benchmark` 自动出分