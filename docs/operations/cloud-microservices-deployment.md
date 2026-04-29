# Cloud Microservices Deployment

Last updated: 2026-04-22 22:55:00 +08:00

## Target

Deploy `ielts-vocab` to `119.29.182.134` as a single-server production baseline:

- nginx serves the Vite build through `/var/www/ielts-vocab/current`
- `/api/*` proxies to `gateway-bff` on `127.0.0.1:8000`
- `/socket.io/*` proxies to ASR Socket.IO on `127.0.0.1:5001`
- domain HTTP services run as single-instance `ielts-service@...` units on `8000` and `8101-8108`
- PostgreSQL stores service-owned and bootstrap shadow tables
- GitHub Actions deploys `main` by SSHing into the server and running a release-based rollout
- GitHub Actions now builds a release artifact off-host with the production frontend asset base, uploads it by SSH, and the server activates that artifact without rebuilding the frontend

## Runtime Layout

- `/opt/ielts-vocab/current`: current active release symlink
- `/opt/ielts-vocab/deploy-state`: last-good rollback records
- `/opt/ielts-vocab/releases/<timestamp>-<sha>`: immutable release directories
- `/opt/ielts-vocab/repository`: persistent git checkout used for `git fetch origin`
- `/opt/ielts-vocab/venv`: shared Python virtual environment
- `/etc/ielts-vocab/backend.env`: shared app secrets and production flags
- `/etc/ielts-vocab/microservices.env`: service-specific PostgreSQL URLs plus Redis/RabbitMQ runtime settings
- `/var/www/ielts-vocab/current`: symlink to the active release `dist`

## Bootstrap

```bash
cd /opt/ielts-vocab/current
bash scripts/cloud-deploy/install-cloud-runtime.sh
bash scripts/cloud-deploy/provision-postgres.sh /etc/ielts-vocab/microservices.env
bash scripts/cloud-deploy/provision-broker-runtime.sh /etc/ielts-vocab/microservices.env
```

Copy production secret values into `/etc/ielts-vocab/backend.env`. It must include `SECRET_KEY`, `JWT_SECRET_KEY`, AI/TTS/ASR provider keys, OSS config, and:

```bash
COOKIE_SECURE=true
CORS_ORIGINS=https://axiomaticworld.com,https://www.axiomaticworld.com
TRUST_PROXY_HEADERS=true
PROXY_FIX_X_FOR=1
PROXY_FIX_X_PROTO=1
MICROSERVICES_ENV_FILE=/etc/ielts-vocab/microservices.env
```

The install script now prepares `/opt/ielts-vocab/releases`, bootstraps `/opt/ielts-vocab/repository` from the existing checkout when needed, installs `redis` plus `rabbitmq-server`, and auto-runs `provision-broker-runtime.sh` when `/etc/ielts-vocab/microservices.env` already exists.

`provision-postgres.sh` now seeds the remote broker baseline into `/etc/ielts-vocab/microservices.env`, including:

- `REDIS_HOST=127.0.0.1`
- `REDIS_PORT=6379`
- `REDIS_KEY_PREFIX=ielts-vocab`
- `GATEWAY_BFF_REDIS_DB=0` through `ADMIN_OPS_SERVICE_REDIS_DB=8`
- `RABBITMQ_HOST=127.0.0.1`
- `RABBITMQ_PORT=5672`
- `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`, and `RABBITMQ_DOMAIN_EXCHANGE`

Optional `ai-execution-service` speaking calibration can also live in `/etc/ielts-vocab/microservices.env`:

```bash
SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON=[[95,9.0],[89,8.5],[83,8.0],[76,7.5],[69,7.0],[62,6.5],[55,6.0],[48,5.5],[41,5.0],[34,4.5],[27,4.0],[20,3.5],[13,3.0],[6,2.5],[1,2.0],[0,0.0]]
```

The value is a JSON array of `[minScore, band]` pairs used by `ai-execution-service` to map model raw scores (`0-100`) into IELTS half-band scores. Invalid JSON or invalid rows now fall back to the built-in default table, and overall band rounding uses a half-up rule, so `7.25` becomes `7.5`.

## Broker Runtime

