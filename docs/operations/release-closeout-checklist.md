# Release Closeout Checklist

Last updated: 2026-04-22

## Purpose

This runbook is the single closeout reference for the canonical remote release path. Use it after the normal deploy path to confirm the active release is healthy, bounded storage checks still pass, projection cutover state is intact, and evidence is archived in one place.

The production baseline is still:

- domain: `https://axiomaticworld.com`
- host: `119.29.182.134`
- browser ingress: `nginx -> gateway-bff -> split services`
- speech ingress: `nginx -> asr-socketio :5001`

## Preconditions

- The target code is already on `main` and passed CI.
- The standard production deploy path has been used:
  - GitHub Actions `deploy-production.yml`, or
  - manual `preflight-check.sh` + `deploy-release.sh`
- `/etc/ielts-vocab/backend.env` and `/etc/ielts-vocab/microservices.env` are present on the host.
- The shared venv exists at `/opt/ielts-vocab/venv`.

## Standard Flow

### 1. Run preflight and deploy

Preferred:

- Trigger `.github/workflows/deploy-production.yml` for the target `main` commit.

Manual fallback:

```bash
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/preflight-check.sh main
sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/deploy-release.sh main
```

### 2. Run the post-deploy closeout pack

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/release-closeout.sh
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com CLOSEOUT_SOURCE_SQLITE=/opt/ielts-vocab/source/production-repair-20260410.sqlite bash /opt/ielts-vocab/current/scripts/cloud-deploy/release-closeout.sh
```

This pack runs:

1. post-switch `smoke-check.sh`
2. bounded `wave4-storage-drill.sh`
3. `run-wave5-projection-cutover.py --verify-only`

The bounded storage drill resolves its source snapshot in this order:

- explicit `CLOSEOUT_SOURCE_SQLITE` / `DRILL_SOURCE_SQLITE`
- `SOURCE_SQLITE_PATH` or `SQLITE_DB_PATH`
- `backend/database.sqlite`
- newest `APP_HOME/source/*.sqlite`

Routine release closeout now runs the bounded storage drill with `CLOSEOUT_RUN_STORAGE_PARITY=false` by default. That keeps the artifact/reference checks and smoke path in the closeout, while avoiding false failures against an archival SQLite snapshot after live PostgreSQL writes continue in production. Set `CLOSEOUT_RUN_STORAGE_PARITY=true` only when you also have a fresh canonical SQLite snapshot for the current production state.

By default the bounded storage drill uses:

- `DRILL_EXAMPLE_AUDIO_BOOK_ID=ielts_reading_premium`
- `DRILL_EXAMPLE_AUDIO_LIMIT=200`
- `DRILL_WORD_AUDIO_BOOK_ID=ielts_reading_premium`
- `DRILL_WORD_AUDIO_LIMIT=200`

### 3. Archive evidence

The closeout script writes raw logs under:

```text
/var/log/ielts-vocab/release-closeout/<timestamp>/
```

Expected files:

- `smoke.log`
- `storage-drill.log`
- `projection-verify.log`

Turn the storage drill log into a durable markdown record:

```bash
/opt/ielts-vocab/venv/bin/python /opt/ielts-vocab/current/scripts/create-wave4-remote-record.py \
  --log-path /var/log/ielts-vocab/release-closeout/<timestamp>/storage-drill.log \
  --host 119.29.182.134 \
  --command "sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh"
```

Then create a closeout submit record in `docs/logs/submit/` that includes:

- deployed release path
- smoke result
- storage drill result
- projection verify result
- any bounded repair flags that were needed

## Acceptance

The closeout is complete only when all of the following are true:

- deploy completed on the intended release
- post-switch smoke passed
- bounded storage drill passed
- `run-wave5-projection-cutover.py --verify-only` exited successfully
- evidence paths and the markdown submit record are linked from the release note or submit log

## References

- [cloud-microservices-deployment.md](./cloud-microservices-deployment.md)
- [remote-production-baseline.md](./remote-production-baseline.md)
- [wave4-storage-parity-runbook.md](./wave4-storage-parity-runbook.md)
