# Cloud Microservices Deployment

Last updated: 2026-04-10

## Target

Deploy `ielts-vocab` to `119.29.182.134` as a single-server production baseline:

- nginx serves the Vite build from `/var/www/ielts-vocab`
- `/api/*` proxies to `gateway-bff` on `127.0.0.1:8000`
- `/socket.io/*` proxies to ASR Socket.IO on `127.0.0.1:5001`
- domain services run on `127.0.0.1:8101-8108`
- PostgreSQL stores service-owned and bootstrap shadow tables

## Required Files

- `/opt/ielts-vocab/current`: checked-out repository
- `/opt/ielts-vocab/venv`: Python virtual environment
- `/etc/ielts-vocab/backend.env`: shared app secrets and production flags
- `/etc/ielts-vocab/microservices.env`: service-specific PostgreSQL URLs
- `/var/www/ielts-vocab`: built frontend assets

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

## Verification

```bash
curl -fsS http://127.0.0.1:8000/ready
curl -fsS http://127.0.0.1:5001/ready
curl -fsS -H 'Host: axiomaticworld.com' http://127.0.0.1/api/books
```

After DNS points to `119.29.182.134`, issue TLS with certbot and verify `https://axiomaticworld.com/`, `/api/books`, login refresh, AI streaming, TTS media, and realtime speech.
