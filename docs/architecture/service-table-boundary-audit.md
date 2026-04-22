# Service Table Boundary Audit

Last updated: 2026-04-10

## Purpose

This Wave 4 audit is the table-level companion to [service-ownership-matrix.md](./service-ownership-matrix.md).

It answers two questions for every SQLAlchemy table in the split backend:

1. Which service is the single authoritative owner for writes?
2. Which non-owning services still mount that table as `read-only` or `transitional` access?

The checked-in source of truth lives in [service_table_plan.py](../../packages/platform-sdk/platform_sdk/service_table_plan.py), and regression coverage must keep every current table classified exactly once as owned.

## Access Labels

- `owned`: the service is authoritative for writes and migration ownership.
- `read-only`: the service may still mount the foreign table for request/auth/context reads, but must not write it.
- `transitional`: the service still mounts the foreign table as a compatibility shadow or temporary local read-side until an internal contract, projection, or event-driven model replaces it.

## How To Inspect The Audit

Render the audit by service:

```bash
python .\scripts\describe-service-table-boundary-audit.py
python .\scripts\describe-service-table-boundary-audit.py --service notes-service --json
```

Render the audit by table:

```bash
python .\scripts\describe-service-table-boundary-audit.py --view tables
python .\scripts\describe-service-table-boundary-audit.py --view tables --table custom_books --json
```

## Current Wave 4 Summary

- `identity-service`, `tts-media-service`, and `asr-service` currently expose owned tables only.
- `learning-core-service` keeps `users` and `revoked_tokens` as `read-only`, while `custom_books*` stays `transitional` until catalog-owned reads are fully remote.
- `catalog-content-service` keeps auth context as `read-only`, and `user_word_notes` remains `transitional`.
- `notes-service` keeps auth context plus `custom_books` as `read-only`, while learning-core study-state tables remain `transitional`.
- `ai-execution-service` keeps auth context as `read-only`; learning-core, notes, and catalog tables remain `transitional` until the remaining internal-call fallback paths are retired.
- `admin-ops-service` treats identity, learning-core, and catalog shared-table reads as `transitional` until Wave 5 event-driven read models replace them.

## Wave 4 Exit Criteria For This Audit

- every SQLAlchemy table is assigned to exactly one owning service
- every non-owning access is explicitly labeled `read-only` or `transitional`
- split-service startup and parity tooling continue to use the same table plan
- Wave 5 and Wave 6 work may only remove `transitional` mounts, not add new unlabeled shared access
