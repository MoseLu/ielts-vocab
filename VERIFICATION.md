# Verification

## Commands

```bash
pnpm --dir frontend verify:repo-guards
./start-project.sh
```

## Current evidence

- **Last verified:** 2026-09-25
- **Status:** verified on 2026-08-23 — manifest v2 path-fix-up applied: PRD.md, TDD.md, root TODO.md, root MILESTONE.md do not exist on disk and were removed from readOrder / currentWork; backend/TODO.md and docs/project-audit-2026-03-31.md used as live anchors.
- Full `pnpm --dir frontend verify:repo-guards` was not re-run this session; owner must re-run to confirm frontend verification still passes.

## Source manifest

- `docs/project-docs.manifest.json` (`commands.verify`)

## Related documents

- `AGENTS.md`
- `README.md`
- `INDEX.md`
- `backend/TODO.md`
- `docs/project-audit-2026-03-31.md`
- `docs/state/CHANGELOG.md`
- `docs/state/DEBUG.md`
- `docs/state/TEST_REPORT.md`
- `VERIFICATION.md` (this file)