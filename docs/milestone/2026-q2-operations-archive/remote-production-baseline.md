# Remote Production Baseline

Last updated: 2026-04-22 22:55:00 +08:00

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
- `redis`
- `rabbitmq-server`

## Runtime routing

- nginx serves frontend assets from `/var/www/ielts-vocab/current`
- `https://axiomaticworld.com/` -> nginx `:80` -> active release `dist` symlink
- `https://axiomaticworld.com/api/*` -> nginx -> `gateway-bff` on `127.0.0.1:8000`
- `https://axiomaticworld.com/socket.io/*` -> nginx -> ASR Socket.IO on `127.0.0.1:5001`
- Active readiness ports:
  - `gateway-bff`: `8000`
  - services: `8101-8108`
  - `asr-socketio`: `5001`

## Env-file locations

- Shared production secrets: `/etc/ielts-vocab/backend.env`
- Service PostgreSQL URLs, split-service ports, and Wave 5 Redis/RabbitMQ settings: `/etc/ielts-vocab/microservices.env`
- Release root: `/opt/ielts-vocab/current`
- Deploy state records: `/opt/ielts-vocab/deploy-state/last-good-release`
- Git fetch root for deploys: `/opt/ielts-vocab/repository`

## GitHub access baseline

- `/root/.ssh/config` maps `github.com` to `ssh.github.com:443`, so remote git traffic does not depend on port `22`
- `/root/.ssh/ielts-vocab-github` is the remote GitHub SSH key used for deploy fetches and direct repository pulls
- Global git rewrite now maps `https://github.com/*`, `http://github.com/*`, and `git://github.com/*` to `git@github.com:*`, so ad-hoc `git clone https://github.com/...` commands still use SSH on the wire
- Deploy-critical GitHub paths are git over SSH `443`, `raw.githubusercontent.com`, source archives through `codeload.github.com`, and release assets through `release-assets.githubusercontent.com`
- `https://github.com` HTML reachability is useful for operator browsing, but it is not required for the current CI/CD deploy chain or for direct remote `git clone` / `git fetch` flows

Remote GitHub baseline commands:

```bash
sudo bash /opt/ielts-vocab/current/scripts/cloud-deploy/configure-github-access.sh --repo /opt/ielts-vocab/repository
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/validate-github-access.sh --repo /opt/ielts-vocab/repository
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/validate-github-access.sh --repo /opt/ielts-vocab/repository --critical-only
```

Status snapshot on `2026-04-11`: `119.29.182.134` now reaches GitHub SSH on `ssh.github.com:443`, public repository refs, `raw.githubusercontent.com`, source archives, and release assets directly from the remote host. The HTML `https://github.com` entrypoint may still be less stable than the git/download endpoints, but that does not block the current deploy contract or direct remote repository pulls.

## Broker runtime baseline

- `redis` runs locally on `127.0.0.1:6379`
- `rabbitmq-server` runs locally on `127.0.0.1:5672`
- `/etc/ielts-vocab/microservices.env` must carry `REDIS_HOST`, `REDIS_PORT`, `REDIS_KEY_PREFIX`, per-service Redis DB assignments, `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`, and `RABBITMQ_DOMAIN_EXCHANGE`
- Optional speaking calibration overrides for `ai-execution-service` also belong in `/etc/ielts-vocab/microservices.env`; use `SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON=[[95,9.0],[89,8.5],[83,8.0],[76,7.5],[69,7.0],[62,6.5],[55,6.0],[48,5.5],[41,5.0],[34,4.5],[27,4.0],[20,3.5],[13,3.0],[6,2.5],[1,2.0],[0,0.0]]` when calibration needs to diverge from the built-in default table
- `scripts/cloud-deploy/preflight-check.sh` now validates that optional speaking calibration JSON before deploy; unset keeps defaults, invalid configured JSON blocks the rollout early
- `scripts/cloud-deploy/preflight-check.sh` now fails fast if the broker env keys or broker systemd units are missing
- `scripts/cloud-deploy/smoke-check.sh` now runs `scripts/cloud-deploy/validate-broker-runtime.sh` before the HTTP readiness probes

Remote broker provisioning and validation commands:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/provision-broker-runtime.sh /etc/ielts-vocab/microservices.env
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/validate-broker-runtime.sh
```

Status snapshot on `2026-04-11`: the broker baseline was provisioned successfully on `119.29.182.134`, and both the updated `preflight-check.sh` and `smoke-check.sh` passed with broker validation enabled.

The deployed release path on `119.29.182.134` now uses the worker-aware [run-service.sh](../../scripts/cloud-deploy/run-service.sh) contract for both browser-path services and workers. Deploy/rollback restarts the single-instance `ielts-service@...` set in place and then stops any leftover `ielts-http-slot@...` units from older blue/green releases.

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

The production release path now also runs `/opt/ielts-vocab/current/scripts/run-service-schema-migrations.py` before the `current` symlink switches, so split-service schema repairs ship with the same immutable release that restarts the services.

Wave 4 remote storage drill command:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RECORD_PATH=/var/log/ielts-vocab/wave4/storage-drill-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_NOTES_EXPORT_REPAIR=true DRILL_NOTES_USER_ID=1 DRILL_NOTES_START_DATE=2026-03-30 DRILL_NOTES_END_DATE=2026-03-30 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_WORD_AUDIO_REPAIR=true DRILL_WORD_AUDIO_BOOK_ID=ielts_reading_premium DRILL_WORD_AUDIO_LIMIT=200 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
```

Wave 4 service-scoped shared SQLite override command:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service asr-service
sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
```

Wave 4 rollback rehearsal command:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_RECORD_PATH=/var/log/ielts-vocab/wave4/rollback-rehearsal-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
```

Wave 4 record generation command:

```bash
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/<captured-log>.log --host 119.29.182.134
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/shared-sqlite-override-<timestamp>.log --host 119.29.182.134 --command "sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-<timestamp>.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service"
```

## Mandatory smoke checks

Every remote rollout must keep these checks green:

- broker env plus Redis/RabbitMQ connectivity through `validate-broker-runtime.sh`
- `gateway-bff` and HTTP service `/ready` checks on `127.0.0.1:8000` and `127.0.0.1:8101-8108`
- `http://127.0.0.1:5001/ready`
- `http://127.0.0.1/` with `Host: axiomaticworld.com`
- `http://127.0.0.1/api/books` with `Host: axiomaticworld.com`
- `smoke-check.sh` defaults to the single-instance ports above; temporary `SMOKE_HTTP_SLOT=<slot>` overrides remain only for cleanup or historical troubleshooting.

## External smoke flow

After internal smoke passes, the deployed domain must still verify:

- `https://axiomaticworld.com/`
- `https://axiomaticworld.com/api/books`
- login refresh flow
- `GET /api/ai/quick-memory/review-queue?limit=0&within_days=1&offset=0&scope=due`
- AI streaming through `gateway-bff`
- TTS media fetch through signed URLs
- realtime speech connection on `/socket.io`