Remote Wave 5 broker rollout now has a dedicated provisioning and validation path:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/provision-broker-runtime.sh /etc/ielts-vocab/microservices.env
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/validate-broker-runtime.sh
```

The validation wrapper checks `systemctl is-active --quiet redis`, `systemctl is-active --quiet rabbitmq-server`, and then runs [validate_wave5_broker_runtime.py](../../scripts/validate_wave5_broker_runtime.py) against `/etc/ielts-vocab/microservices.env`.

`preflight-check.sh` now also runs [validate_speaking_band_thresholds.py](../../scripts/validate_speaking_band_thresholds.py) against the same env file. If `SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON` is unset, preflight keeps the built-in defaults; if it is set but the JSON shape is invalid, preflight fails before the release starts.

The first real remote rollout was executed on `2026-04-11` against `119.29.182.134`: broker env keys were added to `/etc/ielts-vocab/microservices.env`, `redis` plus `rabbitmq-server` were installed and enabled, and `validate-broker-runtime.sh`, `preflight-check.sh`, and `smoke-check.sh` all passed.

## Data Migration

Run from the repository root after copying `backend/database.sqlite` from the final local snapshot:

```bash
/opt/ielts-vocab/venv/bin/python scripts/describe-service-migration-plan.py --json
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --bootstrap-only --scope owned --env-file /etc/ielts-vocab/microservices.env
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --plan --env-file /etc/ielts-vocab/microservices.env
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --scope bootstrap --replace --env-file /etc/ielts-vocab/microservices.env
/opt/ielts-vocab/venv/bin/python scripts/validate_microservice_storage_parity.py --scope owned --env-file /etc/ielts-vocab/microservices.env
```

The current write-owning migration baseline covers:

- `identity-service`
- `learning-core-service`
- `catalog-content-service`
- `notes-service`
- `ai-execution-service`

`describe-service-migration-plan.py` prints the canonical `baseline_revision`, `version_table`, and owned-table list for each service so rollout and rollback can reference the same baseline metadata.

## Service Control

```bash
systemctl list-units 'ielts-service@*'
systemctl enable --now ielts-service@asr-socketio
```

The HTTP browser path now uses the same `ielts-service@...` unit family as the workers. `deploy-release.sh` switches `/opt/ielts-vocab/current`, reloads nginx to `127.0.0.1:8000`, restarts the single running service set, and then stops any leftover `ielts-http-slot@...` units from older blue/green releases.

To keep the `2C4G` production host responsive during deploys, release dependency install/build now runs inside a constrained `systemd-run` scope. The default guardrail is:

- `CPUQuota=50%`
- `MemoryHigh=1280M`
- `MemoryMax=1536M`
- `Nice=15`
- `NODE_OPTIONS=--max-old-space-size=512`

Those defaults can be overridden with `DEPLOY_BUILD_*` env vars if the host profile changes, but the normal release path should no longer let `pnpm install/build` starve `sshd`, `nginx`, or the already-running app processes.

Production also now includes a watchdog timer:

```bash
systemctl status ielts-health-watchdog.timer
systemctl status ielts-health-watchdog.service
```

The timer runs once per minute, skips while `deploy-release.sh` is active, and restarts `nginx` plus the single-instance `ielts-service@...` units after three consecutive local health-check failures.

## GitHub Actions Production Deploy

Workflow file: [deploy-production.yml](../../.github/workflows/deploy-production.yml)

Required GitHub `production` environment secrets:

- `PROD_SSH_HOST`: production host, currently `119.29.182.134`
- `PROD_SSH_USER`: SSH user for deploys
- `PROD_SSH_PRIVATE_KEY`: private key that can SSH into the production host

Recommended GitHub `production` environment variables:

- `PROD_APP_HOME`: defaults to `/opt/ielts-vocab`
- `PROD_SMOKE_HOST`: defaults to `axiomaticworld.com`
- `FRONTEND_ASSET_OSS_ENABLED`, `FRONTEND_ASSET_OSS_PUBLIC_BASE_URL`, and `FRONTEND_ASSET_OSS_PREFIX`: must match `/etc/ielts-vocab/microservices.env` when OSS frontend asset delivery is enabled

Recommended GitHub branch rules:

- `dev`: required CI checks before merge
- `main`: required CI checks plus GitHub Environment approval before deploy

The production workflow does this on each `main` release:

1. Checks out the target ref from GitHub.
2. Builds a release artifact with `scripts/cloud-deploy/build-release-artifact.sh`, including a prebuilt `dist/` and the frontend OSS asset-base marker. The artifact omits `frontend/` source because the production server does not rebuild frontend assets on the artifact path.
3. Uploads the artifact plus the latest deploy scripts to a temporary directory on the server.
4. Runs `preflight-check.sh <git-ref>` on the server to verify sudo, env files, broker baseline, nginx, systemd, and git access.
5. Runs `deploy-release-artifact.sh <artifact-path> <commit-sha>` on the server.
6. The server extracts the artifact into a new immutable release directory under `/opt/ielts-vocab/releases`.
7. PostgreSQL backup runs before the service restart.
8. The release runs `scripts/run-service-schema-migrations.py` against the split-service databases before `current` switches.
9. If frontend OSS delivery is enabled, the server verifies the artifact asset base matches production env and uploads the prebuilt `dist` assets to OSS before switching.
10. `/opt/ielts-vocab/current` and `/var/www/ielts-vocab/current` switch to the new immutable release.
11. nginx is reloaded to keep `/api/*` on `127.0.0.1:8000`, then `ielts-service@...` units restart in place.
12. The deploy smoke checks the restarted single-instance services, verifies `ielts-health-watchdog.timer`, and stops any leftover `ielts-http-slot@...` units from older releases.
13. If post-switch verification fails, deploy points `current` back to the previous release and restarts the single-instance services.

This removes the slowest production-host steps from the steady-state release path: the server no longer runs `pnpm install` or `pnpm build` during normal deploys.

## Manual Deploy and Rollback

Manual production deploy:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/deploy-release.sh main
```

Preferred artifact deploy:

```bash
bash scripts/cloud-deploy/build-release-artifact.sh HEAD /tmp/ielts-vocab-release.tgz
scp /tmp/ielts-vocab-release.tgz <host>:/tmp/ielts-vocab-release.tgz
ssh <host> "sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/deploy-release-artifact.sh /tmp/ielts-vocab-release.tgz <commit-sha>"
```

Manual service-schema migration run:

```bash
sudo APP_HOME=/opt/ielts-vocab /opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/run-service-schema-migrations.py --env-file /etc/ielts-vocab/microservices.env
```

Manual preflight:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/preflight-check.sh main
```

Manual smoke check:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/smoke-check.sh
```

Manual broker validation:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/validate-broker-runtime.sh
```

Wave 4 remote storage drill:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
```

Optional drill flags:

```bash
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_REPAIR=true bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_NOTES_EXPORT_REPAIR=true DRILL_NOTES_USER_ID=1 DRILL_NOTES_START_DATE=2026-03-30 DRILL_NOTES_END_DATE=2026-03-30 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_WORD_AUDIO_REPAIR=true DRILL_WORD_AUDIO_BOOK_ID=ielts_reading_premium DRILL_WORD_AUDIO_LIMIT=200 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_ROLLBACK_TARGET=/opt/ielts-vocab/releases/<timestamp>-<sha> bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RECORD_PATH=/var/log/ielts-vocab/wave4/storage-drill-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
```

Remote service-scoped shared SQLite override restart:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service asr-service
sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
```

Wave 4 rollback rehearsal:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_EXECUTE=true bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_RECORD_PATH=/var/log/ielts-vocab/wave4/rollback-rehearsal-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
```

Turn a captured Wave 4 raw log into a markdown record with:

```bash
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/<captured-log>.log --host 119.29.182.134
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/shared-sqlite-override-<timestamp>.log --host 119.29.182.134 --command "sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-<timestamp>.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service"
```

Post-deploy closeout now has a dedicated wrapper:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/release-closeout.sh
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com CLOSEOUT_SOURCE_SQLITE=/opt/ielts-vocab/source/production-repair-20260410.sqlite bash /opt/ielts-vocab/current/scripts/cloud-deploy/release-closeout.sh
```

That wrapper runs post-switch smoke, bounded storage drill, and `run-wave5-projection-cutover.py --runtime split --verify-only`, then stores raw logs under `/var/log/ielts-vocab/release-closeout/<timestamp>/`. The projection verify step now reads the split service databases directly from the sourced `ADMIN_OPS/NOTES/AI_EXECUTION_SERVICE_DATABASE_URL` or `*_SQLITE_DB_PATH` envs, and compares each projection against the service-local shadow source tables that the bootstrap flow actually uses, instead of booting the monolith against `backend/database.sqlite`. The bounded storage drill now resolves its SQLite snapshot from `CLOSEOUT_SOURCE_SQLITE` / `DRILL_SOURCE_SQLITE`, then `SOURCE_SQLITE_PATH` / `SQLITE_DB_PATH`, then `backend/database.sqlite`, then the newest `APP_HOME/source/*.sqlite`. Routine release closeout defaults `CLOSEOUT_RUN_STORAGE_PARITY=false`, so artifact/reference checks remain in the closeout pack without hard-failing on an archival SQLite snapshot after live PostgreSQL writes continue; set `CLOSEOUT_RUN_STORAGE_PARITY=true` only when you also have a fresh canonical SQLite snapshot.

Manual rollback:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/rollback-release.sh /opt/ielts-vocab/releases/<timestamp>-<sha>
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/rollback-release.sh --last-good
```

## Verification

The release smoke script checks:

- broker env plus Redis/RabbitMQ connectivity through `validate-broker-runtime.sh`
- `gateway-bff` and each HTTP service `/ready` on `127.0.0.1:8000` and `127.0.0.1:8101-8108`
- AI dependency probe on `/internal/ops/ai-dependencies`, including the quick-memory review-queue chain
- `http://127.0.0.1:5001/ready`
- `http://127.0.0.1/` with `Host: axiomaticworld.com`
- `http://127.0.0.1/api/books` with `Host: axiomaticworld.com`
- `ielts-health-watchdog.timer` is active after the release switch

After DNS points to `119.29.182.134`, verify `https://axiomaticworld.com/`, `/api/books`, login refresh, `GET /api/ai/quick-memory/review-queue?limit=0&within_days=1&offset=0&scope=due`, AI streaming, TTS media, and realtime speech.
