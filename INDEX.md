# IELTS Vocabulary — Document Index (INDEX.md)

> Canonical document map for `products/ielts-vocab`. This file is the
> single source of truth for "where do I read or update X?" inside the repo.
> For cross-project relations, see `/Volumes/code/workspace/workspace.graph.json`
> or `workspace-project show ielts-vocab`.

Last refreshed: 2026-10-11 (R3-B post-archive INDEX content rebuild.
Prior M18 commit `0124e095` timestamp-only refreshed this file; this
revision replaces the stale architecture/operations body with the
post-archive inventory. Body line count is held under 250.)

## Root documents (read first)

| File | Purpose | Owner | Update cadence |
|---|---|---|---|
| `README.md` / `README.zh-CN.md` | English / Chinese entrypoint, layout, run/verify commands | owner | when scope changes |
| `AGENTS.md` | Root agent rules, boundaries, verification, doc read order | owner + control-plane | when rules change |
| `INDEX.md` | This file | owner | when document map changes |
| `docs/HANDOFF.md` | Current work, commands, contracts, troubleshooting, freshness | owner + control-plane | per Wave / per session |
| `docs/state/CHANGELOG.md` | Keep-a-Changelog style release history | owner | every release |
| `docs/state/TODO.md` | P0/P1/P2 task list with requirement IDs and test cases | owner + control-plane | weekly |
| `docs/state/MILESTONE.md` | Evidence-backed milestone status snapshot | owner | per milestone close |
| `docs/state/PRD.md` | Product requirements, users, acceptance criteria, non-goals | owner | when scope changes |
| `docs/state/TDD.md` | Test/technical design, architecture assumptions, verification commands | owner + test-engineer | when test strategy changes |
| `docs/state/DEBUG.md` | Common debugging recipes (proxy, ASR, gateway, TTS) | owner | as needed |
| `docs/state/TEST_REPORT.md` | Latest test run summary | control-plane | per CI run |
| `docs/governance/SECURITY.md` | Private operator channel, secret-handling policy | owner | on policy change |

## Active services (current inventory)

Source of truth: `workspace-project show ielts-vocab`. Backing code under
`services/<name>/` (split runtime) plus `backend/` (monolith compat) and
`frontend/` (web client).

| Service / capability | Owner | Backing path |
|---|---|---|
| `gateway-bff` | gateway | `backend/app.py`, `services/gateway-bff` |
| `identity-service` | auth | `services/identity-service` |
| `learning-core-service` | learning | `services/learning-core-service` |
| `catalog-content-service` | content | `services/catalog-content-service` |
| `ai-execution-service` | AI | `services/ai-execution-service` |
| `tts-media-service` | media | `services/tts-media-service` |
| `asr-service` (+ `realtime-asr-socket` on 5001) | speech | `services/asr-service`, `backend/services/asr_service.py` |
| `notes-service` | notes | `services/notes-service` |
| `admin-ops-service` | admin | `services/admin-ops-service` |
| `ielts-learning-app` (web client) | frontend | `frontend/`, `apps/mobile/` |
| `upload-asr-api` | speech | `backend/app.py` upload routes |
| `mac-bridge` | mac-app | `apps/mac-bridge` (out-of-tree Vite/Express runtime) |

Cross-project contracts consumed: `ai-capability`, `minimax-tokenplan`, `ollama-local` (all optional at runtime).

## Architecture (under `docs/architecture/`)

Live documents after M18 archive (2026-10-11). Eight older architecture
specs now live under `docs/milestone/2026-q2-architecture-archive/`.

- `README.md` / `README.zh-CN.md` — folder convention + current specs list
- `audits/architecture-audit.md` — periodic architecture audit
- `audits/2026-06-07-gemma27b-code-review-frontend-nav-popover.md` — code-review record
- `specs/realtime_waveform.md` (en: `realtime_waveform.en.md`) — realtime waveform UI technical doc
- `specs/2026-03-28-tts-batch-generation-design.md` — TTS batch generation design
- `specs/2026-04-09-shared-aliyun-oss-sdk.md` — shared Aliyun OSS SDK contract
- `specs/2026-05-05-practice-mode-data-flow-roadmap.md` — practice / review / game / progress / mastery / session / stats / todo data-flow roadmap
- `specs/templates/` — reusable architecture-spec templates

Historical (read-only, do not edit): `docs/milestone/2026-q2-architecture-archive/` — `Architecture.md`, `backend-layered-architecture.md`, `service-ownership-matrix.md`, `gateway-service-contracts.md`, `domain-event-contracts.md`, `frontend-boundaries.md`, `multi-client-monorepo.md`, `service-table-boundary-audit.md`.

## Operations (under `docs/operations/`)

Live operator runbooks after M18 archive. Ten older operation docs now
live under `docs/milestone/2026-q2-operations-archive/`.

- `README.md` / `README.zh-CN.md` — folder convention
- `agent-browser-guide.md` — agent browser tooling for QA
- `cloud-microservices-deployment.md` — cloud deployment runbook
- `domain-routing.md` — domain and subdomain routing (incl. `ielts.axiomaticworld.com`)
- `frontend-automation-setup.md` — local frontend automation setup
- `local-page-load-performance-report-2026-05-01-1840.md` — perf snapshot
- `local-ui-api-browser-test-report-2026-05-01.md` — UI/API browser test snapshot
- `production-api-full-test-report-2026-04-30.md` — production API test snapshot

