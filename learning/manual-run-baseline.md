# 手动运行官方 Baseline 教程

> 本文档一步步教你如何**自己动手**跑官方 baseline，理解整个流程。
> 目标：从零开始，跑通一个 easy 题，理解输出物。

---

## 前置条件

- 已安装 Python 3.10+（确认：`python --version`）
- 已安装 uv（确认：`uv --version`）
- 已 clone 官方 starter kit 到 `code/competitions/kddcup2026-data-agents-starter-kit/`
- 数据集已解压到 `PHASE_1/data/public/`（50 个任务）

---

## 第一步：创建配置文件

配置文件告诉 baseline 用哪个 LLM 后端。在 `PHASE_1/configs/` 下创建 `local.yaml`：

```yaml
# PHASE_1/configs/local.yaml
agent:
  name: react          # 用官方 ReAct agent
  max_steps: 30        # 最大循环步数
  max_retries: 2       # 单步重试次数

model:
  name: openrouter/auto   # 模型名（后面会详解选哪个）
  temperature: 0.0        # 评测推荐 0
  max_tokens: 2048        # 单步最大输出 token

runner:
  task_timeout_seconds: 1800   # 单题超时（秒）
  max_workers: 1               # 并发数（手动跑建议 1）

# OpenRouter 通过 OpenAI 兼容接口接入
openai_compatible:
  api_base: https://openrouter.ai/api/v1
  api_key: sk-or-v1-你的key
```

**注意**：`api_key` 是你刚给我的 OpenRouter key。**不要**把真实 key 写进会被 git commit 的文件里！

---

## 第二步：选模型

OpenRouter 的免费模型带 `:free` 后缀。以下是我推荐的优先级：

| 优先级 | 模型 ID | 参数 | 上下文 | 推荐理由 |
| --- | --- | --- | --- | --- |
| ⭐ 首选 | `nvidia/nemotron-3-ultra:free` | 550B(55B active) | 1M | 最强免费模型，推理能力好 |
| ⭐ 首选 | `nvidia/nemotron-3-super:free` | 120B(12B active) | 262K | 上下文够用，推理能力强 |
| 试一试 | `minimax/minimax-m3:free` | 大 | 1M | 多模态，agent 能力不错 |
| 试一试 | `qwen/qwen3-coder:free` | - | 1M | 编码能力强，但任务不只是写代码 |

**自动路由**（最省心）：`openrouter/auto` 或 `openrouter/free`
→ OpenRouter 自动从可用免费模型里挑一个。简单题够用，难题可能挑到弱模型。

**⚠️ 免费模型限制**：
- 20 RPM（每分钟 20 次请求）
- 50 次/天（未充值）或 1000 次/天（充过 $10+）
- 模型列表会变——今天有的明天可能下架
- 所以**不要硬编码模型 ID**，写进配置后确认能跑通

---

## 第三步：运行单个任务

```bash
cd code/competitions/kddcup2026-data-agents-starter-kit/PHASE_1

# 方式 1：用 uv run（推荐，自动管理依赖）
uv run dabench run-task \
  --config configs/local.yaml \
  --task-id task_11 \
  --dataset data/public

# 方式 2：如果 uv 有问题，用 Python 直接调
uv run python -c "
from dabench.run.runner import TaskRunner
runner = TaskRunner('configs/local.yaml')
runner.run_single('task_11', 'data/public')
"
```

---

## 第四步：看输出

运行完成后在 `artifacts/runs/` 下会生成一个目录，结构如下：

```
artifacts/runs/
└── 2026-09-02T..._react_openrouter/
    └── task_11/
        ├── trace.json       ← 完整轨迹（最重要！）
        ├── prediction.csv   ← 你的答案
        └── run.json         ← 元信息（耗时、token 数）
```

### trace.json 里的关键字段

```json
{
  "steps": [
    {
      "step": 1,
      "type": "thought",
      "content": "模型的思考过程",
      "messages": [...]      // 完整消息历史
    },
    {
      "step": 1,
      "type": "action",
      "action": "list_context",
      "action_input": {}
    },
    {
      "step": 1,
      "type": "observation",
      "content": "{...}"    // 工具返回的结果
    }
  ],
  "answer": {
    "status": "success",
    "content": "..."
  }
}
```

### prediction.csv 长什么样

```csv
检查ID,检查结果,对应病人ID
10407,10407,10407
20818,20818,20818
30725,30725,30725
```

---

## 第五步：对比答案

```bash
uv run dabench score-task \
  --task-id task_11 \
  --prediction artifacts/runs/.../task_11/prediction.csv \
  --dataset data/public
```

输出类似：
```
task_11: micro=1.000 macro=1.000 (完美匹配)
```

---

## 第六步：看 token 消耗和成本

```bash
# 在 run.json 里找：
cat artifacts/runs/.../task_11/run.json | python -m json.tool | grep -i token
```

OpenRouter 的 response 里也有 usage 字段：
```json
"usage": {
  "prompt_tokens": 15210,
  "completion_tokens": 128,
  "total_tokens": 15338
}
```

免费模型不收费，但有请求次数限制，要省着用。

---

## 常见问题

### Q: 报错 "model not found"
→ 检查模型 ID 拼写，确认带 `:free` 后缀。到 https://openrouter.ai/models?variant=free 看当前有哪些。

### Q: 报错 "rate limited"
→ 免费模型有 RPM 限制（20次/分钟）。跑 benchmark 时设 `max_workers: 1`，别并发。

### Q: 模型输出格式不对（不是 JSON）
→ 免费模型指令跟随能力弱于 DeepSeek。试换 Nemotron Ultra（推理最强的免费模型）。

### Q: 想跑全部 50 题
```bash
uv run dabench run-benchmark \
  --config configs/local.yaml \
  --dataset data/public
```
→ 免费 50 次/天可能不够，考虑分批跑或充值到 1000 次/天。

---

## 下一步

跑通后你会对整个流程有直观感受。接下来可以：
1. 对比你的 OpenRouter 结果 vs 我们之前 DeepSeek 的结果（task_11 DeepSeek 是 17 步全对）
2. 读 trace.json 看免费模型的思考质量
3. 开始写自己的 agent（my-data-agent）
