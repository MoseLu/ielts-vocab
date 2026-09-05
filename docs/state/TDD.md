# IELTS Vocabulary — Test / Technical Design Document (TDD)

> Companion to `PRD.md`. Describes the architecture assumptions, test
> strategy, verification commands, and risk cases for the canonical split
> microservice runtime in `products/ielts-vocab`.

Last updated: 2026-06-08

## 1. Architecture Assumptions

### 1.1 Runtime topology

```
Browser / Mobile
   ↓
gateway-bff :8000   (single browser-facing entry)
   ↓
identity / learning-core / catalog-content / ai-execution /
tts-media / asr / notes / admin-ops services :8101-8108
   ↓
per-service PostgreSQL  :55432 (db+role per service)
Redis  :56379           (throttling, transient state, cache)
RabbitMQ :5679          (outbox/inbox + workers)
   ↓
ASR Socket.IO :5001     (realtime speech)
```

### 1.2 Frontend assumptions

- React 19 + TypeScript + Vite, single SPA, Vite dev `:3020` and preview `:3002`.
- SCSS with CSS variables; Zod for schema validation.
- HttpOnly cookie + JWT refresh for auth.
- Capacitor-based mobile under `apps/mobile` with a Metro bundle and an Android shell.
- All non-trivial UI components are written under `frontend/src/components/` and re-exported through `index.ts` barrels.

### 1.3 Backend assumptions

- Flask (monolith compatibility) + FastAPI wrappers (gateway-bff + split services).
- Flask-SocketIO for realtime ASR.
- Strict split runtime is the default: services do **not** read each other's tables; they exchange through internal contracts and outbox events.
- Shared SQLite is no longer a normal entrypoint; it is only retained for rollback / repair.

### 1.4 Boundary contracts

- `docs/architecture/service-ownership-matrix.md` — service vs. table ownership.
- `docs/architecture/gateway-service-contracts.md` — gateway to split service contracts.
- `docs/architecture/domain-event-contracts.md` — outbox/inbox domain events.
- `docs/architecture/backend-layered-architecture.md` — repository / service / route layers.
- `docs/architecture/multi-client-monorepo.md` — Web + mobile + admin client split.

## 2. Test Strategy

### 2.1 Layers

| Layer | Tooling | Owner |
|---|---|---|
| Frontend unit / integration | Vitest + Testing Library | `frontend/src/**` |
| Frontend E2E | Playwright (`pnpm test:e2e`) | `frontend/e2e` |
| Mobile E2E | Maestro (`bash apps/mobile/scripts/run-maestro-e2e.sh`) | `apps/mobile` |
| Backend unit / integration | pytest (`backend/tests`) | `backend/**` |
| Backend smoke | per-service readiness + gateway smoke | `start-microservices.sh` + `tests/test_runtime_api_smoke.py` |
| Repo guards | `pnpm --dir frontend verify:repo-guards`, `scripts/check-*.mjs` | `scripts/` |

### 2.2 Test naming convention

- File pattern: `test_<module>.py`, `<Module>.test.ts(x)`, `<module>.spec.ts(x)`.
- Each new requirement ID gets a matching test file or case. The PRD AC table maps to specific test files (see "Acceptance Criteria" below).

### 2.3 Mandatory gates before commit

1. `pnpm --dir frontend lint`
2. `pnpm --dir frontend test`
3. `pnpm --dir packages/app-core test`
4. `pnpm --dir packages/app-core typecheck`
5. `pnpm --dir frontend build`
6. `pnpm --dir frontend verify:repo-guards`
7. `bash apps/mobile/scripts/run-maestro-e2e.sh smoke` (for any mobile-surface change)

## 3. Acceptance Criteria → Test Map

