# Local PostgreSQL for Microservices

Last updated: 2026-04-10

## Purpose

Use the local PostgreSQL server as the next database step for the split microservices.

The current local baseline uses a project-owned PostgreSQL cluster on `127.0.0.1:55432` so the migration does not depend on the system `5432` instance credentials.

The repository now supports service-specific database URLs keyed by `CURRENT_SERVICE_NAME`, for example:

- `IDENTITY_SERVICE_DATABASE_URL`
- `LEARNING_CORE_SERVICE_DATABASE_URL`
- `CATALOG_CONTENT_SERVICE_DATABASE_URL`
- `AI_EXECUTION_SERVICE_DATABASE_URL`
- `NOTES_SERVICE_DATABASE_URL`
- `TTS_MEDIA_SERVICE_DATABASE_URL`
- `ASR_SERVICE_DATABASE_URL`
- `ADMIN_OPS_SERVICE_DATABASE_URL`

## What Changed

- `backend/config.py` now resolves database config in this order:
  1. `<SERVICE_PREFIX>_SQLALCHEMY_DATABASE_URI`
  2. `<SERVICE_PREFIX>_DATABASE_URL`
  3. `<SERVICE_PREFIX>_POSTGRES_*`
  4. generic `SQLALCHEMY_DATABASE_URI`
  5. generic `DATABASE_URL`
  6. generic `POSTGRES_*`
  7. SQLite fallback
- Split service entrypoints now set `CURRENT_SERVICE_NAME` before loading the shared backend config.
- Split service entrypoints now load `backend/.env` and `backend/.env.microservices.local` automatically before importing shared Flask runtimes.
- `backend/requirements.txt` now includes `psycopg2-binary` for SQLAlchemy PostgreSQL access.
- `start-microservices.ps1` now starts the full backend microservice chain against the project-owned PostgreSQL cluster.

## Provisioning Script

Run this from the repo root after you know the local PostgreSQL admin password:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\init-local-postgres-microservices.ps1 `
  -AdminUser postgres `
  -AdminPassword '<your-local-postgres-password>'
```

The script will:

- create one role per microservice
- create one database per microservice
- write `backend/.env.microservices.local`

For the current repository, the script has already been run against the project-owned cluster on `55432`.

## Local Loading Pattern

Keep `backend/.env` as the shared application secret/config source.

Load `backend/.env.microservices.local` after it when starting the split services so the service-specific database URLs win over the default SQLite fallback.

If you do not want generated credentials yet, copy [backend/.env.microservices.local.example](/F:/enterprise-workspace/projects/ielts-vocab/backend/.env.microservices.local.example) into a local untracked env file and fill the passwords yourself.

## One-Command Backend Startup

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-microservices.ps1
```

This will:

- ensure the project-owned PostgreSQL cluster on `55432` is running
- stop old listeners on the split-service ports
- start `gateway-bff`
- start all HTTP microservices
- start the ASR Socket.IO process on `5001`
- wait for `/ready` or `/health` checks before returning

For a controlled Wave 4 repair or rollback drill that must temporarily allow one guarded split service to reuse the shared SQLite fallback, use the service-scoped startup flag instead of the global env override:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-microservices.ps1 -AllowSharedSplitServiceSqliteServices notes-service
```

`start-project.ps1` forwards the same flag to the split runtime path:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-project.ps1 -AllowSharedSplitServiceSqliteServices notes-service
```

## Schema Bootstrap And Data Migration

The repository now includes [migrate-sqlite-to-microservice-postgres.py](/F:/enterprise-workspace/projects/ielts-vocab/scripts/migrate-sqlite-to-microservice-postgres.py).

Use it to inspect the per-service table plan:

```powershell
python .\scripts\migrate-sqlite-to-microservice-postgres.py --plan
```

Use it to create the selected service schema without copying rows:

```powershell
python .\scripts\migrate-sqlite-to-microservice-postgres.py --bootstrap-only
```

Use it to replace the selected PostgreSQL tables with the current `backend/database.sqlite` contents:

```powershell
python .\scripts\migrate-sqlite-to-microservice-postgres.py --replace
```

Useful flags:

- `--service identity-service` to migrate a single service
- `--scope owned` to copy only authoritative tables instead of the larger bootstrap set with transitional shadow tables
- `--env-file backend/.env.microservices.local` to point at a different local credential file
