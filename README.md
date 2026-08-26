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

## 📍 当前进度快照（2026-08-26）

> **总控文档：[learning/competition-notes/02-progress-and-targets.md](learning/competition-notes/02-progress-and-targets.md)** ← 想快速了解"做了什么/还做什么/优化到什么程度"，看这份。

- ✅ 环境全通：starter kit + 50 题数据集 + DeepSeek 后端 + 8 处兼容补丁
- ✅ 官方 baseline 单题跑通：task_11 答案与标准答案**完全一致**（22 步 / 72 秒）
- ✅ 学习资料就绪：源码精读 5 篇全完成 + [人类视角任务白话解释](learning/competition-notes/03-task-walkthrough-human-view.md) + ReAct 基础笔记
- ⏭️ 下一步：50 题全量跑分摸清基线 → 失败 case 归因 → 自研 agent 迭代
- 🎯 目标阶梯：官方裸 baseline ≈0.376 → 自研超越它 → 冲 0.55~0.60（Phase1 冠军 A-board 水平）

---

## 一、目录结构

```
zzz_ai_data/
├── README.md                        # 本文件：总 PLAN 与导航
│
├── learning/                        # ★ 学习资料区（笔记为主，不写生产代码）
│   ├── README.md                    # 学习资料区使用说明
│   ├── competition-notes/           # 比赛研究：规则、评分、难度分级、榜单观察
│   │   └── 01-competition-overview.md
│   ├── basics/                      # 基础知识：ReAct、Tool Calling、Text2SQL、文档理解…
│   ├── baseline-study/              # 官方 starter-kit 源码精读笔记
│   ├── experiments-log/             # 实验记录 / 学习日志（含模板）
│   └── resources/                   # 论文、博客、视频等外部资源收藏
│
└── code/                            # ★ 代码区（所有可运行代码都在这里）
    ├── README.md                    # 代码区说明：环境搭建、如何跑 baseline
    ├── competitions/                # 比赛资料（官方内容，不入库）
    │   ├── kddcup2026-data-agents-starter-kit/   # 官方 starter kit（git clone）
    │   └── datasets/                # 比赛数据集（demo_samples.zip 解压到这里）
    ├── solutions/                   # 【我们的项目】自研方案代码
    │   └── my-data-agent/           # 自研 Data Agent 项目骨架
    └── playground/                  # 小实验：API 连通性、工具试用、临时脚本
```

**原则**：

- `learning/` 只放 Markdown 笔记，随手记录，按主题归档；
- `code/competitions/` 保持官方原样，不修改官方代码（要改就复制到 `solutions/`）；
- 数据集、模型产物、虚拟环境一律 gitignore（见 `.gitignore`）；
- 每次跑完实验，把结论沉淀到 `learning/experiments-log/`。

---

## 二、学习 PLAN（路线图）

### Phase 0 — 环境搭建（0.5 天）

- [x] 安装 Python 3.10+、[uv](https://docs.astral.sh/uv/)（starter kit 用它管理依赖）
- [x] 准备 LLM 后端：DeepSeek `deepseek-chat`（v4-flash），配置见 starter kit `configs/react_baseline.local.yaml`
- [x] `code/competitions/` 下 clone starter kit、下载 Phase 1 demo 数据集并解压（50 题，`dabench status` 验证通过）

> 环境实录（真实命令/路径/踩坑）：[learning/00-environment-setup.md](learning/00-environment-setup.md)
> ⚠️ 官方代码含 8 处 DeepSeek 兼容补丁，重克隆需重打：[learning/baseline-study/01-patches-for-deepseek.md](learning/baseline-study/01-patches-for-deepseek.md)

### Phase 1 — 跑通官方 Baseline（1~2 天）

- [x] 按 `code/competitions/kddcup2026-data-agents-starter-kit/README` 装依赖（`uv sync`）
- [x] 单题跑通：task_11 (easy) 答案与 gold **完全一致**（22 步/72s）→ [实验记录](learning/experiments-log/2026-08-26-first-baseline-task.md)
- [ ] 小批量：`run-benchmark --limit 5` 看 easy 通过率
- [ ] 全量 50 题 + 记录 micro/macro → 写入 `learning/experiments-log/`

### Phase 2 — 精读 Baseline 源码（3~5 天）

重点读懂四个模块，边读边在 `learning/baseline-study/` 记笔记：

- [ ] **Agent 循环**：ReAct 的 thought → action → observation 循环怎么实现
- [ ] **工具系统**：`execute_python` / `execute_context_sql` / `read_csv` / `read_doc` / `inspect_sqlite_schema` 等工具的输入输出协议
- [ ] **Prompt 工程**：system prompt 怎么组织（角色、工具说明、JSON 输出协议、历史回灌）
- [ ] **评测流程**：答案如何与 gold 对比（multiset 列比对）、micro/macro 分数怎么算

### Phase 3 — 基础知识补强（并行进行）

按需阅读，每个主题一篇笔记放 `learning/basics/`：

- [ ] ReAct 范式与函数调用（Function Calling）
- [ ] Text-to-SQL：schema linking、few-shot、执行反馈修正
- [ ] 非结构化文档理解：PDF/DOCX 解析、长上下文处理
- [ ] Agent 高级模式：任务分解（DAG 规划）、自我反思（self-reflection）、多 agent 协作

### Phase 4 — 自研改进（持续）

在 `code/solutions/my-data-agent/` 里从零实现自己的 agent，逐个叠加改进点：

- [ ] v0.1：复刻一个最小 ReAct loop（自己写一遍才算学会）
- [ ] v0.2：增强工具集（更好的 schema 摘要、文档分块检索）
- [ ] v0.3：显式任务分解（先规划成 DAG 再逐步执行）
- [ ] v0.4：错误恢复与自我反思（SQL 报错查 schema、NaN 自动清洗重试）
- [ ] v0.5：评测驱动迭代 —— 失败 case 归因分析，针对性优化

### Phase 5 — 总结沉淀

- [ ] 输出一份完整复盘：方法、消融、得分曲线、经验教训

---

## 三、快速开始

> **当前状态（2026-08-25）**：1~2 步已在本机完成，数据集已就位并验证。
> 换机重建按下面顺序执行；本机实际命令与踩坑见 [learning/00-environment-setup.md](learning/00-environment-setup.md)。

```powershell
# 1. 进入比赛资料目录，克隆官方 starter kit
cd code\competitions
git clone https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit.git

# 2. 获取 Phase 1 demo 数据集（436MB zip 放 datasets\ 下）
#    Google Drive 或百度网盘（提取码 bh3v）二选一，链接见 code/competitions/datasets/README.md
#    解压到 starter kit 官方默认路径：
tar.exe -xf ..\datasets\demo_samples_0417.zip -C kddcup2026-data-agents-starter-kit\PHASE_1\data\
#    （需先 New-Item PHASE_1\data 目录；解压后结构为 PHASE_1\data\public\input|output）

# 3. 安装 uv 并同步依赖
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"   # 新终端免打
cd kddcup2026-data-agents-starter-kit\PHASE_1
uv sync

# 4. 验证数据集可见
uv run dabench status --config configs/react_baseline.example.yaml   # 期望 Public tasks: 50

# 5. 配置 LLM API（复制 example 为 local yaml 填 model/api_base/api_key）后跑 baseline
uv run dabench run-benchmark --config configs/react_baseline.local.yaml
```
