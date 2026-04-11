# Cloud Microservices Deployment

Last updated: 2026-04-11 15:39:26 +08:00

## Target

Deploy `ielts-vocab` to `119.29.182.134` as a single-server production baseline:

- nginx serves the Vite build from `/var/www/ielts-vocab`
- `/api/*` proxies to `gateway-bff` on `127.0.0.1:8000`
- `/socket.io/*` proxies to ASR Socket.IO on `127.0.0.1:5001`
- domain services run on `127.0.0.1:8101-8108`
- PostgreSQL stores service-owned and bootstrap shadow tables
- GitHub Actions deploys `main` by SSHing into the server and running a release-based rollout

## Runtime Layout

- `/opt/ielts-vocab/current`: current active release symlink
- `/opt/ielts-vocab/releases/<timestamp>-<sha>`: immutable release directories
- `/opt/ielts-vocab/repository`: persistent git checkout used for `git fetch origin`
- `/opt/ielts-vocab/venv`: shared Python virtual environment
- `/etc/ielts-vocab/backend.env`: shared app secrets and production flags
- `/etc/ielts-vocab/microservices.env`: service-specific PostgreSQL URLs plus Redis/RabbitMQ runtime settings
- `/var/www/ielts-vocab`: active frontend assets served by nginx

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

## Broker Runtime

Remote Wave 5 broker rollout now has a dedicated provisioning and validation path:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/provision-broker-runtime.sh /etc/ielts-vocab/microservices.env
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/validate-broker-runtime.sh
```

The validation wrapper checks `systemctl is-active --quiet redis`, `systemctl is-active --quiet rabbitmq-server`, and then runs [validate_wave5_broker_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/validate_wave5_broker_runtime.py) against `/etc/ielts-vocab/microservices.env`.

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
systemctl enable --now ielts-service@gateway-bff
systemctl enable --now ielts-service@identity-service
systemctl enable --now ielts-service@learning-core-service
systemctl enable --now ielts-service@catalog-content-service
systemctl enable --now ielts-service@ai-execution-service
systemctl enable --now ielts-service@tts-media-service
systemctl enable --now ielts-service@asr-service
systemctl enable --now ielts-service@notes-service
systemctl enable --now ielts-service@admin-ops-service
systemctl enable --now ielts-service@asr-socketio
```

Wave 5 worker units are now part of the release restart path when the target release contains worker-aware [run-service.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/run-service.sh) entries. [release-common.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/release-common.sh) enables those worker instances automatically for worker-aware releases and disables them again when rolling back to an older release that does not support them. [smoke-check.sh](/F:/enterprise-workspace/projects/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) also verifies worker unit health in that case.

## GitHub Actions Production Deploy

Workflow file: [deploy-production.yml](/F:/enterprise-workspace/projects/ielts-vocab/.github/workflows/deploy-production.yml)

Required GitHub `production` environment secrets:

- `PROD_SSH_HOST`: production host, currently `119.29.182.134`
- `PROD_SSH_USER`: SSH user for deploys
- `PROD_SSH_PRIVATE_KEY`: private key that can SSH into the production host

Recommended GitHub `production` environment variables:

- `PROD_APP_HOME`: defaults to `/opt/ielts-vocab`
- `PROD_SMOKE_HOST`: defaults to `axiomaticworld.com`

Recommended GitHub branch rules:

- `dev`: required CI checks before merge
- `main`: required CI checks plus GitHub Environment approval before deploy

The production workflow does this on each `main` release:

1. Checks out the target ref from GitHub.
2. Uploads the latest deploy scripts to a temporary directory on the server.
3. Runs `preflight-check.sh <git-ref>` on the server to verify sudo, env files, broker baseline, nginx, systemd, and git access.
4. Runs `deploy-release.sh <git-ref>` on the server.
5. The server fetches the target commit from `/opt/ielts-vocab/repository`.
6. A new immutable release directory is created under `/opt/ielts-vocab/releases`.
7. PostgreSQL backup runs before traffic switches.
8. The release runs `scripts/run-service-schema-migrations.py` against the split-service databases before `current` changes.
9. `current` is pointed to the new release, frontend assets are copied, and all services restart.
10. `smoke-check.sh` validates broker runtime first, then verifies internal readiness plus nginx proxy routing.
11. If restart or smoke verification fails, `rollback-release.sh` switches back to the previous release.

## Manual Deploy and Rollback

Manual production deploy:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/deploy-release.sh main
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

Manual rollback:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/rollback-release.sh /opt/ielts-vocab/releases/<timestamp>-<sha>
```

## Verification

The release smoke script checks:

- broker env plus Redis/RabbitMQ connectivity through `validate-broker-runtime.sh`
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

After DNS points to `119.29.182.134`, verify `https://axiomaticworld.com/`, `/api/books`, login refresh, AI streaming, TTS media, and realtime speech.