Historical (read-only, do not edit): `docs/milestone/2026-q2-operations-archive/` — `asr-http-socketio-contract.md`, `local-postgres-microservices.md`, `local-rabbitmq-microservices.md`, `local-redis-microservices.md`, `lowmem-consolidated-runtime.md`, `release-closeout-checklist.md`, `remote-production-baseline.md`, `ticket-driven-release-workflow.md`, `wave4-storage-parity-runbook.md`, `wave6c-cutover-validation.md`.

## Governance, planning, milestone, logs

- `docs/governance/` — UI / product governance records, authority and ownership rules, `SECURITY.md`.
- `docs/planning/` — forward-looking roadmap; read with `docs/state/MILESTONE.md` and `docs/state/TODO.md`.
- `docs/milestone/` — per-milestone evidence, decisions, drills; current Wave 1-6 historical entries plus Q2 archives.
- `docs/logs/submit/` — submit-batch logs from `git-commit-batch` (gitignored flat `.md` and dated subdirs).
- `docs/project-docs.manifest.json` — project doc ownership manifest (status: partial).
- `docs/project-audit-2026-03-31.md` — last full project audit.

## Frontend layout (`frontend/src/`)

- `app/` — route entry, app-level providers
- `components/` — page and UI components
- `composables/` — page-level composables
- `contexts/` — Auth / Settings / Toast / AIChat
- `features/` — domain features
- `hooks/` — shared hooks
- `lib/` — schema, utilities, local sync
- `styles/` — page styles
- `tests/` — unit and integration tests

Top runtime dependencies (from `frontend/package.json`): `react ^19.2.4`,
`react-dom ^19.2.4`, `react-router-dom ^7.13.1`, `@tiptap/react ^3.24.0`,
`socket.io-client ^4.8.3`. Top dev deps: `@types/react ^19.2.14`,
`@playwright/test ^1.58.2`, `msw ^2.12.14`,
`@testing-library/react ^16.3.2`,
`@testing-library/user-event ^14.6.1`.

## Backend layout (`backend/`)

- `app.py` — monolith compatibility entry, default port 5000
- `speech_service.py` — speech service entry, default port 5001
- `models.py` / `model_definitions/` — data models
- `routes/` — HTTP / Socket.IO route layer
- `services/` — service / repository / provider adapter layer
- `tests/` — backend tests
- `README.md` — backend architecture and layering
- `API.md` — API index

## Apps and packages

- `apps/mobile` — Capacitor mobile shell (Android-first), Maestro E2E under `apps/mobile/scripts/`
- `packages/app-core` — shared TypeScript / schema package
- `packages/platform-sdk` — shared Python platform SDK (gateway, services, Redis, RabbitMQ, outbox, projections)

## Vocabulary data

- `vocabulary_data/` — word books, chapter data, learning assets
- `reference-materials/raw/` — IELTS PDFs and audio (gitignored, kept locally)

## Scripts and runtime

- `scripts/` — guard scripts, repo utilities, commit-batch helpers, cloud deploy (`scripts/cloud-deploy/`)
- `services/` — split microservice startup helpers and shared env (`requirements.lock.txt`, `requirements.txt`)
- `start-project.sh` / `start-microservices.sh` / `start-lowmem.sh` / `start-monolith-compat.sh` — local canonical runtimes

## Build / verify commands

From `package.json` (root) — narrowest meaningful set:

- Dev runtime: `pnpm dev` (Mac local app) / `pnpm preview`
- Frontend build: `pnpm build`
- Lint: `pnpm lint` (frontend)
- Frontend tests: `pnpm test` / `pnpm test:e2e` / `pnpm test:coverage`
- Mobile: `pnpm mobile:android`, `pnpm mobile:test`, `pnpm mobile:typecheck`
- Mobile E2E: `pnpm mobile:e2e:smoke` / `pnpm mobile:e2e:android`
- Shared package: `pnpm app-core:test` / `pnpm app-core:typecheck`
- Cross-client verify: `pnpm verify:clients`
- Repo guards: `pnpm verify:repo-guards`
- Doc discipline: `pnpm check:docs` / `pnpm check:file-lines` / `pnpm check:design-tokens` / `pnpm check:style-discipline`

Index-level canonical verification (from `workspace-project show ielts-vocab`):

- `pnpm --dir frontend verify:repo-guards`
- `python -m pytest backend/tests/test_speech_transcribe.py backend/tests/test_speech_socketio.py`

## Source-of-truth resolution order

1. `README.md` and `README.zh-CN.md` for entrypoint narrative.
2. `docs/state/PRD.md` for product scope; `docs/state/TDD.md` for technical design and verification.
3. `AGENTS.md` for agent rules and edit boundaries.
4. `docs/state/MILESTONE.md` for current status; `docs/milestone/` for historical Wave detail and Q2 archives.
5. `docs/state/TODO.md` for active work; `docs/state/CHANGELOG.md` for shipped history.
6. `docs/architecture/*` for live design; `docs/operations/*` for live run/ops; `docs/governance/*` for policy.
7. `docs/milestone/2026-q2-{architecture,operations}-archive/` for historical, read-only design and runbook material.

## Update discipline

- Update `INDEX.md` whenever a new top-level document is added or its owner changes.
- Update `project-docs.manifest.json` alongside `INDEX.md` so machine-readable consumers stay aligned.
- Every material change in this index should be reflected in `docs/state/CHANGELOG.md` if the change is user-visible.
- M18 doc-cleanup moved 10 operations + 8 architecture files into `docs/milestone/2026-q2-{operations,architecture}-archive/`; if a future change re-promotes any of them to live status, move the file back and refresh the corresponding body section here.