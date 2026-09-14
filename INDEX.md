# IELTS Vocabulary — Document Index (INDEX.md)

> Canonical document map for `products/ielts-vocab`. This file is the
> single source of truth for "where do I read or update X?" inside the repo.
> For cross-project relations, see `/Volumes/code/workspace/workspace.graph.json`.

Last updated: 2026-06-08

## Root documents (read first)

| File | Purpose | Owner | Update cadence |
|---|---|---|---|
| `README.md` | English project entrypoint, layout, run/verify commands | owner | when scope changes |
| `README.zh-CN.md` | Simplified Chinese counterpart of `README.md` | owner | synced with README |
| `AGENTS.md` | Root agent rules, boundaries, verification, doc read order | owner + control-plane | when rules change |
| `docs/state/CHANGELOG.md` | Keep-a-Changelog style release history | owner | every release |
| `docs/state/TODO.md` | P0/P1/P2 task list with requirement IDs and test cases | owner + control-plane | weekly |
| `docs/state/MILESTONE.md` | Evidence-backed milestone status snapshot | owner | per milestone close |
| `docs/milestone/` | Long-form Wave history (Wave 1-6+); supplemental to `docs/state/MILESTONE.md` | owner | per Wave close |
| `docs/state/PRD.md` | Product requirements, users, acceptance criteria, non-goals | owner | when scope changes |
| `docs/state/TDD.md` | Test/technical design, architecture assumptions, verification commands | owner + test-engineer | when test strategy changes |
| `INDEX.md` | This file | owner | when document map changes |
| `docs/governance/SECURITY.md` | Private operator channel, secret-handling policy | owner | on policy change |
| `docs/state/DEBUG.md` | Common debugging recipes (proxy, ASR, gateway, TTS) | owner | as needed |
| `docs/state/TEST_REPORT.md` | Latest test run summary | control-plane | per CI run |

## Architecture (under `docs/architecture/`)

- `Architecture.md` — top-level architecture overview
- `backend-layered-architecture.md` — repository / service / route layers
- `service-ownership-matrix.md` — service vs. table ownership
- `gateway-service-contracts.md` — gateway to split service contracts
- `domain-event-contracts.md` — outbox/inbox domain events
- `frontend-boundaries.md` — Web / mobile / admin client boundaries
- `multi-client-monorepo.md` — Web + mobile + admin client split
- `audits/` — periodic audits (table boundary, strict contract, etc.)
- `specs/realtime_waveform.md` (en mirror: `realtime_waveform.en.md`) — realtime waveform UI technical doc

## Governance (under `docs/governance/`)

- UI / product governance records
- Authority, ownership, and contribution rules
- Read first when changing UX, product surface, or contributor policy
- `docs/governance/SECURITY.md` (en mirror: `docs/governance/SECURITY.zh-CN.md`) — security policy

## Planning (under `docs/planning/`)

- Roadmap and forward-looking plans
- Should be read alongside `docs/state/MILESTONE.md` and `docs/state/TODO.md`

## Operations (under `docs/operations/`)

- Local run, deployment, proxy chain, drill, and rollback recipes
- Includes `nginx.conf.example` walkthrough and the production-like local proxy chain

## Milestone (under `docs/milestone/`)

- Per-milestone evidence, decisions, and drills
- Currently archived under Wave 1-6 historical entries

## Logs / Submit (under `docs/logs/submit/`)

- Submit-batch logs (created by `git-commit-batch` flow)
- `2026xxxx-xxxxxx-*.md` are immutable once written

## Project manifest (under `docs/`)

- `project-docs.manifest.json` — project doc ownership manifest (status: partial)
- `project-audit-2026-03-31.md` — last full project audit

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

- `apps/mobile` — Capacitor mobile shell (Android-first)
- `packages/app-core` — shared TypeScript / schema package
- `packages/platform-sdk` — shared Python platform SDK (gateway, services, Redis, RabbitMQ, outbox, projections)

## Vocabulary data

- `vocabulary_data/` — word books, chapter data, learning assets
- `reference-materials/raw/` — IELTS PDFs and audio (git-ignored, kept locally)

## Scripts and runtime

- `scripts/` — guard scripts, repo utilities, commit-batch helpers
- `services/` — split microservice startup helpers and shared env
- `start-project.sh` / `start-microservices.sh` / `start-lowmem.sh` / `start-monolith-compat.sh` — local canonical runtimes

## Source-of-truth resolution order

1. `README.md` and `README.zh-CN.md` for entrypoint narrative.
2. `docs/state/PRD.md` for product scope; `docs/state/TDD.md` for technical design and verification.
3. `AGENTS.md` for agent rules and edit boundaries.
4. `docs/state/MILESTONE.md` for current status; `docs/milestone/` for historical Wave detail.
5. `docs/state/TODO.md` for active work; `docs/state/CHANGELOG.md` for shipped history.
6. `docs/architecture/*` for deep design; `docs/operations/*` for run/ops; `docs/governance/*` for policy.

## Update discipline

- Update `INDEX.md` whenever a new top-level document is added or its owner changes.
- Update `project-docs.manifest.json` alongside `INDEX.md` so machine-readable consumers stay aligned.
- Every material change in this index should be reflected in `docs/state/CHANGELOG.md` if the change is user-visible.
