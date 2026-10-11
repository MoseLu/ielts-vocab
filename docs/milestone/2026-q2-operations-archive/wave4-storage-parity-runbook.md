# Wave 4 Storage Parity Runbook

Last updated: 2026-04-11 15:39:26 +08:00

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
- `tts-media-service`
- `asr-service`
- `admin-ops-service`

Allowed targets:

- service-owned PostgreSQL via `*_DATABASE_URL` or `*_POSTGRES_*`
- explicit service-local SQLite paths such as a temp test database

Blocked target:

- implicit shared fallback `backend/database.sqlite`

Break-glass override:

```bash
ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES=notes-service
```

Emergency global override:

```bash
ALLOW_SHARED_SPLIT_SERVICE_SQLITE=true
```

Prefer the service-scoped allowlist for a controlled rollback or repair drill. Use the global override only when several guarded services must temporarily share the fallback together, and do not leave either env enabled in normal split-service startup.

Audit the current guard coverage with:

```bash
python .\scripts\describe-service-storage-boundary-plan.py --json
```

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

Default source resolution order:

- explicit `--source-sqlite`
- `SOURCE_SQLITE_PATH` or `SQLITE_DB_PATH`
- `backend/database.sqlite`
- newest `APP_HOME/source/*.sqlite` snapshot on the host

## Parity Repair

When a selected service drifts from the canonical SQLite snapshot, repair it with:

```bash
python .\scripts\repair_microservice_storage_parity.py --scope owned
```

Useful variants:

```bash
python .\scripts\repair_microservice_storage_parity.py --service identity-service --service learning-core-service
python .\scripts\repair_microservice_storage_parity.py --scope bootstrap
python .\scripts\repair_microservice_storage_parity.py --dry-run
```

The repair script:

- validates the selected service tables first
- skips clean services
- replaces only mismatched target tables from the selected SQLite snapshot
- validates again and exits `1` if any mismatch remains

## Suggested Rollout Order

1. Refresh service databases from the canonical SQLite snapshot if needed.
2. Run `validate_microservice_storage_parity.py --scope owned`.
3. Fix any mismatched tables with `repair_microservice_storage_parity.py` before changing runtime startup.
4. Start split services without `ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES` or `ALLOW_SHARED_SPLIT_SERVICE_SQLITE`.
5. Verify `/ready` for the affected services plus the browser smoke flow through `gateway-bff`.

