# 00 · 本机环境搭建实录（2026-08-25）

> 目的：记录这台 Windows 机器上从零到"数据集就绪"的真实步骤、路径与踩坑。
> 换电脑重建环境时直接照抄，避免重新踩坑。

## 机器与基础环境

- Windows（PowerShell 5.1），用户目录 `C:\Users\Penn.Xie.TYMPHANY`
- Python 3.14.3（来自 `.workbuddy\binaries\python`，`python -m pip` 可用，但 `pip/py/uv` 均不在 PATH）
- 工作区：`D:\work\zzz_ai_data`，GitHub 远程 `git@github.com:Penn-Xie-Tymphany/zzz_ai_data.git`

## 已完成步骤

### 1) starter kit 克隆

```powershell
cd D:\work\zzz_ai_data\code\competitions
git clone https://github.com/HKUSTDial/kddcup2026-data-agents-starter-kit.git
```

GitHub 直连可用；仓库按 `PHASE_1/`、`PHASE_2/` 分阶段组织。

### 2) uv 安装

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# 装到 C:\Users\Penn.Xie.TYMPHANY\.local\bin，当前会话需手动加 PATH：
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
```

依赖同步（在 PHASE_1 内）：

```powershell
cd kddcup2026-data-agents-starter-kit\PHASE_1
uv sync          # 自动建 .venv 并按 uv.lock 锁定版本安装
```

### 3) 数据集获取（踩坑最多的一步）

**结论先说：Google Drive 在本机网络不可用（TLS 握手被断），最终走百度网盘人工下载。**

| 尝试 | 结果 |
| --- | --- |
| curl 直连 Google Drive | ❌ TCP 偶尔通但 TLS 握手超时（SNI 阻断特征）；VPN 开启时可下载，但 **17 分钟只下到 131MB 即断流**，zip 缺 EOCD 尾记录 = 截断损坏 |
| HuggingFace / hf-mirror / ModelScope / Gitee 搜镜像 | ❌ 无此数据集 |
| GitHub 参赛仓库找已入库的数据 | ❌ 11 个仓库（含 Rank9、Rank4 方案）均只有代码和 trace，无人提交数据 |

**最终方案**：百度网盘 <https://pan.baidu.com/s/14MrxhShtuAjY9Z_jBMW_sg?pwd=bh3v>（提取码 bh3v）
→ 手动下载 `demo_samples_0417.zip`（436MB）到 `code\competitions\datasets\`
→ 解压到官方默认路径：

```powershell
cd code\competitions\kddcup2026-data-agents-starter-kit
New-Item -ItemType Directory -Force -Path "PHASE_1\data"
tar.exe -xf ..\..\datasets\demo_samples_0417.zip -C "PHASE_1\data"
```

> 经验：zip 完整性快速校验 = 读文件头两字节是否 `PK` + 文件尾部 128 字节内是否有 EOCD（`50 4B 05 06`）。
> 大文件下载务必检查完整性，HTTP 200 ≠ 下载完整。

### 4) 数据集验证

```powershell
uv run dabench status --config configs/react_baseline.example.yaml
# Public tasks: 50   easy=15, extreme=1, hard=11, medium=23 ✅
```

实际落位结构：

```
PHASE_1/data/public/
├── input/task_<id>/task.json + context/{csv|json|db|doc, knowledge.md}
└── output/task_<id>/gold.csv        # demo 才有答案；hidden test 只有 input
```

### 5) SSH Key 与 GitHub

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh"
ssh-keygen -t ed25519 -C "kddcup2026-learning-workstation" -f "$env:USERPROFILE\.ssh\id_ed25519" -N '""'
# 公钥添加到 github.com/settings/keys 后验证：
ssh -T git@github.com    # Hi Penn-Xie-Tymphany! ✅
```

- ssh-agent 服务默认 Disabled 且无管理员权限改不了 → **不影响使用**，git 直接读默认密钥文件
- github.com:22 端口本机可直连，无需 443 备用通道
- 推送：`git branch -M main; git push -u origin main`

## 待办（下一步卡点）

- [ ] 配置 LLM API：复制 `configs/react_baseline.example.yaml` 为 `react_baseline.local.yaml`，
      填入 OpenAI 兼容端点的 model / api_base / api_key
- [ ] 先跑单题验证链路：`uv run dabench run-task task_11 --config ...local.yaml`
- [ ] 再小批量：`run-benchmark --limit 5`，最后全量 50 题

## 网络环境备忘

- Google 系（drive/docs.google.com）：不可用；`drive.usercontent.google.com` 偶发可达但极不稳定
- GitHub（github.com / api.github.com / codeload）：可用
- astral.sh（uv 安装脚本）、PyPI：可用
- 百度网盘：仅能人工客户端下载，无法脚本化
