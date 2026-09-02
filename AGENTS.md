# AGENTS.md — 仓库协作规范（AI Agent 必读）

> 本文档是本仓库所有 AI 助手、协作者在读取与改动仓库时必须遵守的规则。
> 维护人：Penn（项目所有者）。修改本文件前先与 Penn 确认。

---

## 1. 仓库定位

本仓库是 **KDD Cup 2026（Data Agents for Complex Data Analysis）** 的学习与自研工作区。
当前目录是公共工作区，**任何项目专属内容一律放 `learning/PENN/`**（Penn 的个人学习目录），
`code/solutions/` 下每个人各有自己的方案目录，互不覆盖。

典型结构：

```
code/solutions/            # 每个人的自研方案（每人一个目录）
  penn_data_agent/         # Penn 的自研 agent
learning/PENN/             # Penn 的个人学习/文档目录（3 个子目录：baseline / agent / basics）
AGENTS.md                  # 本文件（仓库级规则）
```

---

## 2. 提交规则（Commit Rules）

1. **只有在用户明确要求时才 commit / push / 建 PR**。不得擅自提交。
2. 提交前必须检查：
   - `git status --short`：确认只暂存**预期要提交**的文件。
   - `git diff` / `git diff --cached`：确认没有误入无关改动。
3. 提交信息**简短、符合仓库既有风格**（用中文，`type: 摘要` 形式，如 `docs: xxx`、`refactor: xxx`）。
4. 不修改 git 全局/本地 config、不跳过 hooks、不做空提交、不 force-push。
5. 若提交被 hook 拒绝，修复后**新建提交**，不要 amend 失败的提交。
6. 提交前执行第 3 节的敏感信息检查。发现密钥 → 立刻中止，改用占位符/环境变量。

---

## 3. 敏感信息检查（Sensitive Info）

**绝不把任何 API Key、Token、密码、私钥提交进 Git。** 每次 commit 前必须自查：

```powershell
# 全仓检索已知的密钥形态（结果应为空 / 只命中占位符）
git grep -n -E "sk-ws-|sk-or-v1-|sk-[a-zA-Z0-9]{24,}" -- .

# 检索常见密钥变量赋值
git grep -n -E "api[_-]?key\s*[:=]\s*['\"]" -- .
```

人工核对要点：
- `api_key:` 一律从配置文件读取，或用环境变量 `(os.environ["LLM_API_KEY"])`，**禁止硬编码**。
- 配置文件若含密钥，必须被 `.gitignore` 覆盖，或用占位符（如 `xxx`）提交，真实值留在本地。
- 遇到新增模型/服务商（DeepSeek / 阿里云百炼 / OpenRouter 等），key 一律不进仓库。

---

## 4. 不纳入版本管理的文件/目录（Unmanaged）

以下内容**永远不要提交**（`.gitignore` 已覆盖，新增同类也要遵守）：

| 类别 | 路径/规则 |
| --- | --- |
| 密钥与环境变量 | `.env`、`.env.*`（保留 `.env.example`） |
| 官方 starter kit | `code/competitions/kddcup2026-data-agents-starter-kit/`（外部仓库，不复制入库，只保留说明 README） |
| 数据集大文件 | `code/competitions/datasets/*`（`*.zip` / `*.csv` / `*.db` 等） |
| 运行产物 | `artifacts/`、`runs/`、`outputs/`、`logs/`、`*.sqlite-journal` |
| 虚拟环境/构建 | `.venv/`、`venv/`、`__pycache__/`、`*.egg-info/`、`build/`、`dist/`、`uv.lock` |
| IDE/系统 | `.idea/`、`.vscode/`、`.DS_Store`、`Thumbs.db` |
| 临时/搜索产物 | `*_tree.json`、`*search*.json` |

**通用原则**：不确定是否会越权泄露的东西，一律不提交；宁缺勿滥。

---

## 5. 文档规范指北

- 仓库未显式规定文档目录时，通用知识/方法放入相应文档区即可。
- **项目专属学习文档**必须放在 `learning/PENN/` 内，并遵守 `learning/PENN/doc_agent.md` 的写作要求。
- 新增模型、服务商、密钥类变更属于敏感内容，登记配置但**不落库**。

---

## 6. 运行与验证

- 需要跑通验证时，优先用 `uv run`（仓库统一包管理器）。
- 改动代码后若存在 lint / typecheck / 测试命令，必须运行；没有则说明并询问。
