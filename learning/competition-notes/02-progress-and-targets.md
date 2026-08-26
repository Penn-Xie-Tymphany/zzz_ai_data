# 02 · 进度与目标总控（持续更新）

> **这份文档回答三个问题：现在做了什么？还需要做什么？要优化到什么程度？**
> 每次重大进展后更新本文件。最后更新：2026-08-26

---

## 一、已经做了什么（时间线）

| 日期 | 里程碑 | 产出 |
| --- | --- | --- |
| 08-25 | 工作区框架搭建（learning/ + code/ 双区结构） | git 初始提交，GitHub 同步 |
| 08-25 | 比赛调研：规则/评分/难度分级整理 | [01-competition-overview.md](01-competition-overview.md) |
| 08-25 | 官方 starter kit 克隆 + uv 环境 | PHASE_1 可运行 |
| 08-25 | Phase 1 demo 数据集落地（50 题） | `dabench status` 验证通过 |
| 08-25 | SSH key + GitHub 仓库推送 | github.com/Penn-Xie-Tymphany/zzz_ai_data |
| 08-26 | DeepSeek 接入 + **8 处兼容补丁**（死锁/编码/JSON 解析等） | [补丁记录](../baseline-study/01-patches-for-deepseek.md) |
| 08-26 | **官方 baseline 单题跑通：task_11 答案与 gold 完全一致**（22 步/72s） | [实验日志](../experiments-log/2026-08-26-first-baseline-task.md) |

## 二、还需要做什么（按优先级）

### 近期（本周）— 把 baseline 的底摸清

- [ ] **小批量验证**：`run-benchmark --limit 5`（easy 题），确认链路稳定、观察通过率
- [ ] **全量 50 题跑分**：得到我们环境下的 baseline 基线分（micro/macro/perfect 数）
- [ ] **失败 case 归因**：按难度分层统计，每题记录"挂在哪一步"（解析？工具？推理？步数？）
- [ ] 精读 baseline 源码四模块（[精读清单](../baseline-study/README.md)），补齐 00~04 笔记

### 中期（1~2 周）— 自研 agent 迭代

- [ ] my-data-agent v0.1：脱离官方代码复刻最小 ReAct loop（用 Function Calling 替代自由文本 JSON —— 直接消灭本轮所有解析类故障）
- [ ] v0.2 工具增强：schema 摘要、observation 截断策略（上下文线性膨胀问题）、文档分块读取
- [ ] v0.3 显式规划：先产出计划再执行
- [ ] 对照实验：同一批题，自研 vs 官方 baseline 分数对比

### 远期（持续）— 向高分架构演进

- [ ] 借鉴冠军方案的 **PLAN→EXPLORE→ANSWER→VERIFY 四阶段架构**（见下文参考基准）
- [ ] 确定性门控（不信任模型自律）：EXPLORE 达标前禁止 ANSWER、答案形状校验、fail-closed 输出守卫
- [ ] 难度专项：medium(Text-to-SQL 多源)、hard/extreme(长文档推理) 各自的针对性策略

## 三、要优化到什么程度（参考基准与目标）

### 评分机制回顾

`Score = Recall − 0.5 × (Extra Columns / Predicted Columns)`，列 multiset 比对。
**含义：答案宁缺勿滥——多给的列会被罚；少给列只损失 recall。**

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
| G5 | 极限挑战 | hidden-set 思维：抗干扰文档、视频模态、fail-closed 设计 |

### 优化方向的优先级判断（基于评分公式）

1. **减少 Extra Columns 罚分** > 提升 Recall：输出守卫（列数/形状校验）是性价比最高的改动；
2. easy→medium→hard 逐层攻克：easy 是纯代码生成，medium 加 Text-to-SQL，hard 考长文档——先保证低难度题零失误；
3. 步数预算与上下文管理是工程瓶颈（observation 回灌线性膨胀，17 步已 15K tokens）。

## 四、相关资源索引

- 高分开源方案（学习材料）：见 [resources](../resources/README.md)
- 本机补丁与环境：[00-environment-setup](../00-environment-setup.md)、[01-patches-for-deepseek](../baseline-study/01-patches-for-deepseek.md)
