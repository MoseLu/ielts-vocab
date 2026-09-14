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
- [已完成] 完成 Wave 4：已在远端 `119.29.182.134` 实跑 parity/repair storage drill、`notes-service` scoped shared-`SQLite` override restart、以及真实 rollback rehearsal；归档证据已写入 [20260411-072543-wave4-storage-drill.md](/Volumes/code/workspace/products/ielts-vocab/docs/logs/submit/20260411-072543-wave4-storage-drill.md)、[20260411-072709-wave4-shared-sqlite-override-restart.md](/Volumes/code/workspace/products/ielts-vocab/docs/logs/submit/20260411-072709-wave4-shared-sqlite-override-restart.md) 和 [20260411-072946-wave4-rollback-rehearsal.md](/Volumes/code/workspace/products/ielts-vocab/docs/logs/submit/20260411-072946-wave4-rollback-rehearsal.md)。
- [已完成] 完成 Wave 5：本地/远端 `Redis`、`RabbitMQ`、`outbox/inbox`、worker-aware release、首批 `6` 条 domain event publisher/consumer、`admin/notes/ai` 事件投影、bootstrap-marker cutover、统一 cutover operator 都已落地；`notes-service` summary-context 与 `admin users/detail` 在 strict split runtime 下都已停止 shared fallback，`identity-service` 限流、`asr-service` transcript-aware realtime session snapshot、以及 `SearchCache` 都已切到 `Redis-first`，所以 Wave 5 的“经典微服务基础设施 + 事件读侧 + 缓存/瞬时状态”目标已经关单。
- [已完成] 完成本地 split backend 基础设施底座：每服务 `PostgreSQL` 已就位，本地 `Redis`、`RabbitMQ`、`outbox/inbox` 骨架已落地。
- [已完成] 完成 Wave 6A，`gateway-bff` 已补齐 per-downstream timeout / retry / circuit-breaker，ASR HTTP + Socket.IO 部署契约已固定。
- [已完成] 完成 Wave 6B，`start-project`、Vite dev/preview 代理、Playwright 默认入口、`nginx` 示例和运行文档已统一切到 `gateway-bff :8000 -> services` 的 canonical split runtime contract。
- [已完成] 完成 Wave 6C：browser cutover 默认只看 `gateway-bff` browser surface，route coverage 已锁到 `94/94`，远端 cutover smoke 与本地 rollback drill 都已实跑通过；剩余 `tts-admin` 五条路由已正式冻结为 rollback-only operator surface，不再作为 browser ingress 或 split-runtime 补齐目标。
- [已完成] 将最新 `dev`（含 Wave 5 worker-aware deploy contract）合并到 `main` 并重新部署生产，当前 `https://axiomaticworld.com/` 核心 smoke 正常。

---

# Prioritized Task List (P0 / P1 / P2)

> This section is a structured overlay on top of the narrative above. The
> narrative is preserved as the daily working log; this overlay is the
> machine-readable counterpart that the deep-init-pro documentation standard
> requires. Each P0/P1 item has a requirement ID (`REQ-IELTS-...`) and at
> least one test case.

## P0 — Must ship before final closeout

### REQ-IELTS-P0-001 — Final remote release / deploy / preflight / smoke / bounded storage drill
- **Owner**: solo owner
- **Source AC**: `PRD-AC-005`, `PRD-AC-006`, `PRD-AC-007`
- **Test case**: run `pnpm --dir frontend verify:repo-guards`, `bash apps/mobile/scripts/run-maestro-e2e.sh smoke`, then on remote `119.29.182.134` run `run-wave5-projection-cutover.py --verify-only` and the bounded storage drill; expected output: all gates green and storage drill report archived to `docs/logs/submit/`.
- **Evidence**: `docs/logs/submit/<release-timestamp>-*.md`; `CHANGELOG.md` entry for the release.

### REQ-IELTS-P0-002 — Lock feature-wish tickets to the release that ships them
- **Owner**: solo owner
- **Source AC**: `PRD-AC-007`
- **Test case**: for each `feature_wish` opened in the release window, verify a release-closeout ticket reference in `CHANGELOG.md` under the matching version; expected output: zero open feature-wish tickets without a release linkage.
- **Evidence**: `CHANGELOG.md` Operations block + ticket board snapshot.

### REQ-IELTS-P0-003 — Strict split runtime boundary remains `503 strict-internal-contract` (no silent shared fallback)
- **Owner**: solo owner
- **Source AC**: `PRD-AC-004`
- **Test case**: `python -m pytest -q backend/tests/test_strict_internal_contract_boundary.py backend/tests/test_admin_projection_bootstrap.py`; expected: all pass and zero `transitional_tables` reported by the table-boundary audit.
- **Evidence**: pytest output + `docs/audits/` table-boundary audit.

