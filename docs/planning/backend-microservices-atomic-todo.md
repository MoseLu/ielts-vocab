# Backend Microservices Atomic TODO

Last updated: 2026-04-12 00:07:44 +08:00

## Goal

Upgrade the current split-compatible backend into a standard microservice backend with:

- service-owned runtime entrypoints
- service-owned PostgreSQL databases
- gateway-only browser ingress
- Redis and RabbitMQ for cross-service state and async work
- service-level readiness, observability, and local orchestration

## Phase A: Platform Baseline

- [已完成] Freeze service list and browser-compatible ownership boundaries.
- [已完成] Introduce a project-owned local PostgreSQL cluster for split services on `55432`.
- [已完成] Add service-specific database URL resolution keyed by `CURRENT_SERVICE_NAME`.
- [已完成] Generate one local PostgreSQL database and one role per service.
- [已完成] Add shared split-service env loading from `backend/.env` plus `backend/.env.microservices.local`.
- [已完成] Add one-command local startup for `gateway-bff + all backend services`, with target-port reservation during boot to avoid Windows dynamic-port collisions.
- [已完成] Add database-backed `/ready` checks for every stateful service.
- [已完成] Add Redis local runtime and shared config: [start-local-redis-microservices.ps1](/F:/enterprise-workspace/projects/ielts-vocab/scripts/start-local-redis-microservices.ps1), [local-redis-microservices.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/local-redis-microservices.md), and [redis_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/redis_runtime.py).
- [已完成] Add RabbitMQ local runtime and shared config: [start-local-rabbitmq-microservices.ps1](/F:/enterprise-workspace/projects/ielts-vocab/scripts/start-local-rabbitmq-microservices.ps1), [local-rabbitmq-microservices.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/local-rabbitmq-microservices.md), and [rabbitmq_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/rabbitmq_runtime.py).
- [已完成] Standardize internal request headers: `X-Request-Id`, `X-Trace-Id`, `X-User-Id`, `X-User-Scopes`, `X-Service-Name`.
- [已完成] Add shared internal service auth/JWT package for gateway-to-service calls.

## Phase B: Runtime Independence

- [已完成] Split browser ingress from domain services via `gateway-bff`.
- [已完成] Move `identity`, `learning-core`, `catalog-content`, `notes`, `ai-execution`, `tts-media`, `asr`, `admin-ops` into dedicated service entrypoints.
- [进行中] Remove service boot dependence on manually exported shell env.
- [已完成] Replace remaining service imports of monolith route modules with service-local transport layers.
- [已完成] Replace remaining service imports of mixed backend service modules with service-local application modules or shared SDKs. `identity / notes / admin-ops / learning-core / catalog-content` are already on service-local application modules; `identity` session/cookie/email helpers, `catalog-content` read/word pagination/confusable wrappers, `learning-core` library/progress/favorites/familiar wrappers, and `notes` word-note writes now live in `platform-sdk` instead of high-level backend service modules. `ai-execution` now uses service-local route files, a local module loader, and service-local application/support modules for `context/profile`, `assistant`, `custom-books`, and `practice`, with local implementations for `prompt/text/metric/summary helpers`, `learning context composition`, `assistant memory`, `related-note recall`, `tool input validation`, `tool execution helpers`, `session logging/review queue`, `wrong-words`, `quick-memory/smart-stats` sync flows, vocabulary-pool lookup, and listening-confusables indexing. `platform-sdk` no longer directly imports mixed high-level `services.*` modules outside explicit adapter and service-repository boundaries, and [test_platform_sdk_service_import_boundaries.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_platform_sdk_service_import_boundaries.py) now locks that constraint in regression coverage.
- [已完成] Separate `asr-service` HTTP and Socket.IO deployment contracts into explicit ports and config docs in [asr-http-socketio-contract.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/asr-http-socketio-contract.md) and [gateway-service-contracts.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/gateway-service-contracts.md).
- [已完成] Add gateway readiness checks for critical downstream services.
- [已完成] Re-run the Wave 2 closeout verification pack: `python -m compileall packages/platform-sdk/platform_sdk backend/services`, `pnpm check:file-lines`, `pnpm lint`, `pytest backend/tests -q` (`432 passed`), plus the read-only remote smoke flow for homepage, `GET /api/books`, `GET /api/tts/voices`, `GET /api/tts/word-audio/metadata?w=hello`, and Socket.IO polling on `/socket.io/?EIO=4&transport=polling`, all returning `200` on `2026-04-10`.

