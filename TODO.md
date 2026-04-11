# TODO
Last updated: 2026-04-12 00:14:22 +08:00

## 进行中
- [进行中] 维持远程已部署 split backend 稳定，后续重构继续以 `gateway-bff -> services` 的线上链路、自动部署和 smoke check 为验收基线。
- [进行中] 做 post-cutover 收尾：逐项清掉 shared-`SQLite`、手工 env、migration baseline、transitional shadow tables、剩余 OSS 聚合物、gateway auth context 和文档自动化这些尾项，同时保持当前 split runtime 与线上链路稳定。

## 待完成
- [待完成] 归档或退役 split services 的 shared-`SQLite` backup runtime，把 rollback-only 数据兜底从日常运行面拿掉，并继续收紧 shared SQLite 的应急写入/回退面。
- [待完成] 去掉 service boot 对手工导出 shell env 的依赖，把 split services 的启动前置条件继续收口到稳定的 env/autoload 合同。
- [待完成] 为各服务补齐初始 migration baseline，避免 schema 仍部分依赖 `create_all` / bootstrap 语义。
- [待完成] 继续把 `admin-ops-service` 的 transitional read-side shadow tables 收口到真正 service-owned 的 PostgreSQL 读模型形态。
- [待完成] 继续把 media / export artifacts 收到 service-owned OSS keys，把仍带本地缓存或过渡路径的对象流彻底收口。
- [待完成] 完成 gateway-issued internal headers / JWT 的 auth context 收口，消除这条边界上的剩余过渡实现。
- [待完成] 补回或替换 `scripts/repo_summary.py`，恢复仓库总结文档的自动同步流程。

## 已完成
- [已完成] 完成 Wave 1，共享 helper coupling 第一轮抽离、远程生产基线冻结和剩余 `platform-sdk -> services.*` 耦合清单固化已经落地。
- [已完成] 完成 Wave 2，`learner_profile`、`learning_stats`、`notes_summary` 和 `llm provider adapter` 等共享支持层边界化已完成。
- [已完成] 完成 Wave 3：service-owned repositories、service-owned models、按服务 bootstrap、迁移基线，以及 AI 到 learning / notes / catalog 的 internal contracts 已落地；split runtime 默认也已切到 strict internal contract，backend 回归 `506 passed`。
- [已完成] 完成 Wave 4：已在远端 `119.29.182.134` 实跑 parity/repair storage drill、`notes-service` scoped shared-`SQLite` override restart、以及真实 rollback rehearsal；归档证据已写入 [20260411-072543-wave4-storage-drill.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260411-072543-wave4-storage-drill.md)、[20260411-072709-wave4-shared-sqlite-override-restart.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260411-072709-wave4-shared-sqlite-override-restart.md) 和 [20260411-072946-wave4-rollback-rehearsal.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260411-072946-wave4-rollback-rehearsal.md)。
- [已完成] 完成 Wave 5：本地/远端 `Redis`、`RabbitMQ`、`outbox/inbox`、worker-aware release、首批 `6` 条 domain event publisher/consumer、`admin/notes/ai` 事件投影、bootstrap-marker cutover、统一 cutover operator 都已落地；`notes-service` summary-context 与 `admin users/detail` 在 strict split runtime 下都已停止 shared fallback，`identity-service` 限流、`asr-service` transcript-aware realtime session snapshot、以及 `SearchCache` 都已切到 `Redis-first`，所以 Wave 5 的“经典微服务基础设施 + 事件读侧 + 缓存/瞬时状态”目标已经关单。
- [已完成] 完成本地 split backend 基础设施底座：每服务 `PostgreSQL` 已就位，本地 `Redis`、`RabbitMQ`、`outbox/inbox` 骨架已落地。
- [已完成] 完成 Wave 6A，`gateway-bff` 已补齐 per-downstream timeout / retry / circuit-breaker，ASR HTTP + Socket.IO 部署契约已固定。
- [已完成] 完成 Wave 6B，`start-project`、Vite dev/preview 代理、Playwright 默认入口、`nginx` 示例和运行文档已统一切到 `gateway-bff :8000 -> services` 的 canonical split runtime contract。
- [已完成] 完成 Wave 6C：browser cutover 默认只看 `gateway-bff` browser surface，route coverage 已锁到 `94/94`，远端 cutover smoke 与本地 rollback drill 都已实跑通过；剩余 `tts-admin` 五条路由已正式冻结为 rollback-only operator surface，不再作为 browser ingress 或 split-runtime 补齐目标。
- [已完成] 将最新 `dev`（含 Wave 5 worker-aware deploy contract）合并到 `main` 并重新部署生产，当前 `https://axiomaticworld.com/` 核心 smoke 正常。