| AC ID | Test(s) |
|---|---|
| `PRD-AC-001` | `frontend/src/app/AppRoutes.practice.test.tsx`, `frontend/src/components/practice/PracticePage.testHarness.tsx` |
| `PRD-AC-002` | `backend/tests/test_listening_choice_distractors.py`, frontend `radio`/`listening` unit tests |
| `PRD-AC-003` | `backend/tests/test_learning_stats_aggregation.py`, `backend/tests/test_mode_performance_writes.py` |
| `PRD-AC-004` | `backend/tests/test_admin_projection_bootstrap.py`, `backend/tests/test_strict_internal_contract_boundary.py` |
| `PRD-AC-005` | `frontend/verify:repo-guards`, CI smoke |
| `PRD-AC-006` | `nginx.conf.example` + manual proxy walkthrough (recorded in `docs/operations/`) |
| `PRD-AC-007` | `scripts/release-closeout/` ticket linkage; not auto-tested |

## 4. Verification Commands

```bash
# Frontend
pnpm install
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend test:coverage
pnpm --dir frontend build
pnpm --dir frontend verify:repo-guards

# Shared package (app-core)
pnpm --dir packages/app-core typecheck
pnpm --dir packages/app-core test

# Mobile
pnpm --dir apps/mobile typecheck
pnpm --dir apps/mobile test
bash apps/mobile/scripts/run-maestro-e2e.sh smoke

# Backend (local)
python -m pytest -q backend/tests
python -m pytest -q backend/tests/test_admin_projection_bootstrap.py

# Repo guards
node scripts/check-doc-links.mjs
node scripts/check-file-line-limits.mjs
node scripts/check-design-token-usage.mjs
node scripts/check-style-discipline.mjs

# Doc integrity
test -f PRD.md && test -f TDD.md && test -f INDEX.md && test -f MILESTONE.md && \
  test -f TODO.md && test -f CHANGELOG.md && test -f AGENTS.md && \
  test -f README.md && test -f README.zh-CN.md
```

## 5. Risk Cases

| Risk | Trigger | Mitigation | Test / Drill |
|---|---|---|---|
| Frontend practice route broken on cancel | Cancel path regression | Lock state in `AppRoutes.practice.test.tsx` | `AppRoutes.practice.test.tsx` |
| Listening-choice distractors collapse to inflection-only | Distractor generation regression | Exclude `-ing` / `-ed` / plural variants | listening-choice unit tests + `CHANGELOG 1.2.6` |
| Strict split runtime falls back to shared table | Downstream service outage | Return `503 strict-internal-contract` instead of silent fallback | `test_strict_internal_contract_boundary.py` |
| `tts-admin` route drifts out of rollback-only | Operator accidentally promotes | Keep `tts-admin` operator surface rollback-only | Wave 6C smoke + `MILESTONE.md` note |
| Word-audio missing blocks quick recall | Asset pipeline miss | Cache fallback through gateway + TTS media paths | `CHANGELOG 1.2.6` regression coverage |
| Ambient proxy settings hijack internal service calls | `HTTP_PROXY` / `HTTPS_PROXY` env leakage | Force internal clients to ignore ambient proxy | `CHANGELOG 1.2.6` regression coverage |
| Mobile MAESTRO smoke fails on CI | Maestro infra drift | `bash apps/mobile/scripts/run-maestro-e2e.sh smoke` is the gate; pin Maestro version in `apps/mobile` |
| Project-domain proxy chain breaks | `ERR_SSL_PROTOCOL_ERROR` or `502` from local | Walk `nginx :80 -> vite preview :3002 -> gateway-bff :8000` end-to-end before declaring green | `nginx.conf.example` walkthrough |

## 6. Test Data and Seeding

- Local seed data: `vocabulary_data/` (git-tracked JSON / CSV word books).
- Reference PDFs / audio: `reference-materials/raw/` (git-ignored).
- Test databases: per-service Postgres on `127.0.0.1:55432`; per-test rollback with a transaction wrapper.

## 7. Out-of-Scope for TDD

- Performance benchmarks beyond what `test:coverage` already reports.
- Cross-cloud deploy (we standardize on the local proxy chain + remote host `119.29.182.134`).
- Visual regression (no snapshot framework adopted yet; tracked as a future hardening item).

---

*This TDD is auto-summary friendly. The owner preserves any manual `<!-- MANUAL -->` blocks at the bottom and the architecture assumptions section above; refresh only the test map and verification commands as the suite evolves.*
