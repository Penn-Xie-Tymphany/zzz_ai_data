# 比赛数据集（不入库）

此目录被 `.gitignore` 忽略，存放下载的官方数据集。

## 当前状态 ✅

- `demo_samples_0417.zip`（436MB）— **Phase 1 Demo Dataset**，已下载并解压到
  `../kddcup2026-data-agents-starter-kit/PHASE_1/data/public/`（官方默认读取路径）
- 共 **50 题**：easy=15、medium=23、hard=11、extreme=1
- 每题含 `task.json`（task_id/difficulty/question）+ `context/`（csv|json|db|doc + knowledge.md）
- demo 附带标准答案 `public/output/task_<id>/gold.csv`（正式评测的 hidden test 只有 input）
- 已验证：`uv run dabench status` → Public tasks: 50 ✅

## 官方下载渠道（备用）

| 数据集 | 渠道 |
| --- | --- |
| Phase 1 Demo | Google Drive: <https://drive.google.com/file/d/1c6u5WlFw4KV7CBRyXh5BvFYbKqxhBSbL/view> ・ 百度网盘: <https://pan.baidu.com/s/14MrxhShtuAjY9Z_jBMW_sg?pwd=bh3v>（提取码 bh3v） |
| Phase 2 Demo | Google Drive: <https://drive.google.com/file/d/1QItyxal97dv875j_on6rq3PE8qByj_SA/view> ・ 百度网盘: <https://pan.baidu.com/s/1RSMWkUVUvaHfC06Skt72gQ?pwd=x4ws>（提取码 x4ws） |

## 注意

- 数据文件较大且官方持续更新，不要提交进 git；
- zip 原包保留在本目录作为备份，解压产物在 starter kit 的 `PHASE_1/data/` 下。
