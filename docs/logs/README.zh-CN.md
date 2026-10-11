# Logs 文档
Last updated: 2026-04-04 21:09:41 +08:00

本目录用于存放仅追加（append-only）的执行记录。

## 子目录

- `submit/`：commit-batch 提交记录以及类似的不可变日志

日志应记录「发生了什么」，而不是「接下来要做什么」。后续工作请写到 `docs/planning/`。
