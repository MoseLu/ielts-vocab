# Project Notes
Last updated: 2026-04-12 11:18:00 +08:00

## Repo Summary
- IELTS vocabulary learning web app with React 19 + TypeScript + Vite on the frontend and Flask + SQLite on the backend.
- Main scopes: `frontend/` for the frontend package, build configs, source, and e2e coverage; `backend/` for APIs and persistence; `vocabulary_data/` for book assets; and `docs/` for durable plans, audits, and runbooks.
- Runtime now treats split backend as the canonical local path: preview UI on `3002`, browser API ingress on `8000`, downstream services on `8101-8108`, and speech Socket.IO on `5001`.

## Working Agreements
- Treat repo text files as UTF-8 unless the file itself proves otherwise.
- Before using `apply_patch`, read exact target lines and anchor on stable ASCII or code structure.
- If a file shows encoding corruption, rewrite the whole logical block instead of stacking small mojibake patches.
- Keep tracked hand-edited text files at `<= 500` lines unless they are covered by the checked-in oversize baseline.
- Treat `vocabulary_data/**` and `pnpm-lock.yaml` as generated artifacts that are exempt from the `500`-line cap.
- Keep `pnpm check:file-lines` and `pnpm lint` green before submit; `pnpm build` and `pnpm test` now run the guardrail bundle automatically.
- Keep `pytest backend/tests/test_source_text_integrity.py -q` green after backend or text-heavy edits.
- Treat the remote cloud chain as canonical for domain/runtime bugs: `axiomaticworld.com -> nginx(:443/:80) -> active HTTP slot gateway-bff(:18000|:28000) -> downstream services(:18101-18108|:28101-28108)`, with `/socket.io` proxied to ASR Socket.IO on `:5001`.
- Use the local split runtime only for reproduction: preview UI on `3002`, browser API ingress on `8000`, downstream services on `8101-8108`, and speech Socket.IO on `5001`.
- When touching runtime startup, keep `start-project.bat` and `start-project.ps1` aligned with `frontend/vite.config.ts`, `nginx.conf.example`, and the real service ports.

## Current Focus
- Keep the post-Wave microservice baseline stable: normal split startup no longer exposes shared-`SQLite` override flags, service boot env loading is file-driven, tts/asr migration baselines are registered, gateway/internal auth is stricter, OSS artifact validation is green, and `scripts/repo_summary.py` is restored.
- Keep production-style local startup and proxy behavior stable after the speech-service split.
- Keep Ebbinghaus due-review counts consistent across stats, learner profile, and review queue by using the same UTC-safe time conversion path.
- Continue study-center and homepage visual polish without regressing desktop/mobile layout.
- Remaining post-cutover work is now primarily operational: code-side `admin / notes / ai` boundary cleanup is in place, the table audit is clean for normal split runtime, and the main unfinished item is the final remote release/deploy/preflight/smoke/storage-drill closeout.

