# 03 · Prompt 工程精读（prompt.py，60 行）

> 官方 prompt 只有一个文件、三个函数。本文拆解它解决什么问题、怎么组合。

## 1. 三段式组装（build_system_prompt, :38-47）

```
最终 system prompt =
    REACT_SYSTEM_PROMPT（角色+7条规则）      ← :8-23
  + "Available tools:" + describe_for_prompt() ← registry 注入
  + RESPONSE_EXAMPLES（2 个 few-shot 示例）   ← :25-35
  + 结尾再强调一次输出契约                     ← :45-46
```

## 2. REACT_SYSTEM_PROMPT 的规则设计（:13-22）

```
1. 先用工具检查 context 再回答          → 防瞎猜
2. 答案只能来自工具观察                  → 防幻觉（grounding）
3. 任务只有调了 answer 才算完成           → 明确终止语义
4. answer 必须带 columns 和 rows         → 输出形状
5. 每轮恰好一个 JSON 对象                 → 协议约束
6-7. 用 ```json 围栏包裹，前后无其他文字   → 解析友好
```

**观察**：规则 1/2 是"反幻觉三件套"里的两条；规则 5-7 全部服务于解析器——
prompt 的每一句都在为下游解析的确定性服务，没有一句废话。

## 3. Few-shot 示例的选择（:25-35）

只给了两个例子：
1. `list_context`——最常见的开场动作；
2. `answer`——最关键的终止动作，且示例里直接展示了 `columns` + 嵌套 `rows` 的准确格式。

**没有给 execute_python 的例子**——这是官方 prompt 的一个缺口：模型写多行 Python 时最容易把 JSON 搞坏
（实测两种死法：裸换行 → strict 报错；双引号不转义 → ',' delimiter 报错）。
⚙️ 本机补丁 P8 补了一个带 `\n` 转义的多行代码示例 + 两条转义规则（Rule 8/9），实测错误率显著下降。

## 4. 任务提示与观察回灌

### build_task_prompt(:50-55)

极简两行：Question + "路径相对 context/" + 提醒交表。
难度、题号等元数据**不告诉模型**——避免"难题就该多想几步"之类的先验干扰（也可能只是简化）。

### build_observation_prompt(:58-60)

```python
f"Observation:\n{json.dumps(observation, indent=2)}"
```

工具结果原样 JSON 化塞进 user 消息。注意：
- 成功时含完整 content（可能很大）；失败时只含 `{"ok": false, "error": ...}`；
- **错误信息原文回灌是自我纠正的关键**——模型能看到 "Expecting ',' delimiter: line 3..." 这种具体报错，
  才知道往哪个方向修（实测 task_11 中 4 次解析错误全部自愈于此机制）。

## 5. 可改进点（自研 v0.x 输入）

1. 无动态预算注入：可以在 prompt 里告知剩余步数，让模型学会收敛；
2. 无 observation 截断策略：长结果应摘要后再回灌；
3. 规则可以加"连续解析失败 N 次就简化输出结构"的自救指令；
4. 冠军方案思路：按阶段裁剪 prompt（EXPLORE 阶段隐藏 answer 工具，防过早交卷）。
