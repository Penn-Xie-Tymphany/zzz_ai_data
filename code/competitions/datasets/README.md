# 比赛数据集（不入库）

此目录被 `.gitignore` 忽略，存放下载的官方数据集。

## 获取方式

1. 打开官网 <https://dataagent.top/> → Benchmark / DataAgent-Bench 区块；
2. 下载 **Phase 1 Demo Dataset**（Google Drive 或百度网盘镜像均可）；
3. 解压到本目录，例如：

```
code/competitions/datasets/
└── public/
    └── input/
        ├── task_01/
        │   └── context/ ...
        └── task_11/
            └── context/ ...
```

## 注意

- 数据文件较大且官方持续更新，不要提交进 git；
- starter kit 的 dataset loader 默认路径若不同，以官方 README 为准，或在自研代码中用环境变量 `DATA_ROOT` 指向这里。
