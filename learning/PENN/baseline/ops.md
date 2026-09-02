# baseline 运维实操（跑环境 / 跑分 / 看产物）

> **是什么**：让官方 baseline 在你机器上跑起来的全部操作步骤。
> **为什么重要**：环境就位、命令拿手，才能快速验证任何改动。
> **和比赛的关联**：跑分是自研迭代的地基——先跑通官方，再跑你的。

---

## 1. 环境全景（一次装好）

| 组件 | 说明 |
| --- | --- |
| Python ≥ 3.10 | `python --version` |
| `uv` | 仓库统一包管理器（`uv --version`） |
| 官方 starter kit | `code/competitions/kddcup2026-data-agents-starter-kit/`（**外部仓库，不入 git**） |
| 数据集 | `PHASE_1/data/public/`（50 题：easy15 / medium23 / hard11 / extreme1） |
| LLM 后端 | 阿里云百炼 `qwen3.8-flash`（OpenAI 兼容端点，无速率限制） |

> 网络备忘：Google 系不可用；GitHub / astral.sh / PyPI 可用；数据集走百度网盘人工下载。

---

## 2. 配置 LLM 后端

新建 `PHASE_1/configs/qwen38_flash.yaml`（**含密钥，已被 .gitignore 忽略**）：

```yaml
dataset:
  root_path: data/public/input
agent:
  model: qwen3.8-flash
  api_base: https://ws-aiq3phs9t4to7xr1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
  api_key: <你的阿里云百炼 sk-ws-... 密钥>
  max_steps: 40
  temperature: 0.0
run:
  output_dir: artifacts/runs
  max_workers: 1
  task_timeout_seconds: 1800
```

要点：
- 阿里云 `/compatible-mode/v1` 是标准 OpenAI 兼容接口 → 官方 openai SDK **开箱即用**，无需补丁；
- `api_key` 绝不出现在 git 里（`.gitignore` 已覆盖 starter-kit 目录）。

---

## 3. 常用命令

```powershell
# 环境自检（应有 50 题）
uv run dabench status --config configs/qwen38_flash.yaml

# 跑单题（先用来验证链路）
uv run dabench run-task task_11 --config configs/qwen38_flash.yaml

# 跑一题看产物
cat artifacts/runs/<run_id>/task_11/prediction.csv

# 小批量跑分（建议先 5 题）
uv run dabench run-benchmark --config configs/qwen38_flash.yaml --limit 5

# 全量 50 题
uv run dabench run-benchmark --config configs/qwen38_flash.yaml
```

---

## 4. 跑完后看什么

```
artifacts/runs/<run_id>/task_XX/
├── trace.json       # 完整轨迹（排错核心证据）
├── prediction.csv   # 提交物
└── run.json         # 元信息：耗时 / token / 模型
```

**三步排查法**：
1. 看 `prediction.csv` 是否正确 → 不对就进 trace；
2. 在 `trace.json` 里找到"思维断点"（哪一步开始绕路/报错）；
3. 对照 `00-progress.md` 记录归因，形成迭代输入。

---

## 5. 已实测成绩（参照系）

| 项目 | 结果 |
| --- | --- |
| task_11（DeepSeek） | 17 / 22 / 40 步波动，前两跑答案全对 |
| task_11（qwen3.8-flash） | 17 步全对（tokens 905→9897） |
| 官方裸 baseline 全题 | demo 实测 micro ≈ 0.376 |

> 波动原因：「同配置多次结果不同」详见 `basics/03`。

---

## 6. 常见问题速查

| 症状 | 处理 |
| --- | --- |
| 报错 model not found | 核对 `configs/qwen38_flash.yaml` 的 model / api_base 拼写 |
| 401 / 鉴权失败 | api_key 是否过期；阿里云百炼控制台核对密钥状态 |
| 任务卡死到超时 | 先看 run.json 是否 timeout 标记；重跑一次（有时是偶发） |
| 想换 DeepSeek | 见 [patches.md](patches.md)（需重打 8 处补丁） |