## P1 — Should ship in the next release window

### REQ-IELTS-P1-001 — Listening-choice distractors stay confusable
- **Owner**: solo owner
- **Source AC**: `PRD-AC-002`
- **Test case**: `python -m pytest -q backend/tests/test_listening_choice_distractors.py`; expected: every distractor is sound-alike or spelling-alike, never inflection-only.
- **Evidence**: pytest output; covered in `CHANGELOG 1.2.6`.

### REQ-IELTS-P1-002 — Word-audio cache fallback through gateway + TTS media paths
- **Owner**: solo owner
- **Source AC**: `PRD-AC-003`
- **Test case**: when canonical word audio is missing, the gateway must fall back to the TTS-media cache without blocking quick recall; test: `backend/tests/test_word_audio_fallback.py`.
- **Evidence**: pytest output; covered in `CHANGELOG 1.2.6`.

### REQ-IELTS-P1-003 — Internal service clients stay off ambient proxy
- **Owner**: solo owner
- **Source AC**: `PRD-AC-005`
- **Test case**: with `HTTP_PROXY` / `HTTPS_PROXY` set to a non-local value, internal service calls still resolve to `127.0.0.1`; test: `backend/tests/test_internal_clients_ignore_ambient_proxy.py`.
- **Evidence**: pytest output; covered in `CHANGELOG 1.2.6`.

### REQ-IELTS-P1-004 — `tts-admin` 5 routes stay rollback-only
- **Owner**: solo owner
- **Source AC**: `PRD-AC-006`
- **Test case**: `backend/tests/test_tts_admin_rollback_only.py` confirms the 5 routes are not in the browser cutover set; expected: 0 routes in browser cutover.
- **Evidence**: pytest output; `MILESTONE.md` Wave 6C note.

## P2 — Future hardening

### REQ-IELTS-P2-001 — Visual regression for `frontend/src/components/`
- **Owner**: solo owner
- **Status**: not started; no snapshot framework adopted.
- **Test case**: add a storybook + visual diff harness; currently blocked on framework choice.

### REQ-IELTS-P2-002 — Daily summary export to PDF
- **Owner**: solo owner
- **Status**: not started; currently Markdown-only.
- **Test case**: export to PDF and verify the layout matches the Markdown version.

### REQ-IELTS-P2-003 — Promote `tts-admin` out of rollback-only
- **Owner**: solo owner
- **Status**: deferred; requires owner sign-off.
- **Test case**: not yet defined.

## Zero-context handoff governance

### Completed migration

- **Problem**: The project documentation manifest did not provide enough structured context for a new contributor to identify entrypoints, commands, environment contracts, current work, troubleshooting, decisions, or verification evidence.
- **Solution**: Migrated `docs/project-docs.manifest.json` to version 2 and aligned it with the actual product, split-runtime, documentation, and workspace contracts.
- **Expected result**: A contributor can start from the manifest, follow the declared read order, locate the real entrypoints, and choose a safe setup, health, verification, or smoke command without rediscovery.
- **Acceptance**: The manifest parses as JSON, contains every required v2 field, references existing local paths, contains no secret values, and records fresh safe-smoke evidence dated `2026-06-11`.
- **Evidence**: `docs/project-docs.manifest.json`; `CHANGELOG.md`; fresh manifest/path validation and `pnpm --dir frontend verify:repo-guards` output.
- **Dependencies**: `AGENTS.md`, `README.md`, `INDEX.md`, `PRD.md`, `TDD.md`, `MILESTONE.md`, workspace relationship graph.
- **Status**: Completed on 2026-06-11.

### Ongoing freshness

- **Problem**: Runtime topology, current work, environment variables, contracts, and verification commands can drift as the product evolves.
- **Solution**: Review the v2 manifest whenever an entrypoint, service, required variable, contract, milestone, TODO priority, or verification command changes.
- **Expected result**: Zero-context onboarding remains accurate for the current checkout rather than becoming a one-time snapshot.
- **Acceptance**: Each material onboarding change updates the manifest, TODO status, and changelog together; verification remains `verified` only when the recorded commands have fresh evidence.
- **Evidence**: Future diffs in `docs/project-docs.manifest.json`, `TODO.md`, and `CHANGELOG.md`, plus dated verification evidence.
- **Dependencies**: Maintainers and agents completing the existing documentation update discipline.
- **Status**: Ongoing.
