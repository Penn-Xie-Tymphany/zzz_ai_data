# 本地评测工具（DataAgent-Bench 评分器）

> 把本地跑出的 `prediction.csv` 与 demo 的 `gold.csv` 按**官方同口径**对比打分，
> 用于跟排行榜、公开基线（如官方裸 baseline micro≈0.376）做量化对比。
> 纯 Python 标准库实现，无需 uv/三方依赖；测试为 unittest 风格，直接 `py` 可跑。

## 评分规则（官方口径，规则 6.2/6.3）

```
Score = max(0, Recall − λ · (Extra Columns / Predicted Columns))
Recall = Matched Columns / Gold Columns
Extra  = Predicted Columns − Matched
```

- **列匹配按内容签名**：每列全部值先归一化 → 统计成多重集 Counter →
  签名 `tuple(sorted(Counter.items()))`；签名完全一致的列才算匹配；
- **忽略列名、行序、列序**；
- 匹配是**一对一**：一个预测列最多命中一个 gold 列（不能一列抵多列）；
- Score **下限为 0**（负分截断）。

### λ 取值说明（重要）

官方规则只公开符号 λ，**未公开具体数值**。证据情况：

| 来源 | λ | 说明 |
| --- | --- | --- |
| 本仓库既有文档 / BrightLiao 复盘（复现官方 demo micro≈0.376） | **0.5** | 默认口径，用于与官方 demo 基线对比 |
| 某冠军内部自测脚本（zhezh） | 0.1 | 团队内部调参，非官方值 |

`scoring.py` 默认 `--lam 0.5`，可随时用 `--lam` 切换。**与排行榜精确对比前请确认官方最新规则公告的 λ。**

## 值归一化（决定两列是否同签名）

| 输入 | 归一后 |
| --- | --- |
| `None` / `NaN` / 空串 / `nan`/`none`/`null`/`n/a` | `""` |
| float | 四舍五入保留 2 位小数 → 去尾零 → 去尾小数点（空回退 `"0"`），如 `1.0→"1"`、`1.50→"1.5"` |
| bool | `True→"1"`、`False→"0"`（须先于 int 判断） |
| int | `str(int)` |
| 字符串可解析为数字 | 无小数点且无指数 → 整数字面量；否则同上 2 位小数规则（`"1.0"→"1"`、`"1e3"→"1000"`） |
| 日期 `YYYY[-/.]M[-/.]D`（可带 T/空格后缀） | ISO `YYYY-MM-DD`（`2024/1/5→"2024-01-05"`） |
| 其余文本 | `strip` + 折叠连续空白（含换行/Tab） |

> 注意：`round(2.675, 2)` 在 Python 返回 `2.67`（二进制浮点），官方/复现实现同样带入此行为，此处保持一致。

## 用法

```powershell
# 1) 单题对比
py scoring.py --pred artifacts/runs/<run_id>/task_11/prediction.csv `
              --gold  ../kddcup2026-data-agents-starter-kit/PHASE_1/data/public/output/task_11/gold.csv

# 2) 整批跑分（推荐）：扫描 predict-root 下全部 task_*/prediction.csv
py scoring.py --predict-root artifacts/runs/<run_id> `
              --gold-root ../kddcup2026-data-agents-starter-kit/PHASE_1/data/public/output `
              --input-root ../kddcup2026-data-agents-starter-kit/PHASE_1/data/public/input `
              --out report.json

# 3) 换 λ 对齐不同口径
py scoring.py --predict-root ... --gold-root ... --lam 0.1

# 4) 单元测试（18 用例）
py tests/test_scoring.py
```

提示：本机 PowerShell 控制台对 UTF-8 中文回显可能乱码，属显示层问题；需要机器可读结果时加 `--out report.json` 看文件。

## 批量输出字段

- 每题：`task_id / difficulty / gold_columns / predicted_columns / matched /
  recall / extra / score / note`；
  `note` 常见值：`no prediction.csv`（未提交，0 分）、`empty gold header/rows`；
- 聚合（写 JSON 或打印）：
  - `overall.mean`：**全部 gold 任务**逐题 score 平均（未提交按 0 分计入）——与"官方 demo 基线 micro≈0.376"同口径；
  - `submitted_mean`：仅统计已产出 prediction.csv 的任务；
  - `by_difficulty.*`：easy/medium/hard/extreme 分组统计（n / mean / perfect / zero）；
  - perfect 判定：`score ≥ 0.999`。

## 目录结构

```
evaluation/
├── README.md          # 本文件
├── scoring.py         # 评分器（normalize_value / column_signature / score_task / score_batch / CLI）
└── tests/
    └── test_scoring.py
```

## 参考来源

- 官网评分说明：https://dataagent.top/ （Scoring & Evaluation / Rules 6.2, 6.3）
- 社区对官方公式的复现实现：BrightLiao/KDDCupDataAgent（`src/eval/scorer.py`、`src/eval/normalize.py`）
- 归一化"黄金测试向量"见 `tests/test_scoring.py::TestNormalize`
