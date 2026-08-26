# 05 · Python 并发基础：读官方源码前必须补的一课

> 是什么：GIL、线程 vs 进程、Queue 的正确用法。
> 为什么重要：官方代码用了**两层并发**（ThreadPoolExecutor + multiprocessing），
> 而我们踩的最深的坑（任务永久卡死）正是 multiprocessing Queue 的经典死锁。
> 和比赛的关联：runner.py（调度层）+ python_exec.py（沙箱执行）都依赖这些概念。

## 一、GIL 与两种并发模型

| 模型 | 关键字 | 受 GIL 限制？ | 适用场景 |
| --- | --- | --- | --- |
| 多线程 `threading` / `ThreadPoolExecutor` | 共享内存，轻量 | ✅ 同一时刻只有一个线程执行 Python 字节码 | **I/O 密集**：等网络（LLM API）、等磁盘 |
| 多进程 `multiprocessing` / `ProcessPool` | 独立内存空间，重 | ❌ 每进程有独立 GIL | **CPU 密集**或需要隔离/强杀的场景 |

agent 场景的典型分工（官方代码正是这么做的）：
- **线程池跑多任务**：每个任务大部分时间在等 LLM API 响应（I/O），线程足够，还能共享 model 客户端；
- **子进程跑单任务/用户代码**：要超时强杀、要防崩溃传染——只有进程能 `terminate()/kill()`。

## 二、官方代码的两层并发（对照阅读）

```
runner.py:251  ThreadPoolExecutor(max_workers=4)     ← 外层：4 个任务并行
  └─ 每个任务 → _run_single_task_with_timeout(:132)
       └─ multiprocessing.Process                    ← 内层：单题在独立进程里跑
            目的1: task_timeout_seconds 到点可 terminate/kill（:145-151）
            目的2: 任务崩溃不影响主调度进程

python_exec.py:112  execute_python 也是同样套路
  └─ 独立进程 exec(模型写的代码) + 30s 超时强杀        ← 防死循环拖垮 agent
```

## 三、⚠️ 我们踩过的坑：multiprocessing.Queue 死锁

官方原代码（runner.py 修复前）：

```python
process.start()
process.join(timeout)          # ① 先干等子进程结束
...
result = queue.get()           # ② 结束后才取结果
```

问题：`queue.put(大对象)` 由子进程里的**后台 feeder 线程**异步序列化传输。
子进程主逻辑结束后，feeder 可能还没把数据刷完；而父进程在 join 上干等，
形成"父等子退、子等队列清"的僵局。**Python 官方文档明确警告不要这样做。**

实测表现：task_11 明明在第 17 步生成了答案，但 trace/prediction.csv 永远不落盘，
任务卡满 timeout 才被标记失败。

正确模式（⚙️P4 补丁后）：

```python
while True:
    try:
        result = queue.get(timeout=1.0)   # 以取到结果为主信号
        break
    except Empty:
        if not process.is_alive(): break   # 进程死了没结果 → 异常路径
        if 超时: break                      # 墙钟到点 → 击杀路径
process.join(timeout=5.0)                  # 此时才收尾
```

**口诀：先 get 后 join；join 只用来收尸，不用来等待。**

## 四、其他容易不知道的点

1. `daemon=True` 线程随主进程退出被硬杀——适合后台心跳，不适合承载要写盘的数据；
2. 子进程在 Windows 上是 **spawn** 方式启动（重新 import 主模块），所以官方把子进程入口写成独立函数 `_run_single_task_in_subprocess`；
3. `queue.empty()` 是不可靠的竞态判断（官方旧代码恰好还用了它），用 `get(timeout=...)` 的异常代替；
4. 线程池里抛异常不会立刻可见，攒在 `future.result()` 里——`as_completed` 循环里 `future.result()` 一旦有异常会在这里浮出（runner.py:263）。

## 五、对自研项目的启示

- v0.1 单机顺序跑即可，不需要并发；
- 但 execute_python 必须从第一天就放子进程（防模型写出死循环）；
- 如果做批量评测，抄 runner 的"线程池 + 子进程隔离 + queue 轮询"三件套即可，不要自己发明。
