# AGENTS.md — 仓库协作规范（共享，AI Agent 必读）

> 本文档是**仓库级共享规则**，适用于所有 AI 助手与协作者。
> 个人专属规则见各人自己的 `learning/<用户名>/doc_agent.md`，不在本文件里写死。

---

## 1. 仓库定位与使用者身份识别（重要，先读）

本仓库是 **KDD Cup 2026（Data Agents for Complex Data Analysis）** 的学习与自研工作区，**多人共用**。

- **共享部分**：根 `README.md`、`.gitignore`、本文件、`code/competitions/` 的说明等，谁都可以读改（敏感变更见 §3/§5）。
- **个人部分**：每人有独立工作区，互不覆盖：

```
code/solutions/<用户名>/     # 各自的自研方案（每人一个目录）
learning/<用户名>/           # 各自的学习文档（子目录结构由本人 doc_agent.md 约定）
```

**AI 必须主动确认当前使用者身份**：

1. 当这次操作涉及**个人目录**（创建/修改 `code/solutions/<用户名>/`、`learning/<用户名>/`）、
   或规则存在歧义、或个人规则与共享规则冲突时，**先询问「当前使用者是谁？」**；
2. 得到答复后，按对应 `<用户名>` 的目录约定与 `learning/<用户名>/doc_agent.md` 执行；
3. 在身份未知时：**不假设**、不默认放到某个人的目录、不套用某个人的专属规则，先问。

> 示例：使用者是 Penn，则其专属目录为 `code/solutions/penn_data_agent/` 与 `learning/PENN/`；
> 换成别人，则用其自己的目录。**具体是谁由询问结果决定，不写死在这里。**

---

## 2. 提交规则（Commit Rules）

1. **只有在用户明确要求时才 commit / push / 建 PR**。不得擅自提交。
2. 提交前必须检查：
   - `git status --short`：确认只暂存**预期要提交**的文件。
   - `git diff` / `git diff --cached`：确认没有误入无关改动。
3. 提交信息**简短、符合仓库既有风格**（用中文，`type: 摘要` 形式，如 `docs: xxx`、`refactor: xxx`）。
4. 不修改 git 全局/本地 config、不跳过 hooks、不做空提交、不 force-push。
5. 若提交被 hook 拒绝，修复后**新建提交**，不要 amend 失败的提交。
6. 提交前执行 §3 的敏感信息检查。发现密钥 → 立刻中止，改用占位符/环境变量。

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
| 数据集大文件 | `code/competitions/datasets/*`（`*.zip` / `*.csv` / `*.db` 等） |
| 运行产物 | `artifacts/`、`runs/`、`outputs/`、`logs/`、`*.sqlite-journal` |
| 虚拟环境/构建 | `.venv/`、`venv/`、`__pycache__/`、`*.egg-info/`、`build/`、`dist/`、`uv.lock` |
| IDE/系统 | `.idea/`、`.vscode/`、`.DS_Store`、`Thumbs.db` |
| 临时/搜索产物 | `*_tree.json`、`*search*.json` |

**通用原则**：不确定是否会越权泄露的东西，一律不提交；宁缺勿滥。

> 补充：官方 starter-kit（`code/competitions/kddcup2026-data-agents-starter-kit/`）已于 2026-09-05 作为**快照纳入版本管理**（官方 `@069ee5b` + DeepSeek 兼容补丁；**`PHASE_2/` 已删除，只做 Phase 1**，随 clone 一并获得）。该目录自带 `.gitignore`（覆盖其 `data/`、`artifacts/*`、`configs/*`、`.env.*`），**保护依然生效**：切勿把 demo 数据、运行产物、本地 config（含 api_key）提交进主库。
> 共享评测工具 `code/competitions/evaluation/`（官方同口径本地评分器）随仓库入库。

---

## 5. 文档规范指北

- 共享区域的通用变更（根 README、`.gitignore`、本文件、`code/competitions/` 说明）属共享部分，改动前与协作者确认；
- 各人的文档放 `learning/<用户名>/`，遵循其 `learning/<用户名>/doc_agent.md` 的写作要求；
- 新增模型、服务商、密钥类变更属于敏感内容，登记配置但**不落库**。

---

## 6. 运行与验证

- 需要跑通验证时，优先用 `uv run`（仓库统一包管理器）。
- 改动代码后若存在 lint / typecheck / 测试命令，必须运行；没有则说明并询问。