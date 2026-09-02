# KDD Cup 2026 · Data Agents · 共享学习工作区

针对 [KDD Cup 2026: Data Agents for Complex Data Analysis](https://dataagent.top/) 的共享学习与自研工作区。

> **比赛一句话**：给定自然语言分析问题 + 一组异构数据资产（CSV / JSON / SQLite / PDF / 图表），
> 构建自主 Data Agent：拆解任务 → 规划步骤 → 调用工具（Python / SQL / API）→ 多步推理 → 输出表格答案 `prediction.csv`。
>
> **评分**：`Score = Recall − λ · (Extra Columns / Predicted Columns)`，列按 multiset 比对（忽略列名/行序），λ = 0.5。
>
> **官方资源**：
> - 官网：<https://dataagent.top/>
> - Starter Kit：<https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit>

---

## 这个仓库是干什么的

供多人共用的 KDD Cup 2026 学习与自研工作区，包含两大部分：

- **`learning/`** — 学习资料区（Markdown 笔记）。每人一个子目录 `learning/<用户名>/`，互不覆盖。
- **`code/`** — 代码区。官方比赛资料放 `code/competitions/`（不入库），自研方案放 `code/solutions/<用户名>/`。

仓库级协作规则（提交规范、敏感信息检查、不纳入管理的文件）见 [AGENTS.md](AGENTS.md)。

## 目录结构

```
zzz_ai_data/
├── README.md                        # 本文件：仓库用途与使用说明
├── AGENTS.md                        # 仓库协作规范（AI / 协作者必读）
├── learning/                        # 学习资料区（每人 learning/<用户名>/）
└── code/
    ├── competitions/                # 官方比赛资料（外部仓库 + 数据集，不入库）
    └── solutions/                   # 自研方案代码（每人 code/solutions/<用户名>/）
```

## 使用说明

### 如何开始一次使用

1. 先读本文件与 [AGENTS.md](AGENTS.md)（尤其其中的身份识别规则）；
2. 确认当前使用者是谁，进入其专属目录（`learning/<用户名>/`、`code/solutions/<用户名>/`）工作；
3. 涉及共享内容的改动（根 README、`AGENTS.md`、`.gitignore` 等）先与协作者确认。

### 快速开始（跑官方 baseline）

```powershell
# 1. 克隆官方 starter kit 到 code/competitions/
cd code\competitions
git clone https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit.git

# 2. 下载并解压数据集（见 code/competitions/datasets/README.md）
# 3. 安装 uv 并同步依赖
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
cd kddcup2026-data-agents-starter-kit\PHASE_1
uv sync

# 4. 配置 LLM API（模型 / api_base / api_key），然后：
uv run dabench status --config <你的config.yaml>          # 期望 Public tasks: 50
uv run dabench run-task task_11 --config <你的config.yaml> # 单题验证
```

> 各人的环境配置、踩坑记录、学习笔记都在其 `learning/<用户名>/` 下。

---

> 📋 协作规范：[AGENTS.md](AGENTS.md)　·　🏠 各人学习入口：`learning/<用户名>/README.md`