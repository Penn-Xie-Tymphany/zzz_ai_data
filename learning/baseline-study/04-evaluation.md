# 04 · 运行调度与产物/评测精读（runner.py + cli.py + dataset.py）

> 回答：任务怎么跑、产物长什么样、分数怎么算。

## 1. 调度模型（runner.py）

```
run_benchmark(:211)
  ├─ 单线程路径（workers=1 或注入 model/tools）: 顺序 for 循环（:235-249）
  └─ 多线程路径: ThreadPoolExecutor(max_workers)（:251-267）
       每个任务 → run_single_task → _run_single_task_with_timeout
         └─ multiprocessing.Process 隔离执行 + 超时击杀 ⚙️P4 改为 queue 轮询
```

- **两层并发**：线程池并行跑任务（I/O 密集，等 LLM 响应），进程隔离保证单题崩溃不拖垮全局；
- 默认 max_workers=4；CLI 用 rich 实时渲染 ok/fail/run/queue/speed 进度条（cli.py:169-254）；
- `progress_callback` 把完成事件推回 CLI 层——关注点分离干净。

### 超时机制的两层

| 层 | 参数 | 效果 |
| --- | --- | --- |
| 任务级 | task_timeout_seconds(1800) | 子进程整体墙钟超时，terminate→kill |
| 步数级 | max_steps(40) | ReAct 循环硬上限 |
| （工具级） | 固定 30s | execute_python 内部 |

⚠️ 本机踩坑记录：官方 `process.join(timeout)` 先于 `queue.get()` 是经典死锁模式
（子进程 feeder 线程未 flush、父进程干等）——表现为"答案生成了但永远不写文件"。
修复：改为 1 秒间隔轮询 `queue.get(timeout=1)`，取到结果再 join。

## 2. 产物契约（_write_task_outputs, :168-191）

每个任务的输出目录：

```
artifacts/runs/<run_id>/
├── summary.json                    ← 批量运行才有：总览+每任务状态
└── task_11/
    ├── trace.json                  ← 全轨迹（调试金矿）
    │   {task_id, answer, steps[{step_index,thought,action,action_input,
    │        raw_response,observation,ok}], failure_reason, succeeded}
    └── prediction.csv              ← 仅当 answer 存在：columns+rows 平铺成表
```

**trace.json 的价值**：事后可以完整回放 agent 的思考链——我们分析 DeepSeek 解析失败、
脏数据处理策略全靠它。自研系统应保留此设计。

⚙️P5 补丁：两处写文件显式 `encoding="utf-8"`（Windows GBK 默认编码会崩）。

## 3. 评测怎么算分

**starter kit 本身不含评测代码**（只有 gold.csv 在数据集里）。规则页口径：

```
对每张预测表 vs gold.csv：
  Recall = |预测列 ∩ gold列| / |gold列|          ← 列的 multiset 交集
  Penalty = 0.5 × (多余列数 / 你给的列数)
  Score = Recall − Penalty
micro = 所有列汇总算一次；macro = 每题得分取平均
```

关键性质（决定优化策略）：
1. **列是 multiset 比较**：行序无关、列名无关，但值要精确匹配；
2. **多给列被罚 0.5×占比**：猜 10 列只中 3 列 → Recall=0.3, Penalty=0.35 → Score=-0.05，倒赔！
   → 所以"宁缺勿滥"，有把握才多给；
3. 行数不对按 multiset 差集影响该列命中。

> 待办：自己写一个本地 eval 脚本对比 prediction.csv vs gold.csv（放 code/playground/），
> 这是 G2 阶段（50 题全量跑分）的前置工具。

## 4. 配置面速查（config.py + example yaml)

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| dataset.root_path | data/public/input | 数据根 |
| agent.model/api_base/api_key | - | OpenAI 兼容端点 |
| agent.max_steps | 16 | ⚙️ 本机调到 40（DeepSeek 步子细） |
| agent.temperature | 0.0 | 复现性 |
| run.max_workers | 4 | 并发任务数 |
| run.task_timeout_seconds | 600 | ⚙️ 本机调到 1800 |
