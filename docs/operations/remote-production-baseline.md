# Remote Production Baseline

Last updated: 2026-04-10

## Scope

This document freezes the current remote production baseline on `119.29.182.134` so each remaining microservice migration step can be validated against one stable target before rollout.

## Active systemd units

- `ielts-service@gateway-bff`
- `ielts-service@identity-service`
- `ielts-service@learning-core-service`
- `ielts-service@catalog-content-service`
- `ielts-service@ai-execution-service`
- `ielts-service@tts-media-service`
- `ielts-service@asr-service`
- `ielts-service@notes-service`
- `ielts-service@admin-ops-service`
- `ielts-service@asr-socketio`

## Runtime routing

- nginx serves frontend assets from `/var/www/ielts-vocab`
- `https://axiomaticworld.com/` -> nginx `:80` -> static frontend
- `https://axiomaticworld.com/api/*` -> nginx -> `gateway-bff` on `127.0.0.1:8000`
- `https://axiomaticworld.com/socket.io/*` -> nginx -> ASR Socket.IO on `127.0.0.1:5001`
- Internal service readiness ports:
  - `gateway-bff`: `8000`
  - `identity-service`: `8101`
  - `learning-core-service`: `8102`
  - `catalog-content-service`: `8103`
  - `ai-execution-service`: `8104`
  - `tts-media-service`: `8105`
  - `asr-service`: `8106`
  - `notes-service`: `8107`
  - `admin-ops-service`: `8108`
  - `asr-socketio`: `5001`

## Env-file locations

- Shared production secrets: `/etc/ielts-vocab/backend.env`
- Service PostgreSQL URLs and split-service ports: `/etc/ielts-vocab/microservices.env`
- Release root: `/opt/ielts-vocab/current`
- Git fetch root for deploys: `/opt/ielts-vocab/repository`

## PostgreSQL backup path

- Deploy-time and cron backups write under `/var/backups/ielts-vocab/postgres`
- The deploy path calls `scripts/cloud-deploy/backup-postgres.sh`
- The daily cron job is `/etc/cron.d/ielts-vocab-postgres-backup`

## Migration baseline commands

Use these commands from `/opt/ielts-vocab/current` before any Wave 3 schema cutover:

```bash
/opt/ielts-vocab/venv/bin/python scripts/describe-service-migration-plan.py --json
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --bootstrap-only --scope owned --env-file /etc/ielts-vocab/microservices.env
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --scope bootstrap --replace --env-file /etc/ielts-vocab/microservices.env
/opt/ielts-vocab/venv/bin/python scripts/validate_microservice_storage_parity.py --scope owned --env-file /etc/ielts-vocab/microservices.env
```

## Mandatory smoke checks

Every remote rollout must keep these checks green:

- `http://127.0.0.1:8000/ready`
- `http://127.0.0.1:8101/ready`
- `http://127.0.0.1:8102/ready`
- `http://127.0.0.1:8103/ready`
- `http://127.0.0.1:8104/ready`
- `http://127.0.0.1:8105/ready`
- `http://127.0.0.1:8106/ready`
- `http://127.0.0.1:8107/ready`
- `http://127.0.0.1:8108/ready`
- `http://127.0.0.1:5001/ready`
- `http://127.0.0.1/` with `Host: axiomaticworld.com`
- `http://127.0.0.1/api/books` with `Host: axiomaticworld.com`

## External smoke flow

After internal smoke passes, the deployed domain must still verify:

- `https://axiomaticworld.com/`
- `https://axiomaticworld.com/api/books`
- login refresh flow
- AI streaming through `gateway-bff`
- TTS media fetch through signed URLs
- realtime speech connection on `/socket.io`
