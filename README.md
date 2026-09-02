# KDD Cup 2026 · Data Agents 本地学习工作区

针对 [KDD Cup 2026: Data Agents for Complex Data Analysis](https://dataagent.top/) 的本地学习与实验工作区。

> **比赛一句话**：给定自然语言分析问题 + 一组异构数据资产（CSV / JSON / SQLite / PDF / 图表），
> 构建自主 Data Agent：拆解任务 → 规划步骤 → 调用工具（Python / SQL / API）→ 多步推理 → 输出表格答案 `prediction.csv`。
>
> **评分**：`Score = Recall − λ · (Extra Columns / Predicted Columns)`，列按 multiset 比对（忽略列名/行序），λ = 0.5。
>
> **官方资源**：
> - 官网：<https://dataagent.top/>
> - Starter Kit：<https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit>

---

## 📍 当前进度快照（2026-09-02）

> **总控文档：[learning/PENN/00-progress.md](learning/PENN/00-progress.md)** ← 想快速了解"做了什么/还做什么/优化到什么程度"，看这份。

- ✅ 环境全通：starter kit + 50 题数据集 + **阿里云百炼 qwen3.8-flash** 后端（开箱即用）
- ✅ 官方 baseline 单题跑通：task_11 答案与标准答案**完全一致**（17 步 / 22 步 两套后端均通过）
- ✅ 学习资料就绪：baseline 架构图（Mermaid）+ 通识基础 + [人类视角任务白话解释](learning/PENN/basics/task-walkthrough.md)
- ⏭️ 下一步：50 题全量跑分摸清基线 → 失败 case 归因 → 自研 agent 迭代
- 🎯 目标阶梯：官方裸 baseline ≈0.376 → 自研超越它 → 冲 0.55~0.60（Phase1 冠军 A-board 水平）

---

## 一、目录结构

```
zzz_ai_data/
├── README.md                        # 本文件：总 PLAN 与导航
├── AGENTS.md                        # ★ 仓库协作规范（AI/协作者必读）
│
├── learning/                        # ★ 学习资料区（笔记为主，不写生产代码）
│   └── PENN/                        # ★ Penn 个人学习工作区（见其 README）
│       ├── baseline/                #   官方 starter kit 学习（架构/流程/评测/运维）
│       ├── agent/                   #   我的自研 agent 项目说明
│       ├── basics/                  #   跨项目通识知识
│       ├── experiments-log/         #   实验记录（含模板）
│       └── 00-progress.md           #   进度总控
│
└── code/                            # ★ 代码区（所有可运行代码都在这里）
    ├── competitions/                # 比赛资料（官方内容，不入库）
    │   ├── kddcup2026-data-agents-starter-kit/   # 官方 starter kit（git clone）
    │   └── datasets/                # 比赛数据集（demo_samples.zip 解压到这里）
    └── solutions/                   # 【我们的项目】自研方案代码
        └── penn_data_agent/         # Penn 的自研 Data Agent
```

**原则**：

- `learning/` 只放 Markdown 笔记；每个人的文档放自己的子目录（Penn → `PENN/`）；
- `code/competitions/` 保持官方原样；自研代码都放 `code/solutions/<人名>/`；
- 数据集、模型产物、虚拟环境一律 gitignore（见 `.gitignore` 与 `AGENTS.md` §4）；
- **所有协作者遵守根目录 [AGENTS.md](AGENTS.md)**（提交规则、敏感信息检查）。

---

## 二、学习 PLAN（路线图）

详细进度见 [PENN/00-progress.md](learning/PENN/00-progress.md)，这里保留规划骨架。

### Phase 0 — 环境搭建

- [x] Python 3.10+、uv（starter kit 用其管理依赖）
- [x] LLM 后端：**阿里云百炼 qwen3.8-flash**（OpenAI 兼容端点，配置见 [ops.md](learning/PENN/baseline/ops.md)）
- [x] clone starter kit、解压 Phase 1 demo 数据集（50 题，`dabench status` 验证通过）

### Phase 1 — 跑通官方 Baseline

- [x] 单题跑通：task_11 (easy) 答案与 gold **完全一致** → [实验记录](learning/PENN/experiments-log/2026-08-26-first-baseline-task.md)
- [ ] 小批量：`run-benchmark --limit 5` 看 easy 通过率
- [ ] 全量 50 题 + 记录 micro/macro → 写入 experiments-log

### Phase 2 — 吃透 Baseline（架构层为主）

先读 [architecture.md](learning/PENN/baseline/architecture.md)（全 Mermaid 架构图），细节按需看 [deep-dive.md](learning/PENN/baseline/deep-dive.md)。

### Phase 3 — 基础知识补强（并行进行）

见 [basics/README.md](learning/PENN/basics/README.md)：ReAct、LLM 上下文、Function Calling、并发…

### Phase 4 — 自研改进（持续）

在 `code/solutions/penn_data_agent/` 里从零实现自己的 agent，逐版本叠加改进（v0.1 最小 ReAct → v0.5 评测驱动迭代）。

### Phase 5 — 总结沉淀

输出完整复盘：方法、消融、得分曲线、经验教训。

---

## 三、快速开始

> **当前状态（2026-09-02）**：环境已通、baseline 已跑通单题。换机重建按下面顺序执行。

```powershell
# 1. 进入比赛资料目录，克隆官方 starter kit
cd code\competitions
git clone https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit.git

# 2. 获取 Phase 1 demo 数据集（436MB zip 放 datasets\ 下）并解压
tar.exe -xf ..\datasets\demo_samples_0417.zip -C kddcup2026-data-agents-starter-kit\PHASE_1\data\

# 3. 安装 uv 并同步依赖
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
cd kddcup2026-data-agents-starter-kit\PHASE_1
uv sync

# 4. 配置 LLM API 后跑 baseline
#    配置细节与命令见 learning/PENN/baseline/ops.md
uv run dabench status --config <你的config.yaml>          # 期望 Public tasks: 50
uv run dabench run-task task_11 --config <你的config.yaml> # 单题验证
```

---

> 📚 学习入口：[learning/PENN/README.md](learning/PENN/README.md)　·　📋 协作规范：[AGENTS.md](AGENTS.md)