## Phase C: Storage Separation

- [进行中] Move stateful services to dedicated PostgreSQL databases.
- [已完成] Define per-service table ownership matrix against current SQLAlchemy models.
- [进行中] Split shared SQLAlchemy model set into service-owned model modules.
- [已完成] Create service bootstrap/migration commands instead of global `db.create_all()`.
- [待完成] Add initial schema migration baseline per service.
- [已完成] Add Wave 4 owned-table parity validation script and runbook: [validate_microservice_storage_parity.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/validate_microservice_storage_parity.py) and [wave4-storage-parity-runbook.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/wave4-storage-parity-runbook.md).
- [进行中] Disable new writes to shared SQLite from split services after parity checks pass. Guarded split services now reject the implicit shared fallback `backend/database.sqlite`; use `ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES=<service>` for a service-scoped drill, and reserve `ALLOW_SHARED_SPLIT_SERVICE_SQLITE=true` for an emergency global override only.
- [已完成] Migrate `identity-service` data from SQLite to `ielts_identity_service`.
- [已完成] Migrate `learning-core-service` data from SQLite to `ielts_learning_core_service`.
- [已完成] Migrate `catalog-content-service` data from SQLite/content files into `ielts_catalog_content_service` metadata tables where needed.
- [已完成] Migrate `ai-execution-service` current SQLite-backed runtime tables into `ielts_ai_execution_service`.
- [已完成] Migrate `notes-service` data into `ielts_notes_service`.
- [进行中] Migrate `admin-ops-service` transitional read-side shadow tables into `ielts_admin_ops_service`.
- [进行中] Move media and export artifacts onto service-owned OSS keys. `tts-media-service` example-audio now does OSS-first reads/writes in the split runtime with a local-cache backfill script at [backfill_example_audio_to_oss.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/backfill_example_audio_to_oss.py), and `notes-service` exports now emit OSS object references on `/api/notes/export` when object storage is configured.

## Phase D: Messaging and Caching

- [已完成] Introduce Redis-backed rate limits, ephemeral speech session state, and cache keys. `identity-service` auth/email throttling, `asr-service` transcript-aware realtime session snapshots, and `ai-execution-service` `SearchCache` now all use `Redis-first` state with bounded fallback paths, so Wave 5 no longer depends on SQL-primary or process-local-only cache/session workloads for these runtime surfaces.
- [已完成] Introduce RabbitMQ-backed outbox/event dispatch. Local broker startup, contract resolution, durable queue/inbox helpers, live publisher workers, admin projection consumers, and the first non-admin consumers (`notes-service <- learning.session.logged`, `notes-service <- learning.wrong_word.updated`, `notes-service <- ai.prompt_run.completed`, `ai-execution-service <- learning.wrong_word.updated`, `ai-execution-service <- notes.summary.generated`) are landed; remote `microservices.env` broker seeding, `install/provision` scripts, `preflight/smoke` broker validation, and the worker-aware deploy/restart/smoke contract are all already live on `119.29.182.134`.
- [已完成] Add shared outbox table pattern for every write-owning service via [eventing_models.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/model_definitions/eventing_models.py) and [service_table_plan.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/service_table_plan.py).
- [已完成] Add shared inbox/idempotency handling for event consumers via [outbox_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/outbox_runtime.py).
- [已完成] Publish first event set. The contract registry is checked in at [domain_event_contracts.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/domain_event_contracts.py), local emit plus `admin-ops-service` consume wiring is landed for `identity.user.registered`, `learning.session.logged`, `learning.wrong_word.updated`, `notes.summary.generated`, `tts.media.generated`, and `ai.prompt_run.completed`, `notes-service` consumes `learning.session.logged`, `learning.wrong_word.updated`, and `ai.prompt_run.completed`, and `ai-execution-service` consumes both `learning.wrong_word.updated` and `notes.summary.generated`, so the first contract set is complete locally and already carried by the worker-aware remote release path.
- [已完成] Build admin and other cross-domain read models from events instead of shared table reads. User, study-session, wrong-word, daily-summary, prompt-run, and TTS-media projections now have local event-driven rebuild plus bootstrap-marker cutover paths, [run-wave5-projection-cutover.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/run-wave5-projection-cutover.py) ties `admin / notes / ai` bootstrap plus verification together, `admin users/detail` now surface strict internal-contract errors instead of shared fallback under split runtime, and `notes-service` summary-context now stops at `projection -> learning-core internal` unless explicit legacy fallback is enabled.

## Phase E: Gateway Narrowing

