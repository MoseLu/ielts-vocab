# Backend Microservices Atomic TODO

Last updated: 2026-04-10

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
- [待完成] Add Redis local runtime and shared config.
- [待完成] Add RabbitMQ local runtime and shared config.
- [已完成] Standardize internal request headers: `X-Request-Id`, `X-Trace-Id`, `X-User-Id`, `X-User-Scopes`, `X-Service-Name`.
- [已完成] Add shared internal service auth/JWT package for gateway-to-service calls.

## Phase B: Runtime Independence

- [已完成] Split browser ingress from domain services via `gateway-bff`.
- [已完成] Move `identity`, `learning-core`, `catalog-content`, `notes`, `ai-execution`, `tts-media`, `asr`, `admin-ops` into dedicated service entrypoints.
- [进行中] Remove service boot dependence on manually exported shell env.
- [已完成] Replace remaining service imports of monolith route modules with service-local transport layers.
- [进行中] Replace remaining service imports of mixed backend service modules with service-local application modules or shared SDKs. `identity / notes / admin-ops / learning-core / catalog-content` are already on service-local application modules; `identity` session/cookie/email helpers, `catalog-content` read/word pagination/confusable wrappers, `learning-core` library/progress/favorites/familiar wrappers, and `notes` word-note writes now live in `platform-sdk` instead of high-level backend service modules. `ai-execution` now uses service-local route files, a local module loader, and service-local application/support modules for `context/profile`, `assistant`, `custom-books`, and `practice`, with local implementations for `prompt/text/metric/summary helpers`, `learning context composition`, `assistant memory`, `related-note recall`, `tool input validation`, `tool execution helpers`, `session logging/review queue`, `wrong-words`, `quick-memory/smart-stats` sync flows, vocabulary-pool lookup, and listening-confusables indexing. `platform-sdk` no longer directly imports `services.ai_*`, `services.auth_session_helpers`, `services.books_catalog_service`, `services.books_confusable_service`, `services.books_progress_service`, `services.books_favorites_service`, or `services.books_familiar_service`. Remaining coupling is now concentrated in lower-level repositories, shared learner-profile/stat services, and provider/LLM adapters.
- [待完成] Separate `asr-service` HTTP and Socket.IO deployment contracts into explicit ports and config docs.
- [已完成] Add gateway readiness checks for critical downstream services.

## Phase C: Storage Separation

- [进行中] Move stateful services to dedicated PostgreSQL databases.
- [已完成] Define per-service table ownership matrix against current SQLAlchemy models.
- [进行中] Split shared SQLAlchemy model set into service-owned model modules.
- [已完成] Create service bootstrap/migration commands instead of global `db.create_all()`.
- [待完成] Add initial schema migration baseline per service.
- [待完成] Disable new writes to shared SQLite from split services after parity checks pass.
- [已完成] Migrate `identity-service` data from SQLite to `ielts_identity_service`.
- [已完成] Migrate `learning-core-service` data from SQLite to `ielts_learning_core_service`.
- [已完成] Migrate `catalog-content-service` data from SQLite/content files into `ielts_catalog_content_service` metadata tables where needed.
- [已完成] Migrate `ai-execution-service` current SQLite-backed runtime tables into `ielts_ai_execution_service`.
- [已完成] Migrate `notes-service` data into `ielts_notes_service`.
- [进行中] Migrate `admin-ops-service` transitional read-side shadow tables into `ielts_admin_ops_service`.

## Phase D: Messaging and Caching

- [待完成] Introduce Redis-backed rate limits, ephemeral speech session state, and cache keys.
- [待完成] Introduce RabbitMQ-backed outbox/event dispatch.
- [待完成] Add shared outbox table pattern for every write-owning service.
- [待完成] Add shared inbox/idempotency handling for event consumers.
- [待完成] Publish first event set:
  - `identity.user.registered`
  - `learning.session.logged`
  - `learning.wrong_word.updated`
  - `notes.summary.generated`
  - `tts.media.generated`
  - `ai.prompt_run.completed`
- [待完成] Build admin read models from events instead of shared table reads.

## Phase E: Gateway Narrowing

- [已完成] Browser `/api/*` compatibility now routes through `gateway-bff`.
- [待完成] Remove direct browser access assumptions from backend monolith startup.
- [进行中] Move auth context validation to gateway-issued internal headers/JWT.
- [待完成] Add timeout, retry, and circuit-breaker policy per downstream service.
- [待完成] Add streaming pass-through tests for AI and media endpoints under gateway.
- [待完成] Add `/socket.io` reverse-proxy story for the split ASR service in the microservice startup chain.

## Phase F: Monolith Exit

- [待完成] Stop using `backend/app.py` as the primary runtime in local development.
- [待完成] Keep `backend/app.py` only as a compatibility reference until all write paths leave SQLite.
- [待完成] Remove remaining monolith-only route registration not used by split services.
- [待完成] Replace monolith-only startup scripts with split-service orchestration as the default backend path.
- [待完成] Archive or retire shared-SQLite backup runtime for split services once all writes move to PostgreSQL.

## Immediate Execution Order

- [已完成] A1. Service-specific PostgreSQL env support.
- [已完成] A2. Project-owned local PostgreSQL cluster and per-service databases.
- [已完成] A3. Split-service env autoload.
- [已完成] A4. Local backend microservice orchestration script.
- [已完成] C1. Stateful service readiness checks against PostgreSQL.
- [已完成] C2. Service-local schema bootstrap/migration command.
- [已完成] C3. SQLite-to-PostgreSQL data export/import scripts per service.
- [待完成] D1. Redis local runtime and shared cache/session adapter.
- [待完成] D2. RabbitMQ local runtime and outbox/inbox base implementation.
