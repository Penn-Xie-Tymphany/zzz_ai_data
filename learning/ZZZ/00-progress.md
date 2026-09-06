# 进度与目标总控（持续更新）

> **这份文档回答三个问题：现在做了什么？还需要做什么？要优化到什么程度？**
> 每次重大进展后更新本文件。最后更新：2026-09-07

> 🎯 **当前阶段：起步**。工作区骨架刚搭好，尚未跑通官方 baseline。
> 参赛范围与主仓保持一致：只做 **Phase 1**（单一主赛道公共榜），Phase 2（图像/视频新模态 + Creative Subtrack）不参加。

---

## 一、已经做了什么（时间线）

| 日期 | 里程碑 | 产出 |
| --- | --- | --- |
| 09-07 | 建立 `learning/ZZZ/` 工作区骨架（baseline / agent / basics 三分区 + 总控文档） | 本目录当前结构 |

## 二、还需要做什么（按优先级）

### 近期（本周）— 把环境跑起来

- [ ] 读 [basics/比赛总览.md](basics/比赛总览.md)：搞清任务形态与评分公式
- [ ] 通读 [basics/](basics/README.md) 的 01~05，补齐读 agent 源码前的地基
- [ ] 按 [baseline/运维实操.md](baseline/运维实操.md) 搭环境：`uv sync` → `dabench status` 期望 Public tasks: 50
- [ ] 配置自己的 LLM（模型 / api_base / api_key 走本地 config，不入库），跑通单题 `task_11`
- [ ] 读 [baseline/架构总览.md](baseline/架构总览.md)，把"它怎么跑起来"翻译成自己的话

### 中期（1~2 周）— 摸清基线，开始自研

- [ ] 源码精读并补完 `baseline/` 细节笔记（主循环 / 工具 / prompt / 评测）
- [ ] 全量 50 题跑分，落一份属于自己的基线数字与失败归因（填 `baseline/全量跑分复盘.md`）
- [ ] 自研 `zzz_data_agent` v0.1：最小 ReAct loop
- [ ] 对照实验：同一批题，自研 vs 官方 baseline

### 远期（持续）— 向高分架构演进

- [ ] 输出守卫：答案列形状校验（评分公式对多给列罚分，见第三节）
- [ ] 阶段化架构：PLAN → EXPLORE → ANSWER → VERIFY + 确定性门控
- [ ] 难度专项：easy（代码生成）/ medium（Text-to-SQL）/ hard（长文档）分别优化

## 三、要优化到什么程度（参考基准与目标）

### 评分机制（官方口径，详见 `code/competitions/evaluation/`）

`Score = max(0, Recall − λ × (Extra Columns / Predicted Columns))`，λ 复现口径 0.5（官方只公开符号 λ）。
列按**内容签名**匹配（值归一化后多重集，忽略列名/行序/列序，一对一），负分截 0。
**含义：答案宁缺勿滥——多给的列会被罚；少给列只损失 recall。**

> 本地已有官方同口径评分器 `code/competitions/evaluation/`，并融合进 starter-kit：
> `run-benchmark` 跑完自动出分（明细写入 `artifacts/runs/<run_id>/evaluation_report.json`）；
> 复盘历史 run 用 `uv run dabench evaluate <run_id> --config <yaml>`（不调模型）。

### 外部参照系（来自仓库共享资料，我的分数待实测）

| 参照 | 成绩 | 说明 |
| --- | --- | --- |
| 官方裸 baseline（ReAct，强模型后端） | demo 上 micro ≈ 0.376 | 社区复盘的公开数字 |
| Phase 1 冠军（Team KOBUSHI） | A-board 0.5965 / B-board 0.6812 | 开源仓库公开成绩 |
| **我（ZZZ）** | **待实测** | 跑完 50 题后填入本节 |

> ⚠️ **口径提醒**：别人的数字来自不同数据集/不同模型，只能当方向参照，
> **不可跨集直接比大小**。我自己的进度以同一份 demo 50 题的前后对比为准。

### 我的目标阶梯

| 阶段 | 目标 | 验收标准 |
| --- | --- | --- |
| G1 | 跑通单题 | 任选一题跑出 `prediction.csv`，能与 gold 对齐 |
| G2 | 摸清基线 | 全量 50 题出分，并写出失败归因（未提交 / 全错 / 部分正确） |
| G3 | 不低于官方 baseline | 自研 v0.x 分数 ≥ 官方 baseline 在同一批题上的分数 |
| G4 | 进入优秀区间 | demo 50 题 overall 逼近公开冠军量级（待实测后填具体阈值） |
| G5 | 极限挑战 | hidden-set 思维：抗干扰文档、fail-closed 输出守卫 |

### 优化方向的优先级判断（基于评分公式）

1. **先降 Extra Columns 罚分**，再谈 Recall：输出列形状校验是性价比最高的改动；
2. easy → medium → hard 逐层攻克：低难度题先做到零失误；
3. 步数与上下文预算是工程瓶颈：observation 回灌会线性膨胀，长任务需要截断/摘要。

## 四、相关资源索引

- 通识地基：[basics/](basics/README.md)
- 官方代码学习：[baseline/](baseline/README.md)；环境与跑法：`baseline/运维实操.md`
- 自研代码目录：`code/solutions/zzz_data_agent/`（待创建）
- 本地评分器（官方同口径）：`code/competitions/evaluation/`
- 高分开源方案（学习材料）：[参考资源收藏.md](basics/参考资源收藏.md)