For the deployed remote environment, the same checks can now be rehearsed from `/opt/ielts-vocab/current` with:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
```

Useful remote variants:

```bash
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_REPAIR=true bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_SOURCE_SQLITE=/opt/ielts-vocab/source/production-repair-20260410.sqlite bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_NOTES_EXPORT_REPAIR=true DRILL_NOTES_USER_ID=1 DRILL_NOTES_START_DATE=2026-03-30 DRILL_NOTES_END_DATE=2026-03-30 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_RUN_WORD_AUDIO_REPAIR=true DRILL_WORD_AUDIO_BOOK_ID=ielts_reading_premium DRILL_WORD_AUDIO_LIMIT=200 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_NOTES_USER_ID=1 DRILL_NOTES_START_DATE=2026-03-30 DRILL_NOTES_END_DATE=2026-03-30 bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab DRILL_ROLLBACK_TARGET=/opt/ielts-vocab/releases/<timestamp>-<sha> bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
```

If the active release artifact no longer carries `backend/database.sqlite`, keep a canonical snapshot under `/opt/ielts-vocab/source/*.sqlite` or set `DRILL_SOURCE_SQLITE` explicitly for the remote operator run.

For routine production release closeout, prefer `CLOSEOUT_RUN_STORAGE_PARITY=false` and keep full SQLite parity as an explicit operator drill. Once split PostgreSQL is the live write source, an archival SQLite snapshot will naturally drift unless you refresh it first.

When a remote repair or rollback drill must temporarily restart only selected guarded services against the shared SQLite fallback, use:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service asr-service
```

The wrapper sets `ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES` only for the targeted systemd restarts, waits for each service `/ready`, and then unsets the manager env automatically.
Set `SHARED_SQLITE_OVERRIDE_RECORD_PATH` when the restart also needs a raw operator log for later archiving.

For a rollback rehearsal around the same release set, use:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_EXECUTE=true bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_TARGET_RELEASE=/opt/ielts-vocab/releases/<timestamp>-<sha> bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
```

To keep an archiveable operator trail, capture the raw remote output to a log file first:

```bash
sudo mkdir -p /var/log/ielts-vocab/wave4
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com DRILL_RECORD_PATH=/var/log/ielts-vocab/wave4/storage-drill-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_RECORD_PATH=/var/log/ielts-vocab/wave4/rollback-rehearsal-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-$(date -u +%Y%m%dT%H%M%SZ).log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
```

Then convert the raw log into a short markdown record:

```bash
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/storage-drill-<timestamp>.log --host 119.29.182.134 --command "sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com DRILL_RECORD_PATH=/var/log/ielts-vocab/wave4/storage-drill-<timestamp>.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh"
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/rollback-rehearsal-<timestamp>.log --host 119.29.182.134 --command "sudo APP_HOME=/opt/ielts-vocab REHEARSAL_RECORD_PATH=/var/log/ielts-vocab/wave4/rollback-rehearsal-<timestamp>.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh"
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py --log-path /var/log/ielts-vocab/wave4/shared-sqlite-override-<timestamp>.log --host 119.29.182.134 --command "sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-<timestamp>.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service"
```

The record generator writes `<timestamp>-wave4-*.md` next to the raw log by default. Pass `--output docs/logs/submit/<name>.md` when the result should also be copied into the repository's append-only log folder.

## Artifact Parity Operators

- example-audio OSS backfill is now available via:

```bash
python .\scripts\backfill_example_audio_to_oss.py --dry-run
python .\scripts\backfill_example_audio_to_oss.py
```

- notes export OSS references can now be validated end-to-end via:

```bash
python .\scripts\validate_notes_export_oss_reference.py --user-id 1 --start-date 2026-03-30 --end-date 2026-03-30
python .\scripts\validate_notes_export_oss_reference.py --user-id 1 --format txt --type summaries
```

- notes exports still emit OSS object references inline on `/api/notes/export` when the bucket is configured; treat the script above as the operator check for `object_key`, payload bytes, and content type before treating OSS-backed export handling as canonical
- notes export OSS drift can now be repaired by replaying the same export through `notes-service` and re-validating the stored object:

```bash
python .\scripts\repair_notes_export_oss_reference.py --user-id 1 --start-date 2026-03-30 --end-date 2026-03-30
python .\scripts\repair_notes_export_oss_reference.py --user-id 1 --format txt --type summaries
```

- the repair script overwrites the target OSS object for the selected export filename and then verifies `object_key`, payload bytes, and content type against the regenerated export response
- the deployed remote drill can run the same flow inline with `DRILL_RUN_NOTES_EXPORT_REPAIR=true`, which replaces the read-only notes export validation step for that run
- word-audio OSS metadata drift can now be validated end-to-end via:

```bash
python .\scripts\validate_word_audio_oss_parity.py
python .\scripts\validate_word_audio_oss_parity.py --book-id ielts_reading_premium --limit 200 --verbose
python .\scripts\validate_word_audio_oss_parity.py --require-materialized --book-id ielts_reading_premium --limit 200
```

- word-audio OSS repair uses the local canonical cache as the primary source and can fall back to the current OSS payload when only `content_type` metadata drift needs repair:

```bash
python .\scripts\backfill_word_audio_to_oss.py --dry-run
python .\scripts\backfill_word_audio_to_oss.py --book-id ielts_reading_premium
python .\scripts\backfill_word_audio_to_oss.py --repair-size-mismatch --repair-content-type-mismatch
```

- the deployed remote drill can run the same word-audio repair flow inline with `DRILL_RUN_WORD_AUDIO_REPAIR=true`
- by default, word-audio validation treats `missing_everywhere` as informational, because the cache/OSS set may still be lazily materialized on demand; use `--require-materialized` only when auditing a fully warmed cache set
- example-audio OSS metadata drift can now be validated via:

```bash
python .\scripts\validate_example_audio_oss_parity.py
python .\scripts\validate_example_audio_oss_parity.py --book-id ielts_reading_premium --verbose
python .\scripts\validate_example_audio_oss_parity.py --require-materialized --book-id ielts_reading_premium
```

By default, example-audio validation treats lazy-generation gaps (`missing_everywhere`) as informational only, because dictation example audio is still generated on demand. Use `--require-materialized` only when auditing a fully warmed cache set. The example-audio and word-audio validation scripts both still flag byte-length drift and `content_type` drift against the canonical `audio/mpeg` expectation.

- example-audio OSS repair still uses the backfill script, and can now also repair byte-length drift explicitly:

```bash
python .\scripts\backfill_example_audio_to_oss.py --dry-run
python .\scripts\backfill_example_audio_to_oss.py --repair-size-mismatch
python .\scripts\backfill_example_audio_to_oss.py --repair-content-type-mismatch
```

## Wave 4 Completion Evidence

- Remote storage drill completed on `119.29.182.134` with parity validation, parity repair verification, notes export OSS validation, bounded example-audio validation on `ielts_reading_premium` (`limit=200`), bounded word-audio validation on `ielts_reading_premium` (`limit=200`), and full remote smoke; archived in [20260411-072543-wave4-storage-drill.md](../logs/submit/20260411-072543-wave4-storage-drill.md).
- Remote shared-`SQLite` scoped override restart completed for `notes-service` and re-validated `/ready`; archived in [20260411-072709-wave4-shared-sqlite-override-restart.md](../logs/submit/20260411-072709-wave4-shared-sqlite-override-restart.md).
- Remote rollback rehearsal completed by rolling from `/opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635` to `/opt/ielts-vocab/releases/20260411T033543Z-ae6204d60a3c` and back, with smoke checks passing on both sides; archived in [20260411-072946-wave4-rollback-rehearsal.md](../logs/submit/20260411-072946-wave4-rollback-rehearsal.md).
- The raw remote logs remain archived under `/var/log/ielts-vocab/wave4/` on the host, and each markdown record includes the original log path plus SHA256 for later integrity checks.
