# 02 · 工具系统精读（registry.py + filesystem.py + sqlite.py + python_exec.py）

> 8 个工具 = agent 的手和眼。本文回答：每个工具的协议是什么？安全边界在哪？

## 1. 工具注册表模式（registry.py）

```python
ToolSpec(name, description, input_schema)   # 给模型看的"说明书"
handlers: dict[str, ToolHandler]            # 名字 → 处理函数（:183-192）
```

- `describe_for_prompt()`（:117-123）把 specs 渲染成文本注入 system prompt——**工具即文档，单一事实源**；
- `execute()`（:125-128）就是个带 KeyError 的字典分发；
- `answer` 是唯一 `is_terminal=True` 的工具，且在注册层就做形状校验（:83-97）：columns 必须非空字符串列表、每行长度必须等于列数。

**8 个工具速查**：

| 工具 | 输入 | 返回 content 关键字段 | 实现位置 |
| --- | --- | --- | --- |
| list_context | max_depth=4 | root, entries[{path,kind,size}] | filesystem.py:20 |
| read_csv | path, max_rows=20 | columns, rows(≤20), row_count | filesystem.py:45 |
| read_json | path, max_chars=4000 | preview, truncated | filesystem.py:69 |
| read_doc | path, max_chars=4000 | preview, truncated | filesystem.py:80 |
| inspect_sqlite_schema | path | tables[{name, create_sql}] | sqlite.py:12 |
| execute_context_sql | path, sql, limit=200 | columns, rows(≤200), truncated | sqlite.py:36 |
| execute_python | code | success, output(stdout), stderr, error? | python_exec.py:103 |
| answer | columns, rows | status=submitted + **终止** | registry.py:83 |

## 2. 安全边界（三个层次，很值得抄）

### 层次一：路径逃逸防护（filesystem.py:10-17）

```python
candidate = (context_dir / relative_path).resolve()
if context_root not in candidate.parents and candidate != context_root:
    raise ValueError("Path escapes context dir")
```

`../../etc/passwd` 这类路径直接被拒——agent 的所有文件访问都被锁死在任务目录内。

### 层次二：SQL 只读双保险（sqlite.py）

1. **白名单前缀检查**（:37-39）：只允许 select/with/pragma 开头；
2. **只读连接**（:7-9）：`file:...?mode=ro` URI 模式——就算白名单漏了，数据库层面也写不进去；
3. 结果截断：`fetchmany(limit+1)` 多取一行判断 truncated（:44-46），最多回灌 200 行。

### 层次三：Python 子进程沙箱（python_exec.py）

```
execute_python_code()                     主进程
  └─ multiprocessing.Process              独立进程跑代码（:112）
       ├─ os.chdir(context_root)          工作目录切到 context（:89）
       ├─ _capture_process_streams()      fd 级 stdout/stderr 重定向到临时文件（:14-65）
       ├─ exec(code, namespace)           直接执行（:91）
       └─ queue.put(success/output...)    结果回传
  join(timeout=30s) → 超时 terminate（:125-133）
```

要点：
- **30 秒硬超时 + 进程隔离**：死循环/崩溃不影响主 agent；
- fd 级重定向（os.dup2）比替换 sys.stdout 更彻底——连 C 扩展的输出都能抓到；
- 注意：这**不是**安全沙箱（没禁网络、没限文件系统），隔离目的是稳定性而非安全性。比赛环境里 context 是可信数据，够用。

## 3. 预览哲学：防上下文爆炸的设计

所有读取工具都遵循同一契约：

```
返回预览 + truncated 标志，默认额度小（20行/4000字符）
→ 模型想看更多？自己调工具加大参数，或者用 execute_python 精准提取
```

实测意义：task_330 的 CSV 有 279MB，agent 只可能通过 read_csv(max_rows=20) 看结构、再用 SQL/python 取数——**工具设计强制了正确的大数据习惯**。

## 可改进点

1. `read_csv_preview` 用 `list(reader)` 全量读进内存再切片（filesystem.py:48）——279MB 文件会占内存，应流式读前 N+1 行；
2. `read_doc_preview` 对 extreme 的 286KB 文档只能看开头 4000 字符，中间内容靠 python 绕路取——官方留的空档，正是检索/分块增强点（v0.2）；
3. 工具结果没有 token 预算管理，全靠各工具默认值兜底。