## Latest Sync Notes
- Post-Wave closeout advanced again: [identity_transport.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/identity_transport.py) plus [identity_admin_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/identity_admin_application.py) now expose an internal `set-admin` contract for `admin-ops-service`, [identity_admin_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/identity_admin_internal_client.py), [admin_user_management_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/admin_user_management_application.py), and [admin_user_management_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_management_service.py) now route admin toggles through that contract with legacy fallback only for compat mode, [admin_projection_repository_support.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_projection_repository_support.py) now treats missing admin projection markers as a strict boundary instead of silently dropping to shared rows, [ai_context_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/ai_context_application.py) now returns an empty learner-profile snapshot in strict AI runtime instead of local shared-table fallback, and [service_table_plan.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/service_table_plan.py) now reports `admin-ops-service`, `notes-service`, and `ai-execution-service` with `transitional_tables: []` for the normal split-runtime audit.
- Closed Wave 5: [notes_summary_context_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_summary_context_repository.py) now blocks shared study-session/wrong-word fallback under strict `notes-service` runtime and only keeps that fallback for explicit legacy mode, [notes_summary_jobs_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/notes_summary_jobs_application.py) plus [notes_summary_job_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_summary_job_service.py) now surface the same `503 strict-internal-contract` boundary on sync/async summary generation, and [search_cache_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/search_cache_repository.py) now stores general-purpose web-search cache keys in Redis first with database fallback, which closes the last Wave 5 cache-key gap.
- Continued Wave 5 Redis-backed speech state adoption: [realtime_session_state_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_session_state_runtime.py) now persists transcript-aware session snapshots into Redis with bounded `partial_transcript` / `final_transcript` excerpts, [realtime_sessions.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_sessions.py) and [realtime_socketio.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_socketio.py) now keep those transcript fields updated across realtime ASR events, and [socketio_service.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/socketio_service.py) now exposes `/internal/sessions/<session_id>` for operator reads of the live session snapshot.
- Continued Wave 5 shared-read retirement on the `admin` HTTP surface: [admin_user_detail_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_detail_repository.py) now raises a service-boundary error instead of silently reading shared `UserBookProgress` / `UserChapterProgress` / `UserFavoriteWord` / `UserLearningEvent` rows when `learning-core-service` internal reads fail under strict split runtime, and [admin_overview_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_overview_service.py), [admin_user_management_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_management_service.py), [admin_overview_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/admin_overview_application.py), and [admin_user_management_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/admin_user_management_application.py) now surface that as explicit `503 strict-internal-contract` responses on `/api/admin/users` and `/api/admin/users/<id>`.
- Added a controlled Wave 5 projection cutover pack: [wave5_projection_cutover.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/wave5_projection_cutover.py) now runs the `admin / notes / ai` bootstrap flows and verifies marker readiness plus source/projected count parity in one place, [run-wave5-projection-cutover.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/run-wave5-projection-cutover.py) exposes it as an operator command, and a local run now passes with `admin users=2 study_sessions=578 wrong_words=1644`, `notes study_sessions=578 wrong_words=1644`, and `ai wrong_words=1644 daily_summaries=0`.
- Continued Wave 5 shared-read retirement on the `notes-service` fallback path: [learning_core_notes_context_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_notes_context_application.py) plus [learning_core_transport.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_transport.py) now expose `/internal/learning/notes-context/study-sessions` and `/internal/learning/notes-context/wrong-words`, [learning_core_notes_context_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_notes_context_internal_client.py) now gives `notes-service` typed snapshots for those routes, and [notes_summary_context_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_summary_context_repository.py) now prefers `projection -> internal` under strict split runtime and only drops to shared rows when explicit legacy fallback is enabled.
- Continued Wave 5 projection cutover hardening on the `notes` and `ai` read side: [notes_projection_bootstrap.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/notes_projection_bootstrap.py) plus [ai_projection_bootstrap.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/ai_projection_bootstrap.py) now backfill notes study-session/wrong-word and AI wrong-word/daily-summary projections while stamping service-owned cursor and bootstrap-marker rows, [bootstrap-notes-projections.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/bootstrap-notes-projections.py) plus [bootstrap-ai-projections.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/bootstrap-ai-projections.py) expose those flows as operator scripts, and [notes_summary_context_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_summary_context_repository.py), [ai_wrong_word_projection_support.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/ai_wrong_word_projection_support.py), and [ai_daily_summary_projection_support.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/ai_daily_summary_projection_support.py) now switch by explicit bootstrap markers instead of count parity.
- Hardened AI internal-call fallback against live local port interference: [learning_core_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_internal_client.py) and [catalog_content_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/catalog_content_internal_client.py) now raise on boundary-level `401/403/404/5xx` responses so `run_with_legacy_cross_service_fallback` can still drop to the local compatibility path during local runtime and test runs.
- Continued Wave 5 `admin detail` shared-read retirement on the personalization side: [learning_core_admin_detail_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_application.py) and [learning_core_transport.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_transport.py) now expose `/internal/learning/admin/favorite-words`, [learning_core_admin_detail_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_internal_client.py) now owns the admin-detail learning-core client snapshots, and [admin_user_detail_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_detail_repository.py) plus the admin user-management application/service now read favorite words internal-first with shared-row fallback only when `learning-core-service` is unavailable.
- Split the old oversize admin-detail client/test files back under the `500`-line guardrail: [learning_core_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_internal_client.py) now keeps only the generic learning-core client surface, admin-detail snapshots moved to [learning_core_admin_detail_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_internal_client.py), and the learning-core admin-detail internal-route coverage moved into [test_internal_service_auth_admin_favorites.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_internal_service_auth_admin_favorites.py), so `pnpm check:file-lines` is green again without adding new baseline exceptions.
- Continued Wave 5 `admin detail` shared-read retirement on the learning side: [learning_core_admin_detail_application.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_application.py), [learning_core_transport.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_transport.py), and [learning_core_internal_client.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_internal_client.py) now expose/use narrow internal read endpoints for book progress, chapter progress, and session word-sample events, and [admin_user_detail_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_detail_repository.py) now uses those internal reads first with local shared-read fallback when `learning-core-service` is unavailable.
- Continued Wave 5 `admin` shared-read retirement on the user directory side: [admin_user_directory_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_directory_repository.py) now serves directory reads from `AdminProjectedUser` once the bootstrap marker is present while still keeping owner writes on shared `User`, [auth_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/auth_repository.py) and `set-admin` now refresh the projected user snapshot on write, and [test_wave5_identity_admin_event_flow.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_wave5_identity_admin_event_flow.py) now locks projection-first directory reads plus projection refresh on profile/admin updates.
- Tightened the Wave 5 `admin` projection cutover contract: [admin_projection_repository_support.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_projection_repository_support.py) now switches user/session/wrong-word read models by explicit bootstrap marker cursors instead of comparing projection row counts against shared tables, and the related Wave 5 tests now lock that marker-driven behavior.
- Added a safe Wave 5 admin projection bootstrap path: [admin_projection_bootstrap.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/admin_projection_bootstrap.py) now backfills `AdminProjectedUser`, `AdminProjectedStudySession`, and `AdminProjectedWrongWord` from current shared tables while stamping the related `AdminProjectionCursor` rows, [bootstrap-admin-projections.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/bootstrap-admin-projections.py) exposes that flow as an operator script, and [test_admin_projection_bootstrap.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_admin_projection_bootstrap.py) locks the backfill plus idempotent refresh contract.
- Added the first Redis-backed ASR ephemeral-state slice: [realtime_session_state_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_session_state_runtime.py) now mirrors realtime session metadata into Redis with TTL-backed snapshots and active-session counting, [realtime_socketio.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_socketio.py) and [realtime_sessions.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_sessions.py) now sync that state across session lifecycle transitions, and [test_asr_realtime_session_state_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_asr_realtime_session_state_runtime.py) locks the Redis snapshot contract.
- Landed the first real Redis-backed Wave 5 workload: [identity_rate_limit_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/identity_rate_limit_runtime.py) now drives auth/email throttling through `Redis-first` counters with database fallback, [auth_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/auth_repository.py) now routes login, bind-email code, and forgot-password checks through that path, and [test_auth_rate_limiting.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/tests/test_auth_rate_limiting.py) now locks both Redis and DB-fallback behavior.
- Promoted the Wave 5 worker-aware deploy contract into the normal release path: [run-service.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/run-service.sh), [release-common.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/release-common.sh), and [smoke-check.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) are no longer waiting on a future rollout step, and the remaining Wave 5 closure work is broader shared-read retirement plus Redis-backed workload adoption.
- Added deploy-time split-service schema migration support in [deploy-release.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/deploy-release.sh) and [run-service-schema-migrations.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/run-service-schema-migrations.py), then decoupled the migration runner from app secrets so deploy bootstraps can run before service-specific secret material is loaded.
- Preserved frontend auth sessions across deploy restarts by tightening [AuthContext.tsx](/F:/enterprise-workspace/projects/ielts-vocab/frontend/src/contexts/AuthContext.tsx) and the shared storage helpers in [index.ts](/F:/enterprise-workspace/projects/ielts-vocab/frontend/src/lib/index.ts), with regression coverage in [AuthContext.test.tsx](/F:/enterprise-workspace/projects/ielts-vocab/frontend/src/contexts/AuthContext.test.tsx) and [index.test.ts](/F:/enterprise-workspace/projects/ielts-vocab/frontend/src/lib/index.test.ts).
- Added the Wave 5 remote worker deploy contract: [run-service.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/run-service.sh) now routes all outbox/projection workers through `ielts-service@<worker>`, [release-common.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/release-common.sh) now enables workers only when the target release supports them and disables them on rollback to older releases, and [smoke-check.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) now verifies worker systemd activity when the current release has worker support.
- Executed the Wave 5 remote broker rollout on `119.29.182.134`: `/etc/ielts-vocab/microservices.env` now carries the Redis/RabbitMQ baseline, `redis` plus `rabbitmq-server` are installed and active, and the new broker validation, preflight, and smoke chain all passed remotely against the deployed host.
- Fixed a first-install bug in [provision-broker-runtime.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/provision-broker-runtime.sh): the script now installs broker packages before requiring `redis-cli`, `rabbitmqctl`, and `rabbitmq-diagnostics`, so a clean remote host can bootstrap successfully.
- Added the Wave 5 remote broker rollout baseline: [provision-postgres.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/provision-postgres.sh) now writes canonical `REDIS_*` plus `RABBITMQ_*` settings into `/etc/ielts-vocab/microservices.env`, [install-cloud-runtime.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/install-cloud-runtime.sh) now installs and enables `redis` plus `rabbitmq-server`, [provision-broker-runtime.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/provision-broker-runtime.sh) now provisions the remote local-host broker baseline, and [validate-broker-runtime.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/validate-broker-runtime.sh) is now wired into remote validation.
- Tightened Wave 5 broker validation so missing broker env no longer hides behind code defaults: [validate_wave5_broker_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/validate_wave5_broker_runtime.py) now requires explicit broker settings, [backend/.env.microservices.local](/F:/enterprise-workspace/projects/ielts-vocab/backend/.env.microservices.local) now carries the local Redis/RabbitMQ baseline, and remote [preflight-check.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/preflight-check.sh) plus [smoke-check.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) now validate broker env, systemd units, and runtime connectivity before the HTTP smoke path.
- Closed the code-side Wave 4 storage/artifact parity tooling: shared-`SQLite` scoped-override restart records, remote storage drill plus rollback evidence flow, and `notes export`, `example-audio`, plus `word-audio` `OSS` validate/repair operators are now all documented and wired into the remote runbook.
- Added a Wave 5 `notes-service <- learning.wrong_word.updated` consumer path: `notes_projected_wrong_words` now materializes wrong-word facts from events, `start-microservices.ps1` now boots `notes-wrong-word-projection-worker`, and `notes_summary_context_repository` now prefers that projection once per-user state catches up.
- Added a Wave 5 `ai-execution-service <- notes.summary.generated` consumer path: `ai_projected_daily_summaries` now materializes notes summary facts from events, `start-microservices.ps1` now boots `ai-daily-summary-projection-worker`, `/internal/notes/summaries` is available for service-auth reads, and AI context now falls back to projected summaries when `notes-service` is unavailable.
- Added a Wave 5 `ai-execution-service <- learning.wrong_word.updated` consumer path: `ai_projected_wrong_words` now materializes wrong-word facts from events, `start-microservices.ps1` now boots `ai-wrong-word-projection-worker`, and AI wrong-word reads plus the `get_wrong_words` tool now fall back to that projection when `learning-core-service` is unavailable.
- Added a Wave 5 `notes-service <- ai.prompt_run.completed` consumer path: `notes_projected_prompt_runs` now materializes AI prompt-run facts from events, notes summary generation reads that projection into a new `当天 AI 使用痕迹` section, and `start-microservices.ps1` now boots `notes-prompt-run-projection-worker`.
- Added a Wave 5 `notes-service <- learning.session.logged` consumer path: `notes_projected_study_sessions` now materializes study-session context from events, `notes_summary_context_repository` prefers that projection once it catches up, and `start-microservices.ps1` now boots `notes-study-session-projection-worker`.
- Added Wave 5 `tts.media.generated` and `ai.prompt_run.completed` end-to-end local event flows with service-owned materialization tables, real outbox publisher workers, and admin projection workers, and exposed recent prompt-run plus TTS-media metrics in admin overview.
- `start-microservices.ps1` now boots `ai-execution-outbox-publisher`, `ai-wrong-word-projection-worker`, `ai-daily-summary-projection-worker`, `notes-study-session-projection-worker`, `notes-prompt-run-projection-worker`, and `admin-prompt-run-projection-worker` alongside the earlier Wave 5 workers.
- Split speech handling out of the main Flask app into `backend/speech_service.py` on port `5001`, and updated proxy/startup flow accordingly.
- Added quick-memory reconciliation before learning-stats fetches so newer local records reach the backend before dashboard reads.
- Fixed the due-review timezone skew that undercounted recently due words in `learning-stats` and `learner-profile`.

