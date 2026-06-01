# Ticket-Driven Release Workflow

Last updated: 2026-06-01

## Purpose

Daily IELTS Vocab development should follow one ticket-shaped flow whether the
request starts from a learner bug report, an operator request, or a developer
cleanup. The variable part is the requested behavior. Intake, implementation,
verification, release, production smoke, and ticket closeout stay fixed.

## Ticket Source

The canonical ticket source is `admin-ops-service` table `feature_wishes`.
The visible status values remain:

- `open`: submitted and not yet accepted for a change.
- `planned`: accepted or in progress.
- `done`: deployed and verified in production.

Internal work can use finer checkpoints in notes or submit logs:

```text
open -> planned -> coding -> local_verified -> pushed -> deploying -> prod_verified -> done
```

Only `open`, `planned`, and `done` are written to the product API today.

Operator-originated work should also get a `feature_wish` ticket before coding.
That keeps user reports and owner-requested changes on the same rail.

## Required Trailer

Every ticket-bound commit or release note must include:

```text
Ticket: feature_wish:<id>
```

Use one trailer per ticket when a release closes multiple reports.

## Standard SOP

1. Intake: resolve the ticket and render a Codex handoff.
2. Triage: confirm affected surface, account, data scope, and production status.
3. Locate: inspect the owning code and adjacent state boundary before editing.
4. Patch: make the smallest code change that satisfies the ticket.
5. Local verification: run focused tests first, then the nearest release-risk guard.
6. Git preflight: confirm branch, proxy, and remote reachability.
7. Commit: use the Lore commit format and include `Ticket: feature_wish:<id>`.
8. Push: use normal Git smart HTTP; do not update refs through GitHub API.
9. Deploy: use `.github/workflows/deploy-production.yml` or the documented manual fallback.
10. Production verification: run ticket-specific API/UI smoke against `https://axiomaticworld.com`.
11. Closeout: mark the ticket `done` only after production verification passes.
12. Archive: put evidence in the submit log or currentday report for production hotfixes.

## Helper Commands

Render a handoff for Codex:

```bash
FEATURE_WISH_API_TOKEN=<admin-token> \
python scripts/ops/feature-wish-workflow.py prepare --id 123 --set-status planned
```

Extract ticket IDs from the current commit:

```bash
python scripts/ops/feature-wish-workflow.py extract --rev HEAD
```

Check the local Git path before push:

```bash
python scripts/ops/feature-wish-workflow.py git-preflight --branch dev
```

Mark a ticket done after production verification:

```bash
FEATURE_WISH_API_TOKEN=<admin-token> \
python scripts/ops/feature-wish-workflow.py mark --id 123 --status done
```

The API base defaults to `https://axiomaticworld.com`. Override it with
`FEATURE_WISH_API_BASE` or `--api-base` for local split runtime.

## GitHub Actions Closeout

`deploy-production.yml` can close tickets automatically after deploy succeeds.
Enable it with production environment configuration:

- `FEATURE_WISH_CLOSEOUT_ENABLED=true`
- `FEATURE_WISH_API_BASE=https://axiomaticworld.com`
- `FEATURE_WISH_API_TOKEN=<admin bearer token secret>`

The closeout step scans the deployed commit for `Ticket: feature_wish:<id>` and
PATCHes each ticket to `done`. If the variables or token are absent, the step
skips without failing the release.

## Guardrails

- Do not mark `done` after local tests alone.
- Do not use GitHub API ref writes as a normal publish mechanism.
- Do not close a ticket when deploy succeeded but ticket-specific smoke failed.
- Keep production data repairs coupled with source-of-truth verification.
- For wrong-word, scoped learning, and progress bugs, inspect adjacent rollups
  and compatibility projections before declaring the ticket fixed.
