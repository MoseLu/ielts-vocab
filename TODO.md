# TODO
Last updated: 2026-04-12 11:18:00 +08:00

## 进行中
- [进行中] 维持远程已部署 split backend 稳定，后续重构继续以 `gateway-bff -> services` 的线上链路、自动部署和 smoke check 为验收基线。
- [进行中] 做 post-cutover 最后收尾：准备远端正式 release/preflight/smoke/bounded storage drill，并完成发布后的文档与 closeout 记录归档。

## 待完成
- [待完成] 在远端执行最终正式 release：deploy、preflight、smoke、bounded storage drill、`run-wave5-projection-cutover --verify-only` 和 post-cutover 文档同步。

## 已完成
- [已完成] 完成 post-wave shared-`SQLite` 常态路径收口：`start-microservices.ps1` / `start-project.ps1` 不再暴露 `ALLOW_SHARED_SPLIT_SERVICE_SQLITE*` 正常入口，shared SQLite override 只保留 rollback/repair 专用路径。
- [已完成] 完成 service boot env 合同收口：`runtime_env.py` 支持 `BACKEND_ENV_FILE` + `MICROSERVICES_ENV_FILE` 两文件模型，测试覆盖本地/远端 env-file 加载约定。
- [已完成] 补齐 per-service migration baseline：`tts-media-service` 与 `asr-service` 已进入 `describe-service-migration-plan.py --json` 和 `run-service-schema-migrations.py --plan` 输出。
- [已完成] 完成 gateway/internal auth-context 收口第一阶段：非 `identity-service` 下游不再接收浏览器 `Authorization` / `cookie` 作为常态输入，internal clients 复用统一 header builder。
- [已完成] 完成 post-cutover `admin / notes / ai` 读侧收口：`admin-ops-service` 的 `set-admin` 已改走 `identity-service` 内部契约，`admin` user/session/wrong-word projections 缺失时在 strict split runtime 下改为明确边界错误，`ai-execution-service` 的 strict learner-profile 路径改为返回空快照而不是本地 shared-table fallback，表边界审计对 `admin / notes / ai` 现已清到 `transitional_tables: []`。
- [已完成] 完成 OSS 收口验证：notes export、example audio、word audio 的 validate/repair/API 测试通过，canonical object reference 路径保持 service-owned object key 约定。
- [已完成] 恢复 `scripts/repo_summary.py`，`bootstrap` 与 `changes --json` 已有回归测试并可继续作为 AGENTS/MILESTONE/TODO 同步入口。
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