## Encoding & Patch Strategy
- Assume repo text files are UTF-8 unless the file itself proves otherwise.
- Before using `apply_patch`, read the exact target lines with line numbers and anchor on nearby clean ASCII or stable code structure.
- Prefer patching whole logical blocks over matching a single suspicious line when a file shows any text corruption.
- If `apply_patch` fails to match twice on the same area, stop matching the mojibake literally. Re-anchor on clean surrounding code, or rewrite the full function/component/doc block instead.
- Do not keep stacking partial edits onto a file that shows encoding corruption. Restore or re-read a clean base first, then replay the intended change.
- After any encoding-related fix, inspect the diff and confirm the file did not pick up unrelated text corruption.
- Keep the text-integrity regression green: `pytest backend/tests/test_source_text_integrity.py -q`.

## File Line Guardrail
- The hard cap is `500` lines for tracked hand-edited text files across app code, backend code, tests, scripts, docs, and config.
- `vocabulary_data/**` and `pnpm-lock.yaml` are explicitly exempt because they are generated data or lockfiles.
- Historical oversize files are frozen in `scripts/file-line-limit.config.json`. They are temporary exceptions, may not grow past their recorded baseline, and should be split down over time.
- `scripts/check-file-line-limits.mjs` is the enforcement gate. It fails when a new oversize file appears, when a baseline file grows, or when the baseline file is not cleaned up after a file drops back to `<= 500` lines.
- `frontend/eslint.config.mjs` mirrors the `500`-line cap for tracked JS/TS files, while letting the oversize baseline remain temporarily exempt until those files are split.
- `.github/workflows/ci.yml` runs both the file-line script and ESLint explicitly before frontend tests/build so the rule is enforced in CI, not just locally.

