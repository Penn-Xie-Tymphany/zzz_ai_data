# 03 · 这个比赛到底让 AI 干什么？（人类视角白话版）

> **一句话**：给 AI 一个"项目资料袋"+ 一句业务问题，它要像一个初级数据分析师那样，
> 自己翻资料 → 定口径 → 写代码算数 → 交一张结果表。
> 本文用真实题目走一遍「如果是人来做的流程」，对照出 AI Agent 在做什么。
> 最后更新：2026-08-26

---

## 一、AI 拿到的东西：一个"项目资料袋"

每个任务 = 一个独立文件夹，模拟"分析师入职第一天收到的材料"：

```
task_11/
├── task.json                  ← 任务卡：题目编号、难度、一句自然语言问题
└── context/                   ← 全部资料（AI 只能在这个文件夹里活动）
    ├── knowledge.md           ← 【必读】数据字典/业务口径说明书
    └── json/
        ├── Patient.json       ← 病人主表（ID、性别、生日、诊断…）
        └── Examination.json   ← 检查记录表（含血栓严重度字段）
```

**50 个题目的资料袋按难度递增**（demo 实测）：

| 难度 | 真实例子 | 袋子里有什么 | 难在哪 |
| --- | --- | --- | --- |
| easy ×15 | task_11 | JSON 文件 + knowledge.md | 会写 Python 处理数据 |
| medium ×23 | task_145 | CSV + **SQLite 数据库(.db)** + knowledge.md | 要写 SQL、跨文件对齐 |
| hard ×11 | task_330 | **279MB 的巨型 CSV** + 说明文档 + knowledge.md | 数据大到不能直接读，得用工具翻 |
| extreme ×1 | task_418 | **286KB 纯文本文档**×2 + knowledge.md | 要在长文档里找口径再计算 |

## 二、真实案例全程走读：task_11（easy）

### 题目

> "For patients with severe degree of thrombosis, list their ID, sex and disease the patient is diagnosed with."
> （列出重度血栓患者的 ID、性别、所患疾病。）

### 如果是一个人类分析师 🧑‍💼

| 步骤 | 动作 | 心里在想 |
| --- | --- | --- |
| 1 | 把文件夹里的文件都点开看看 | "有个说明文档、两张 JSON 表" |
| 2 | **先读 knowledge.md**（数据字典） | "原来 Thrombosis 字段在检查表里，'1'=最严重、'2'=severe——'重度'应该指这两档" |
| 3 | 瞄一眼两张表的结构 | "Patient 有 ID/SEX/Diagnosis；Examination 有 ID/Thrombosis。两表靠 ID 关联" |
| 4 | 定计划 | "① 从检查表筛出 Thrombosis 为 1 或 2 的记录 → ② 拿这些 ID 去 Patient 表查性别诊断 → ③ 拼成三列表" |
| 5 | 打开 Excel/写个 Python 脚本执行 | "筛出来 18 条检查记录…" |
| 6 | **发现脏数据**：部分 ID 在 Patient 表里查无此人 | "查不到性别就没法交差，这几行只能丢弃" |
| 7 | 核对结果，填入答案模板交表 | "3 行：163109/F/SLE、2803470/F/SLE、4395720/F/SLE" |

### AI Agent 做的完全一样，只是每一步变成「思考 → 调工具」🤖

实测 trace（22 步，72 秒）：

| AI 步骤 | 对应人类的动作 | 用的工具 |
| --- | --- | --- |
| step 1 | "先看看文件夹里有什么" | `list_context(max_depth=4)` |
| step 2 | 读数据字典，搞懂"severe"的口径 | `read_doc("knowledge.md")` |
| step 3-4 | 翻两张表的结构和样例数据 | `read_json(...)` ×2 |
| step 5-14 | 写 Python 反复筛选验证（还自己发现并处理了 ID 对不上的脏数据） | `execute_python(code)` ×10 |
| step 15-16 | 中途两次输出格式错误，看到报错后自我纠正 | （解析容错 + 重试） |
| step 17 | **交表**：columns=["ID","SEX","Diagnosis"], rows=[...] | `answer(...)` ← 唯一终止动作 |

**结论：Agent = 用 LLM 扮演上面那个人的大脑，用工具扮演他的手和眼睛。**

## 三、四件套：读什么、想什么、用什么、交什么

### 1️⃣ 读什么（输入材料）