Wave 6 is split here into two delivery seams: Wave 6A closes edge hardening at the gateway and ASR boundary, and Wave 6B promotes the split-service startup path into the canonical runtime contract.

- [已完成] Browser `/api/*` compatibility now routes through `gateway-bff`.
- [已完成] Remove direct browser access assumptions from backend monolith startup by switching `start-project.ps1`, `frontend/vite.config.ts`, `frontend/playwright.config.ts`, `nginx.conf.example`, and the runtime docs to the `gateway-bff :8000 -> services` contract, with static regression coverage in [test_split_runtime_contract.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_split_runtime_contract.py).
- [进行中] Move auth context validation to gateway-issued internal headers/JWT.
- [已完成] Add timeout, retry, and circuit-breaker policy per downstream service in [gateway_upstream.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/gateway_upstream.py), [http_proxy.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/http_proxy.py), and [gateway_browser_routes.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/gateway_browser_routes.py).
- [已完成] Add streaming pass-through tests for AI and media endpoints under gateway in [test_http_proxy.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_http_proxy.py), [test_gateway_bff_ai_proxy.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_gateway_bff_ai_proxy.py), and [test_gateway_bff_tts_proxy.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_gateway_bff_tts_proxy.py).
- [已完成] Add `/socket.io` reverse-proxy story for the split ASR service in the microservice startup chain, with the browser `POST /api/speech/transcribe -> asr-service:8106` and `/socket.io/* -> asr-socketio:5001` contract documented in [asr-http-socketio-contract.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/asr-http-socketio-contract.md).

## Phase F: Monolith Exit

Wave 6C starts only after Wave 6A and Wave 6B are green and the Wave 4/5 storage and infrastructure prerequisites are stable enough to retire the monolith safely.

Wave 6C acceptance is already closed; the remaining shared-SQLite backup-runtime item below is a post-cutover cleanup tail, not a blocker for the wave closeout.

- [已完成] Stop using `backend/app.py` as the primary runtime in local development.
- [已完成] Keep `backend/app.py` only as a compatibility reference for rollback drills and operator access while split services remain the canonical browser path.
- [已完成] Remove remaining monolith-only route registration not used by split services.
- [已完成] Replace monolith-only startup scripts with split-service orchestration as the default backend path.
- [待完成] Archive or retire shared-SQLite backup runtime for split services once all writes move to PostgreSQL.

## Immediate Execution Order

- [已完成] A1. Service-specific PostgreSQL env support.
- [已完成] A2. Project-owned local PostgreSQL cluster and per-service databases.
- [已完成] A3. Split-service env autoload.
- [已完成] A4. Local backend microservice orchestration script.
- [已完成] C1. Stateful service readiness checks against PostgreSQL.
- [已完成] C2. Service-local schema bootstrap/migration command.
- [已完成] C3. SQLite-to-PostgreSQL data export/import scripts per service.
- [已完成] D1. Redis local runtime and shared cache/session adapter.
- [已完成] D2. RabbitMQ local runtime, remote broker rollout, and outbox/inbox base implementation. The remote broker baseline is active on `119.29.182.134`, and the worker-aware release path is now part of the normal deploy chain.
- [已完成] E1. Close Wave 6A edge hardening: gateway timeout/retry/circuit-breaker policy, streaming pass-through coverage, and ASR HTTP plus Socket.IO contract docs. Targeted verification is green: `pytest backend/tests/test_http_proxy.py backend/tests/test_gateway_bff_ai_proxy.py backend/tests/test_gateway_bff_tts_proxy.py backend/tests/test_gateway_bff_readiness.py backend/tests/test_asr_service_api.py backend/tests/test_asr_socketio_service.py -q` (`28 passed`), `python -m compileall apps/gateway-bff packages/platform-sdk/platform_sdk services/asr-service`, `pnpm check:file-lines`, and `pnpm lint`.
- [已完成] E2. Close Wave 6B canonical runtime cutover: local startup, browser proxy defaults, e2e instructions, and remote rollout docs now all converge on the split-service runtime contract. Verification is green: `pytest backend/tests/test_split_runtime_contract.py backend/tests/test_source_text_integrity.py -q` (`5 passed`), `pnpm check:file-lines`, `pnpm lint`, and `pnpm build`.
- [已完成] F1. Close Wave 6C monolith retirement: browser route coverage is locked at `94/94`, local rollback drill and remote cutover smoke have both been exercised successfully, and `tts-admin` is frozen as the only rollback-only operator surface.
