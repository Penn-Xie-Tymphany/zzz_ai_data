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

- [ ] 安装 Python 3.10+、[uv](https://docs.astral.sh/uv/)（starter kit 用它管理依赖）
- [ ] 准备一个 LLM 后端：OpenAI 兼容 API（如阿里云百炼 Qwen 系列 / OpenAI / DeepSeek 等），配好 `.env`
- [ ] `code/competitions/` 下 clone starter kit、下载 Phase 1 demo 数据集并解压

### Phase 1 — 跑通官方 Baseline（1~2 天）

- [ ] 按 `code/competitions/kddcup2026-data-agents-starter-kit/README` 装依赖（`uv sync`）
- [ ] 在 demo 数据集上端到端跑通 ReAct baseline，产出 `prediction.csv`
- [ ] 记录：跑通了哪些 task、失败哪些、日志在哪 → 写入 `learning/experiments-log/`

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

```powershell
# 1. 进入比赛资料目录，克隆官方 starter kit
cd code\competitions
git clone https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit.git

# 2. 下载 Phase 1 demo 数据集（官网 dataagent.top 的 DataAgent-Bench 区块有链接）
#    解压后放到 code/competitions/datasets/ 下

# 3. 配置 LLM API key（参考 starter kit 内 .env.example）

# 4. 跑 baseline
cd kddcup2026-data-agents-starter-kit
uv sync
uv run python -m ...   # 以官方 README 为准
```