## Technology Stack
- Frontend: React 19 + TypeScript + Vite
- Styling: SCSS + CSS variables
- Validation: Zod runtime schemas in `frontend/src/lib/schemas.ts`
- Backend: Python Flask + SQLite
- Auth: JWT + localStorage
- Realtime: Socket.IO / WebSocket for speech

## Project Structure
```text
frontend/
- package.json              # Frontend package manifest
- vite.config.ts            # Frontend build/proxy config
- vitest.config.ts          # Frontend unit-test config
- playwright.config.ts      # Frontend e2e config
- index.html                # Vite HTML entry
- assets/                   # Static assets
- src/
  - app/                    # App router entry
  - components/
    - ui/                   # Base UI components
    - layout/               # Shared shell/layout pieces
    - practice/             # Practice feature components
  - contexts/               # Auth / Settings / Toast / AIChat
  - features/
    - vocabulary/hooks/     # Data hooks for books, words, progress, stats
    - ai-chat/              # AI chat feature
    - speech/               # Speech recognition feature
  - hooks/                  # Shared hooks
  - lib/                    # Schemas, helpers, sync logic, formatting
  - styles/                 # Global and page SCSS
 - tests/
   - e2e/                   # Playwright end-to-end coverage

backend/
- app.py                    # Compatibility monolith API on :5000
- speech_service.py         # Compatibility speech Socket.IO service on :5001
- models.py                 # Database models
- routes/                   # API route modules
- services/                 # Backend service logic
- tests/                    # Backend tests

apps/
- gateway-bff/             # Canonical browser ingress on :8000

services/
- */main.py                # Split backend services on :8101-8108
- asr-service/socketio_main.py # Canonical Socket.IO runtime on :5001

docs/
- architecture/             # Specs and audits
- governance/               # Product and UI governance logs
- milestones/               # Durable delivery snapshots
- operations/               # Runbooks and operator docs
- planning/                 # Design and implementation plans
- logs/submit/              # Append-only submit records

pnpm-workspace.yaml         # Root workspace orchestration
```

