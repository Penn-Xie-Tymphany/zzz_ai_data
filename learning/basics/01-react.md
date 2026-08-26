# 01 · ReAct 范式：从论文概念到官方代码

> 是什么：让 LLM 交替输出「推理（Thought）」和「行动（Action）」，用环境返回的「观察（Observation）」
> 继续推理，循环直到得出答案。
> 为什么重要：官方 baseline 的整个骨架就是它；理解了它，80% 的 agent 框架都能看懂。
> 和比赛的关联：DataAgent-Bench 的每一步 trace 就是一次 Thought→Action→Observation。

## 1. 论文核心思想（ReAct, Yao et al. 2022, arXiv:2210.03629）

对比三种范式：

```
仅推理 (CoT)      : Thought → Thought → ...        （会编造事实）
仅行动 (Act)      : Action → Action → ...          （没有规划，盲目试）
ReAct (本文)      : Thought → Action → Observation → Thought → ...
                    ↑ 推理指导行动，观察修正推理 ↑
```

人类类比：做事时"边想边做、做完看结果再想"——不是一口气想完，也不是闷头乱试。

## 2. 在官方代码中的落地（react.py:97-147）

一次循环 = 四个动作：

```python
raw = model.complete(messages)          # ① LLM 生成 {"thought":..., "action":...}
step = parse_model_step(raw)            # ② 解析出结构化指令
obs = tools.execute(task, action, args) # ③ 环境执行工具，返回观察
messages.append(observation)            # ④ 观察回灌 → 进入下一轮
```

对应论文里的要素：

| 论文概念 | 代码实体 | 位置 |
| --- | --- | --- |
| Thought | `step.thought` 字段 | react.py:51 |
| Action | `step.action` + `action_input` | react.py:52-53 |
| Environment | ToolRegistry（8 个工具） | registry.py |
| Observation | `{"ok":..., "tool":..., "content":...}` 回灌 | react.py:104-108 |
| 终止 | `answer` 工具 is_terminal | registry.py:100 |

## 3. 实测感受（task_11 trace 的启示）

1. **Thought 质量决定效率**：模型在 thought 里写清计划（"先读字典→再筛检查表→关联病人表"），
   后面步数就少；thought 含糊就会绕路重试；
2. **Observation 回灌是双刃剑**：错误信息回灌 → 模型自愈（4 次解析错误全部自愈）；
   但上下文线性膨胀（17 步 ≈15K tokens）→ 长任务需要截断/摘要；
3. **ReAct ≠ 只能线性**：比赛强调 DAG 式非线性推理（并行子查询+汇合），这是 baseline 没有的，
   也是冠军方案四阶段架构（PLAN→EXPLORE→ANSWER→VERIFY）的出发点——**先学懂 ReAct，再超越它**。

## 4. 一分钟实现清单（自研 my-data-agent v0.1 对照）

必须有的五件事：
- [ ] system prompt（角色+规则+工具说明+输出示例）
- [ ] 循环上限（max_steps）
- [ ] 解析器（宽容 + 错误回灌）
- [ ] 工具分发（dict[str, callable]）
- [ ] 终止动作（answer）+ 全程 trace 记录

参考：我们已经在 `code/solutions/my-data-agent/src/my_data_agent/` 里搭了骨架（agent.py/protocol.py）。
