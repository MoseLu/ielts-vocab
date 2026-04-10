# Wave 4 Storage Parity Runbook

Last updated: 2026-04-10

## Purpose

Wave 4 starts by closing the last unsafe shared-storage path:

- write-owning split services must not silently fall back to `backend/database.sqlite`
- SQLite-to-service-database parity must be measurable before the fallback is considered retired

This runbook is the gate for that transition.

## Runtime Guard

`backend/config.py` now rejects the shared SQLite fallback for write-owning split services:

- `identity-service`
- `learning-core-service`
- `catalog-content-service`
- `ai-execution-service`
- `notes-service`

Allowed targets:

- service-owned PostgreSQL via `*_DATABASE_URL` or `*_POSTGRES_*`
- explicit service-local SQLite paths such as a temp test database

Blocked target:

- implicit shared fallback `backend/database.sqlite`

Break-glass override:

```bash
ALLOW_SHARED_SPLIT_SERVICE_SQLITE=true
```

Use the override only for a controlled rollback or repair drill. Do not leave it enabled in normal split-service startup.

## Parity Validation

Run from the repository root after the latest SQLite snapshot and after the target service databases are refreshed:

```bash
python .\scripts\validate_microservice_storage_parity.py --scope owned
```

Useful variants:

```bash
python .\scripts\validate_microservice_storage_parity.py --service identity-service --service learning-core-service
python .\scripts\validate_microservice_storage_parity.py --scope bootstrap
python .\scripts\validate_microservice_storage_parity.py --env-file backend\.env.microservices.local
```

The script compares, per selected table:

- row count in legacy SQLite
- row count in the target service database
- single-column primary-key min/max when available

Exit code:

- `0`: all selected tables match
- `1`: at least one table mismatched

## Suggested Rollout Order

1. Refresh service databases from the canonical SQLite snapshot if needed.
2. Run `validate_microservice_storage_parity.py --scope owned`.
3. Fix any mismatched tables before changing runtime startup.
4. Start split services without `ALLOW_SHARED_SPLIT_SERVICE_SQLITE`.
5. Verify `/ready` for the affected services plus the browser smoke flow through `gateway-bff`.

## Remaining Wave 4 Work

- example-audio OSS backfill is now available via:

```bash
python .\scripts\backfill_example_audio_to_oss.py --dry-run
python .\scripts\backfill_example_audio_to_oss.py
```

- notes exports now emit OSS object references inline on `/api/notes/export` when the bucket is configured; verify `object_key` and `signed_url` before treating local-only export handling as canonical

- extend parity checks beyond row counts to artifact metadata where needed
- move remaining media/export artifact references fully onto OSS-backed object keys
- add repair scripts for database rows and OSS metadata drift
- rehearse the same parity and rollback flow on the deployed remote environment