## Zod Validation
- Schema location: `frontend/src/lib/schemas.ts`
- Validation utilities: `frontend/src/lib/validation.ts`
- Form hook: `frontend/src/lib/useForm.ts`
- Auth, settings, toast, AI chat, and vocabulary hooks all validate inputs or API payloads through Zod-backed helpers.

## Key Features
1. Authentication and user profile management
2. Vocabulary books, chapters, and progress tracking
3. Practice modes: `smart`, `listening`, `meaning`, `dictation`, `radio`, `quickmemory`, `errors`
4. Guided study homepage and learner-profile driven recommendations
5. AI assistant, journal, and daily summary flows
6. Dedicated speech recognition service and TTS tooling

## Backend API
- `/api/auth`: register, login, logout, avatar, current user
- `/api/books`: books, chapters, words, progress
- `/api/progress`: legacy day-based progress
- `/api/ai`: learning stats, learner profile, quick memory, AI assistant, practice helpers
- `/api/notes`: notes, summaries, exports
- `/api/tts`: TTS audio and generation state
- `/api/admin`: admin capabilities

## Development
```bash
# Frontend
pnpm install
pnpm dev
pnpm build
pnpm preview
pnpm test:e2e

# Backend
cd backend
pip install -r requirements.txt

# Canonical split backend startup
powershell -ExecutionPolicy Bypass -File .\start-microservices.ps1

# Monolith compatibility rollback drill
powershell -ExecutionPolicy Bypass -File .\start-monolith-compat.ps1

# One-click local production-style startup
start-project.bat
```

