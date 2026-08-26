# 01 · Agent 主循环精读（react.py + model.py + runtime.py）

> 核心三问：循环怎么驱动？模型输出怎么解析？状态怎么流转？

## 1. ReAct 循环骨架（react.py:97-147）

```python
def run(self, task):
    state = AgentRuntimeState()
    for step_index in range(1, max_steps + 1):          # 硬上限
        raw = self.model.complete(self._build_messages(task, state))   # ① 问 LLM
        try:
            step = parse_model_step(raw)                 # ② 解析 JSON 协议 ⚙️P6
            result = self.tools.execute(task, step.action, step.action_input)  # ③ 执行工具
            state.steps.append(StepRecord(...))          # ④ 记录轨迹
            if result.is_terminal:                       # ⑤ answer 工具 → 结束
                state.answer = result.answer; break
        except Exception as exc:
            state.steps.append(StepRecord(action="__error__", ...))       # ⑥ 错误也进历史
    if state.answer is None:
        state.failure_reason = "did not submit answer within max_steps"   # ⑦ 步数耗尽
```

**关键机制逐个拆：**

### ① 消息构造 = 无状态的"重放"（_build_messages, react.py:83-95）

每次调用 LLM 都**从零重建全部消息**：

```
[system] 角色 + 规则 + 工具清单 + 输出示例
[user]   Question + 提示交表
[user]   Observation: 第1步工具结果     ← 历史以 user 消息回灌
[assistant] 第1步的原始输出
[user]   Observation: 第2步工具结果
...
```

- LLM 本身无记忆，**"记忆"= 把历史重放给它看**；
- 注意 assistant 消息存的是 `raw_response` 原文（含可能的错误格式）——让模型看到自己之前的错误，才有自我纠正的机会（实测 task_11 里 4 次解析错误就是这么自愈的）；
- **代价**：上下文线性膨胀，实测 17 步时 prompt 已 ~15K tokens（task.json 很小的情况下）。这是 v0.2 要解决的工程点。

### ② JSON 协议解析的三层容错（react.py:24-66）

```
raw_response
  → _strip_json_fence()      : 剥掉 ```json ...``` 围栏（:24-32）
  → _load_single_json_object(): raw_decode + 校验"后面不能还有内容"（:35-44）
  → 字段类型校验              : thought:str / action:非空str / action_input:dict（:51-59）
```

- `raw_decode` 允许前导空白但不允许前导文字——DeepSeek 加开场白就炸（本机补丁 P1 用 response_format=json_object 从服务端根治）；
- "只允许一个 JSON 对象"很严格：`{...}{...}` 或 `{...} 解释文字` 都拒绝；
- ⚙️P6：`JSONDecoder(strict=False)` 容忍字符串内的裸控制字符。

### ③ 失败也是一等公民（except 分支, react.py:122-137）

解析失败/未知工具不中断循环，而是记一条 `action="__error__"` 的 StepRecord，
observation 只含 `{"ok": false, "error": str(exc)}` 回灌给模型。
**但注意**：`model.complete()` 的网络异常在 try 之外（:100），会直接炸掉整个 run——官方没有做 LLM 调用的容错（我们补丁里加了 timeout+retries 缓解）。

### ④ 终止条件只有两个

| 出口 | 条件 | 结果 |
| --- | --- | --- |
| 正常 | `answer` 工具执行成功（is_terminal） | `state.answer = AnswerTable` |
| 失败 | 步数耗尽仍无 answer | failure_reason 固定文案 |

`succeeded` 属性（runtime.py:37-39）：answer 非空 且 无 failure_reason。

## 2. 模型层（model.py）

- `OpenAIModelAdapter`：薄封装，唯一职责是把消息列表发给 OpenAI 兼容端点并取回文本；
- `ScriptedModelAdapter`（:69-77）：测试用桩，按序吐预置响应——**依赖倒置的好例子**，agent 不依赖具体 SDK；
- ⚙️ 本机补丁：response_format=json_object / timeout=120s / max_retries=2 / max_tokens=2048 / token 用量打印。

## 3. 运行时数据结构（runtime.py，48 行全读完）

| 类 | 内容 | 用途 |
| --- | --- | --- |
| StepRecord | step_index/thought/action/action_input/raw_response/observation/ok | 单步快照 → trace.json 的最小单元 |
| AgentRuntimeState | steps 列表 + answer + failure_reason | 可变累积器 |
| AgentRunResult | task_id + answer + steps + failure_reason + succeeded 属性 | 循环出口产物 |

## 可改进点（自研 v0.x 输入）

1. 消息重放无截断 → 需要 observation 压缩/摘要策略；
2. complete() 异常会杀死整个任务 → 应降级为一条 error observation 重试；
3. 无 planning：纯反应式，复杂题容易绕路（冠军方案用四阶段+门控解决）；
4. `__error__` 连续多次时没有熔断（实测烧掉 15 步在同一类错误上）。
