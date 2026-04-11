# Project Notes
Last updated: 2026-04-11 15:29:44 +08:00

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
- Treat the local production-style chain as canonical for runtime bugs: `natapp -> nginx(:80) -> vite preview(:3002)` for UI, `/api` to `gateway-bff :8000`, downstream fan-out to `:8101-8108`, and `/socket.io` to speech service `:5001`.
- When touching runtime startup, keep `start-project.bat` and `start-project.ps1` aligned with `frontend/vite.config.ts`, `nginx.conf.example`, and the real service ports.

## Current Focus
- Keep Wave 5 event-driven read-side moving: local outbox publisher plus consumer chains now cover `identity.user.registered`, `learning.session.logged`, `learning.wrong_word.updated`, `notes.summary.generated`, `tts.media.generated`, and `ai.prompt_run.completed`, with `notes-service` now projecting study-session, prompt-run, and wrong-word context and `ai-execution-service` now projecting wrong-word plus daily-summary context from events; remote broker runtime is live and validated on `119.29.182.134`, deploy/restart/smoke code now supports remote worker rollout too, and the remaining closure work is releasing those worker entrypoints remotely plus broader shared-read retirement.
- Keep production-style local startup and proxy behavior stable after the speech-service split.
- Keep Ebbinghaus due-review counts consistent across stats, learner profile, and review queue by using the same UTC-safe time conversion path.
- Continue study-center and homepage visual polish without regressing desktop/mobile layout.

## Latest Sync Notes
- Added the Wave 5 remote worker deploy contract: [run-service.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/run-service.sh) now routes all outbox/projection workers through `ielts-service@<worker>`, [release-common.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/release-common.sh) now enables workers only when the target release supports them and disables them on rollback to older releases, and [smoke-check.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) now verifies worker systemd activity when the current release has worker support.
- Verified the current deployed host does not yet contain the worker entrypoint files in `/opt/ielts-vocab/current`, so remote workers were not force-started out of band; they will come up through the normal release path on the next deploy that includes the new worker-aware `run-service` contract.
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
- The current working tree includes an uncommitted homepage hero background polish in `frontend/src/styles/pages/study-center.scss`.

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

## Local Proxy Topology
1. Vite preview serves the browser UI on `http://127.0.0.1:3002`
2. Local `nginx` listens on port `80` and proxies UI traffic to `3002`
3. `natapp` exposes `https://axiomaticworld.com` and forwards to local `:80`
4. `nginx` proxies `/api/*` to `gateway-bff` on `127.0.0.1:8000`
5. `gateway-bff` fans out browser API traffic to split services on `127.0.0.1:8101-8108`
6. `nginx` proxies `/socket.io/*` directly to ASR Socket.IO on `127.0.0.1:5001`

When debugging domain issues, treat the whole chain as the deployment context instead of blaming only frontend code.

## Browser APIs
- `speechSynthesis`: pronunciation playback
- `localStorage`: auth, settings, progress, quick-memory caches
- `WebSocket` / Socket.IO: realtime speech recognition
