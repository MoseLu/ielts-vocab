# TODO
Last updated: 2026-04-11 15:31:28 +08:00

## 进行中
- [进行中] 推进 Wave 5：本地 `Redis`、`RabbitMQ`、`outbox/inbox` 已接通 `identity.user.registered`、`learning.session.logged`、`learning.wrong_word.updated`、`notes.summary.generated`、`tts.media.generated`、`ai.prompt_run.completed` 的真实 publisher；`admin` read model 六条链已落地，`notes-service <- learning.session.logged`、`notes-service <- learning.wrong_word.updated`、`notes-service <- ai.prompt_run.completed`、`ai-execution-service <- learning.wrong_word.updated`、`ai-execution-service <- notes.summary.generated` 也已分别落地到 `notes_projected_study_sessions`、`notes_projected_wrong_words`、`notes_projected_prompt_runs`、`ai_projected_wrong_words`、`ai_projected_daily_summaries`，其中 AI wrong-word read/tool、AI context、notes summary context 都已开始接 projection fallback；远端 `119.29.182.134` 上的 `Redis/RabbitMQ` 已经实装、broker 校验已通过，deploy/restart/smoke 代码也已支持 worker units，下一步是发一版真正包含这些 worker entrypoints 的 release 并继续收 shared-read。
- [进行中] 维持远程已部署 split backend 稳定，后续重构继续以 `gateway-bff -> services` 的线上链路、自动部署和 smoke check 为验收基线。

## 待完成
- [待完成] 发一版包含 Wave 5 worker entrypoints 和新的 worker-aware `run-service`/deploy contract 的 release，把远端首批 worker/outbox publisher 真正纳入 systemd 发布链，并收掉依赖 shared table 的过渡读路径。
- [待完成] 补回或替换 `scripts/repo_summary.py`，恢复仓库总结文档的自动同步流程。

## 已完成
- [已完成] 完成 Wave 1，共享 helper coupling 第一轮抽离、远程生产基线冻结和剩余 `platform-sdk -> services.*` 耦合清单固化已经落地。
- [已完成] 完成 Wave 2，`learner_profile`、`learning_stats`、`notes_summary` 和 `llm provider adapter` 等共享支持层边界化已完成。
- [已完成] 完成 Wave 3：service-owned repositories、service-owned models、按服务 bootstrap、迁移基线，以及 AI 到 learning / notes / catalog 的 internal contracts 已落地；split runtime 默认也已切到 strict internal contract，backend 回归 `506 passed`。
- [已完成] 完成 Wave 4：已在远端 `119.29.182.134` 实跑 parity/repair storage drill、`notes-service` scoped shared-`SQLite` override restart、以及真实 rollback rehearsal；归档证据已写入 [20260411-072543-wave4-storage-drill.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260411-072543-wave4-storage-drill.md)、[20260411-072709-wave4-shared-sqlite-override-restart.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260411-072709-wave4-shared-sqlite-override-restart.md) 和 [20260411-072946-wave4-rollback-rehearsal.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260411-072946-wave4-rollback-rehearsal.md)。
- [已完成] 完成本地 split backend 基础设施底座：每服务 `PostgreSQL` 已就位，本地 `Redis`、`RabbitMQ`、`outbox/inbox` 骨架已落地。
- [已完成] 完成 Wave 6A，`gateway-bff` 已补齐 per-downstream timeout / retry / circuit-breaker，ASR HTTP + Socket.IO 部署契约已固定。
- [已完成] 完成 Wave 6B，`start-project`、Vite dev/preview 代理、Playwright 默认入口、`nginx` 示例和运行文档已统一切到 `gateway-bff :8000 -> services` 的 canonical split runtime contract。
- [已完成] 完成 Wave 6C：browser cutover 默认只看 `gateway-bff` browser surface，route coverage 已锁到 `94/94`，远端 cutover smoke 与本地 rollback drill 都已实跑通过；剩余 `tts-admin` 五条路由已正式冻结为 rollback-only operator surface，不再作为 browser ingress 或 split-runtime 补齐目标。
- [已完成] 将最新 `dev` 合并到 `main` 并重新部署生产，当前 `https://axiomaticworld.com/` 核心 smoke 正常。
