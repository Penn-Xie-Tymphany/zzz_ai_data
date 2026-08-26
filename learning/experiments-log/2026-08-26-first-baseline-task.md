# 2026-08-26 · 首次跑通官方 Baseline（task_11）

## 目的
验证「DeepSeek deepseek-chat + 官方 ReAct baseline + 本地 demo 数据集」全链路可用。

## 配置
- 代码：官方 starter kit PHASE_1（含 8 处本机补丁，见 `learning/baseline-study/01-patches-for-deepseek.md`）
- 数据集：Phase 1 demo 50 题
- 模型：deepseek-chat（v4-flash），temperature=0，max_tokens=2048，max_steps=40，task_timeout=1800s

## 结果

| 指标 | 值 |
| --- | --- |
| task_11 (easy) | ✅ succeeded，prediction 与 gold **完全一致** |
| 步数 / 耗时 | 22 步 / 72s |
| 错误步 | 4 次（JSON 解析类），全部自愈 |

## 失败/踩坑归因（修复过程 = 6 连环）
| # | 现象 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | 全部步骤 __error__ | 前导文字破坏严格 JSON 解析 | response_format=json_object |
| 2 | 任务超时但 trace 0 步 | 单次调用无限挂起 | timeout=120s+retries |
| 3 | 有答案不落盘、永久卡死 | mp Queue+join 经典死锁 | 先 get 后 join |
| 4 | 写 trace 崩溃 | Windows GBK 默认编码 | 显式 utf-8 |
| 5 | 大量 "Invalid control character" | 字符串内裸换行 | strict=False |
| 6 | "Expecting ',' delimiter" 循环 | 代码双引号未转义 | prompt 规则+few-shot |

## 结论
链路全通。下一步：`run-benchmark --limit 5` 看 easy 题通过率，再决定是否全量 50 题（预估成本可忽略，耗时 ~1h）。
