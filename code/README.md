# 代码区（code/）

所有可运行代码都在这里。分三类：

> **当前状态（2026-08-26）**：starter-kit 已克隆 + PHASE_1 依赖已 `uv sync` + 数据集已就位（`PHASE_1/data/public/`，50 题）+
> DeepSeek 已配置（`PHASE_1/configs/react_baseline.local.yaml`，含 API key，勿提交）+ task_11 单题验证通过。
>
> ⚠️ **starter kit 源码含 8 处本机补丁**（DeepSeek 兼容），重克隆必须按
> [补丁记录](../learning/baseline-study/01-patches-for-deepseek.md) 重打。

| 子目录 | 内容 | 是否入库 |
| --- | --- | --- |
| `competitions/` | 官方 starter kit 克隆 + 官方数据集 | ❌ gitignore（外部仓库 + 大文件） |
| `solutions/` | **我们的自研项目**（核心产出） | ✅ |
| `playground/` | 小实验脚本、API 连通性测试、一次性探索 | ✅ |

## 环境搭建

```powershell
# 1) 获取官方比赛资料
cd code\competitions
git clone https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit.git
# 下载 demo 数据集（官网 dataagent.top → DataAgent-Bench → Phase 1 Demo Dataset）
# 解压到 code\competitions\datasets\ 下

# 2) 配置 API key：在 starter kit 目录按其 .env.example 建 .env
#    注意 .env 已被根 .gitignore 忽略，绝不提交密钥

# 3) 跑通 baseline（以官方 README 为准，starter kit 用 uv 管理依赖）
cd kddcup2026-data-agents-starter-kit
uv sync
```

## 使用约定

- `competitions/` 内的官方代码**只读不改**；想改逻辑就复制到 `solutions/` 再动手；
- 自研 agent 每个版本打 tag（v0.1、v0.2 …），配合 `learning/experiments-log/` 做对照；
- 数据集路径统一约定为 `code/competitions/datasets/<phase>/...`，自研代码里用相对路径或环境变量引用。