| 材料 | 作用 | 类比 |
| --- | --- | --- |
| `task.json` 的 question | 业务问题，唯一的目标来源 | 老板的需求邮件 |
| `knowledge.md` | **字段含义 + 业务口径 + 计算公式**（如"LDH>500 算异常"） | 公司的数据字典 Wiki |
| `context/` 下数据文件 | 原始数据：CSV / JSON / SQLite / Markdown | 各业务系统的导出表 |

### 2️⃣ 想什么（推理过程 = ReAct 循环）

每一轮都在回答三个问题（写在 trace.json 里可回放）：

```json
{"thought": "我现在知道什么？下一步该干什么？",
 "action": "选哪个工具",
 "action_input": "工具参数"}
```

难点不在单步，而在**串联**：口径要从文档里挖 → 字段要跨表对齐 → 中间结果要自检 → 错了要回头重来。

### 3️⃣ 用什么（8 个工具，官方全部清单）

| 工具 | 干什么 | 人类类比 | 关键限制 |
| --- | --- | --- | --- |
| `list_context` | 列出资料袋文件树 | 拉开抽屉看有什么 | 只见 context/ 内 |
| `read_doc` / `read_json` / `read_csv` | 预览文档/JSON/CSV 前 N 行/字符 | 大致翻一翻 | 默认只给 4000 字符/20 行（防撑爆） |
| `inspect_sqlite_schema` | 看数据库有哪些表、字段类型 | `desc 表名` | 只读连接 |
| `execute_context_sql` | 对 .db 跑 SELECT 查询 | 让 DBA 代查 | 仅 select/with/pragma 开头，最多返回 200 行 |
| `execute_python` | **万能后门**：任意 Python，工作目录就是 context/ | 自己开电脑写脚本 | 子进程隔离，30 秒超时 |
| `answer` | 提交最终表格并结束 | 交差 | 唯一能结束任务的出口 |

### 4️⃣ 交什么（输出物）

```csv
# prediction.csv —— 就是一张普通表格
ID,SEX,Diagnosis
163109,F,SLE
2803470,F,SLE
4395720,F,SLE
```

评分时和隐藏的标准答案 `gold.csv` 做**列的多重集合比对**（不看列名、不看行序）：

```
Score = Recall − 0.5 × (多给的列数 ÷ 你给的列数)
```

所以策略是**宁少勿多**：多猜一列会被罚，少给只是拿不到那部分的分。

## 四、再看三个不同难度的例子（感受差异）

**medium · task_145**（CSV + SQLite）
> 题："在 Student_Club 成员参加超过 10 次的活动里，有多少是会议？"
> 资料袋：`attendance.csv`（签到记录）+ `event.db`（活动数据库，含活动类型）
> 人类做法：SQL 连接签到表和活动表 → 按成员数过滤 → 数 meeting 类型 → 答案就一个数字 `4`

**hard · task_330**（279MB CSV！）
> 题："2008 年 9 月 24 日比甲联赛主客场的比分是多少？"
> 坑：Match.csv 有 2.79 亿字节，直接读会撑爆任何模型 → 必须用 SQL/Python 条件查询，而不是全文阅读
> 考察：知不知道"大数据要用工具查，不能用眼睛看"

**extreme · task_418**（286KB 长文档）
> 题："肌酐水平异常的患者里，有几个不到 70 岁？"
> 资料袋：两份很长的医疗 Markdown + knowledge.md
> 人类做法：先在字典里找到"肌酐异常"的医学口径 → 再在长文中定位相关患者 → 计算年龄
> 考察：上下文管理能力（这正是冠军方案做记忆/检索优化的地方）

## 五、总结成一张图

```
┌─────────────── 任务输入 ───────────────┐      ┌──────────── 最终输出 ───────────┐
│  question（一句业务问题）                │      │  prediction.csv                 │
│  context/（知识文档+异构数据）           │      │  （一张表格，和 gold 多重集比对） │
└──────────────────┬─────────────────────┘      └────────────────▲────────────────┘
                   ▼                                              │
        ┌── ReAct 循环（最多 N 步）───────────────────────────────┴──┐
        │  thought（想） → action（调工具） → observation（看结果）   │
        │  工具箱：list/read×3/schema/sql/python → answer 终止       │
        └────────────────────────────────────────────────────────────┘
```

> 学习建议：跑一次 `uv run dabench inspect-task task_330 --config configs/react_baseline.local.yaml`
> 再打开 `artifacts/runs/<run_id>/task_11/trace.json` 对照本文，所有概念立刻落地。