## Test Account
- Dedicated test account for local/manual verification: username `admin`
- Password: `admin123`

## Production SSH Access
- Production SSH connection metadata is already tracked in `backend/.env`; when Codex needs remote access, read `PROD_SSH_HOST`, `PROD_SSH_USER`, and `PROD_SSH_KEY_PATH` or `PROD_SSH_PRIVATE_KEY_PATH` from that file first instead of assuming the local shell has no credentials.
- Treat `backend/.env` as sensitive: use it to resolve the SSH host, username, and local key-file path, but never echo private-key contents or unrelated secrets back to the user.
- Preferred PowerShell discovery snippet:
```powershell
$envPath = 'backend/.env'
$sshKey = (Get-Content $envPath | Where-Object { $_ -match '^PROD_SSH_(PRIVATE_)?KEY_PATH=' } | Select-Object -First 1).Split('=', 2)[1].Trim()
$remoteHost = (Get-Content $envPath | Where-Object { $_ -match '^PROD_SSH_HOST=' } | Select-Object -First 1).Split('=', 2)[1].Trim()
$remoteUser = (Get-Content $envPath | Where-Object { $_ -match '^PROD_SSH_USER=' } | Select-Object -First 1).Split('=', 2)[1].Trim()
ssh -i $sshKey -o StrictHostKeyChecking=accept-new "$remoteUser@$remoteHost" "hostname"
```
- Preferred production log commands after connecting:
```bash
sudo journalctl -u 'ielts-service@gateway-bff' -u 'ielts-service@learning-core-service' -u 'ielts-service@ai-execution-service' -n 200 --no-pager
sudo journalctl -u 'ielts-service@catalog-content-service' -n 200 --no-pager
```
- When a browser request fails only for logged-in users, inspect `gateway-bff`, `learning-core-service`, `ai-execution-service`, and `catalog-content-service` together before assuming the frontend auth flow is at fault.

## Remote Production Topology
1. `https://axiomaticworld.com/` terminates at the cloud nginx entrypoint on `119.29.182.134`
2. nginx serves the frontend build from the active release symlink under `/var/www/ielts-vocab/current`
3. nginx proxies `/api/*` to the active HTTP slot `gateway-bff` on `127.0.0.1:18000` or `127.0.0.1:28000`
4. `gateway-bff` fans out browser API traffic to the same-slot microservices on `18101-18108` or `28101-28108`
5. nginx proxies `/socket.io/*` directly to ASR Socket.IO on `127.0.0.1:5001`

When debugging domain issues, treat this remote chain as the deployment context instead of assuming any local tunnel is involved.

## Local Reproduction Topology
1. Vite preview serves the browser UI on `http://127.0.0.1:3002`
2. Local browser API ingress runs on `http://127.0.0.1:8000`
3. Split backend services run on `127.0.0.1:8101-8108`
4. Local `/socket.io/*` traffic goes to ASR Socket.IO on `127.0.0.1:5001`

## Browser APIs
- `speechSynthesis`: pronunciation playback
- `localStorage`: auth, settings, progress, quick-memory caches
- `WebSocket` / Socket.IO: realtime speech recognition
