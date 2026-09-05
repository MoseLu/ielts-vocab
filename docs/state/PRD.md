# IELTS Vocabulary — Product Requirements Document (PRD)

> Source of truth for the user-facing scope of `products/ielts-vocab`. This PRD
> covers the canonical split microservice runtime (`gateway-bff -> services`).
> Runtime changes that affect user-visible behavior must be reflected here.

Last updated: 2026-06-08

## 1. Identity

- **Product name**: IELTS Vocabulary
- **Working short name**: `ielts-vocab`
- **Owner**: Axi Core Projects / solo owner (`1208136885@qq.com`)
- **Canonical path**: `/Volumes/code/workspace/products/ielts-vocab`
- **Workspace position**: `products/` partition (non-Axi owner = solo product)
- **Public surface**:
  - Production-like local proxy: local nginx → Vite preview; public project origin is `https://ielts.axiomaticworld.com` (root-domain compatibility remains during migration)
  - Browser API: `http://127.0.0.1:8000` (gateway-bff) and split services `127.0.0.1:8101-8108`
  - Realtime ASR: `http://127.0.0.1:5001` (Socket.IO)

## 2. Primary Users

| Persona | Goal | Surface |
|---|---|---|
| Self-studying learner | Acquire IELTS vocabulary through spaced repetition and practice modes | Web (`http://127.0.0.1:3020` dev, `:3002` preview), mobile (`apps/mobile`, Capacitor) |
| Listening / dictation learner | Train ear-to-text recognition and pronunciation | Web + mobile, exercises under `practice/` |
| Speaking learner | Practice pronunciation with AI scoring | Web + mobile, advanced path |
| Admin / operator | Operate vocabulary data, TTS assets, notes exports, user roles | Web admin route, TTS admin operator pages |
| Reviewer / Axi operator | Drive release, drill, and rollback rehearsals on remote host `119.29.182.134` | CLI / scripts under `scripts/` |

## 3. Functional Scope (in scope)

1. **Vocabulary book learning**: word books, chapters, word detail pages, favorites / known / confused-word marking.
2. **Practice loop**: `smart`, `listening`, `meaning`, `dictation`, `follow`, `radio`, `quickmemory`, `errors` modes.
3. **Spaced repetition + error review**: Ebbinghaus schedule, wrong-word book, follow-reading, listening, dictation, listening-to-meaning, all wired to learning stats, mode performance, and learner profile.
4. **AI assistant**: contextual Q&A, learning advice, wrong-word analysis, summary assistance, user-memory injection.
5. **Journal and summary**: learning journal, topic aggregation, daily summary, related export.
6. **Voice capability**: HTTP ASR API + realtime Socket.IO ASR split into an independent `speech_service.py` process.
7. **Admin and operations**: admin capability, TTS generation, startup scripts, production-like local proxy chain, submit-log archival.
8. **Static reference materials**: `reference-materials/raw/` holds non-code IELTS PDFs / audio; the directory is git-ignored.

## 4. Out of Scope / Non-Goals

- **Five-dimensional integrated mode and AI speaking scoring are independent paid / 2.0 tracks**; they do **not** accept Ebbinghaus / wrong-word book traffic in the basic flow.
- Not a multi-tenant SaaS: this is a single-owner product. There is no multi-tenant isolation, no external admin marketplace, and no public API monetization.
- The repo does **not** mirror `infra/axi-workspace-governance/` content, and does not act as a generic backend template.
- Live ASR / AI scoring in production is not in scope for the local dev runtime unless the operator has explicitly enabled cloud credentials.

## 5. Acceptance Criteria

| AC ID | Statement | Verifier |
|---|---|---|
| `PRD-AC-001` | All eight practice modes launch from the practice route and return to a stable home state on cancel. | `frontend/src/app/AppRoutes.practice.test.tsx` |
| `PRD-AC-002` | Listening-choice distractors never collapse to inflection-only forms (`-ing` / `-ed` / plural). | `CHANGELOG 1.2.6` regression coverage + listening-choice unit tests |
| `PRD-AC-003` | Ebbinghaus, wrong-word, follow, listening, dictation modes all write to learning stats, mode performance, and learner profile. | backend integration tests under `backend/tests/` |
| `PRD-AC-004` | Strict split runtime returns `503 strict-internal-contract` for cross-service shared reads that lack a projection. | `tests/test_admin_projection_bootstrap.py`, split-runtime smoke |
| `PRD-AC-005` | Frontend build, lint, and repo guards all pass for any release-bound commit. | `pnpm lint && pnpm build && pnpm --dir frontend verify:repo-guards` |
| `PRD-AC-006` | Production-like local proxy chain reaches `gateway-bff :8000` for `/api` and `asr-socketio :5001` for `/socket.io`. | `nginx.conf.example` + manual proxy walkthrough |
| `PRD-AC-007` | Feature-wish tickets created in production are closed in lockstep with the release that ships them. | release-closeout ticket linkage (see `CHANGELOG 1.2.6 Operations`) |

## 6. User Stories

- **US-LRN-1**: As a learner, I can start a `quickmemory` session, complete it, and see the wrong words appear in `errors` on the next visit.
- **US-LRN-2**: As a learner, I can take a `dictation` round with audio fallbacks when the canonical word audio is missing.
- **US-LRN-3**: As a learner, I can ask the AI assistant about a wrong word and get a contextual explanation grounded in the current word detail.
- **US-OPS-1**: As an operator, I can run `start-microservices.sh` to bring up the canonical split runtime and watch per-service readiness on `8101-8108`.
- **US-OPS-2**: As an operator, I can run `run-wave5-projection-cutover.py --verify-only` to confirm `admin/notes/ai` projections are healthy without rebooting any service.

## 7. Open Product Questions

- Whether the five-dimensional integrated mode ever becomes a free entry from `practice/` (currently frozen as 2.0 / paid).
- Whether `tts-admin` should be promoted out of the rollback-only operator surface (currently frozen; see `MILESTONE.md` Wave 6C).
- Whether daily summary export will move from Markdown to PDF as a first-class artifact (currently Markdown-only).

## 8. Change Control

- Material scope changes update this PRD and `CHANGELOG.md` in the same commit.
- Any new practice mode or AI feature requires a new `AC ID` and a regression test.
- The owner has final authority on promotion from `dev` to `main` and on remote release.

---

*This PRD is a living document. Preserve all manual sections after `<!-- MANUAL -->` markers; only auto-generated summaries above the marker may be refreshed.*
