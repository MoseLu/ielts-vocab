# IELTS Vocabulary Handoff

- Project: `ielts-vocab`
- Path: `/Volumes/code/workspace/products/ielts-vocab`
- Owner: `AxiomaticWorld solo owner`
- Readiness: `verified`
- Purpose: Full-stack IELTS vocabulary learning product with web, mobile, shared client packages, gateway, split backend services, speech, and production operations.

## 90-Second Read Order

1. `AGENTS.md`
2. `README.md`
3. `INDEX.md`

## Entrypoints

- `frontend/src/app`: React web routes and application providers.
- `apps/mobile`: React Native mobile client.
- `apps/gateway-bff`: Canonical browser API ingress for the split runtime.
- `backend/app.py`: Compatibility monolith entrypoint retained for migration and rollback.
- `services`: Service-owned runtime entrypoints for identity, learning, catalog, AI, notes, TTS, ASR, and admin operations.
- `start-project.sh`: Production-style local startup with readiness checks.

## Commands

- Setup: `./scripts/setup-mac-runtime.sh && pnpm install`
- Start: `./start-project.sh`
- Health: `curl --fail http://127.0.0.1:8000/health`
- Verify: `pnpm --dir frontend verify:repo-guards`
- Smoke: `pnpm --dir frontend verify:repo-guards`

## Environment

- Runtimes: `Node.js`, `pnpm 9`, `Python`, `PostgreSQL`
- Services: `Redis`, `RabbitMQ`, `gateway-bff`, `split backend services`, `ASR Socket.IO`
- `POSTGRES_HOST`: required=yes, secret=no, source=backend/.env.microservices.local.example
- `REDIS_HOST`: required=yes, secret=no, source=backend/.env.microservices.local.example
- `RABBITMQ_HOST`: required=yes, secret=no, source=backend/.env.microservices.local.example
- `RABBITMQ_USER`: required=yes, secret=no, source=backend/.env.microservices.local.example
- `RABBITMQ_PASSWORD`: required=yes, secret=yes, source=local untracked environment file
- `WECHAT_MOBILE_APP_SECRET`: required=no, secret=yes, source=local untracked environment file
- `STAR_SERVICE_DATABASE_URL`: required=yes, secret=yes, source=local untracked environment file; names are documented in backend/.env.microservices.local.example

## Contracts

- Provides: `ielts-learning-app`, `upload-asr-api`, `realtime-asr-socket`, `tts-backend`
- Consumes: `ai-capability`, `minimax-tokenplan`, `ollama-local`
- Contract files: `AGENTS.md`, `packages/platform-sdk/platform_sdk/asr_runtime`, `backend/services/asr_service.py`, `services/asr-service/main.py`

## Current Work

- TODO: `backend/TODO.md`
- Milestone: `docs/project-audit-2026-03-31.md`
- Active: Keep the deployed split backend stable.
- Active: Complete final remote release, preflight, smoke, bounded storage drill, and closeout documentation.
- Known failure: Final remote release and bounded storage drill remain outstanding.
- Known failure: Visual regression coverage for frontend components is not yet established.

## Troubleshooting

- Symptom: Browser API or page startup fails locally.
  Diagnosis: Check the canonical chain at frontend preview :3002, gateway-bff :8000, split services :8101-8108, and ASR Socket.IO :5001.
  Resolution: Run ./start-project.sh and inspect its readiness output and runtime logs before falling back to compatibility mode.
- Symptom: Internal service requests fail only when a proxy is configured.
  Diagnosis: Ambient HTTP_PROXY or HTTPS_PROXY may be leaking into local service traffic.
  Resolution: Run the internal-client proxy regression tests and keep loopback service clients on the no-proxy path.

## Decisions And Freshness

- ADR: not recorded
- Changelog: `docs/state/CHANGELOG.md`
- Submit log: `docs/logs/submit`
- Last verified: `2026-08-23`
- Evidence: `Manifest v2 path-fix-up applied on 2026-08-23: PRD.md, TDD.md, root TODO.md, root MILESTONE.md do not exist on disk and were removed from readOrder / currentWork; backend/TODO.md and docs/project-audit-2026-03-31.md used as live anchors.`, `Full `pnpm --dir frontend verify:repo-guards` was not re-run this session; owner must re-run to confirm frontend verification still passes.`

> Generated from `docs/project-docs.manifest.json`; edit the manifest, then regenerate this file.
