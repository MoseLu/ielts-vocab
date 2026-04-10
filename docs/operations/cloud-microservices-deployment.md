# Cloud Microservices Deployment

Last updated: 2026-04-10

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
- `/etc/ielts-vocab/microservices.env`: service-specific PostgreSQL URLs
- `/var/www/ielts-vocab`: active frontend assets served by nginx

## Bootstrap

```bash
cd /opt/ielts-vocab/current
bash scripts/cloud-deploy/install-cloud-runtime.sh
bash scripts/cloud-deploy/provision-postgres.sh /etc/ielts-vocab/microservices.env
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

The install script now prepares `/opt/ielts-vocab/releases` and bootstraps `/opt/ielts-vocab/repository` from the existing checkout when needed.

## Data Migration

Run from the repository root after copying `backend/database.sqlite` from the final local snapshot:

```bash
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --plan --env-file /etc/ielts-vocab/microservices.env
/opt/ielts-vocab/venv/bin/python scripts/migrate-sqlite-to-microservice-postgres.py --scope bootstrap --replace --env-file /etc/ielts-vocab/microservices.env
```

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
3. Runs `preflight-check.sh <git-ref>` on the server to verify sudo, env files, nginx, systemd, and git access.
4. Runs `deploy-release.sh <git-ref>` on the server.
5. The server fetches the target commit from `/opt/ielts-vocab/repository`.
6. A new immutable release directory is created under `/opt/ielts-vocab/releases`.
7. PostgreSQL backup runs before traffic switches.
8. `current` is pointed to the new release, frontend assets are copied, and all services restart.
9. `smoke-check.sh` verifies internal readiness plus nginx proxy routing.
10. If restart or smoke verification fails, `rollback-release.sh` switches back to the previous release.

## Manual Deploy and Rollback

Manual production deploy:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/deploy-release.sh main
```

Manual preflight:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/preflight-check.sh main
```

Manual smoke check:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/smoke-check.sh
```

Manual rollback:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/rollback-release.sh /opt/ielts-vocab/releases/<timestamp>-<sha>
```

## Verification

The release smoke script checks:

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
