# Submit Log — 2026-09-28 — ielts-vocab HANDOFF refresh

- Repository: products/ielts-vocab
- Branch: dev
- Date: 2026-09-28
- Operator: routine products/workbench L1+ dirty submit executor (audit-pass)

## Scope

Fifth (and last) of five commits closing the remaining L1+
dirty on `products/ielts-vocab` after the port-fix commit
`42260192 fix(ports): source TTS/ASR URLs from AXI_*_URL env with
safe fallback` landed. This commit refreshes the project
handoff doc.

## Commit

- Subject: `docs: HANDOFF refresh`
- Paths: `docs/HANDOFF.md`

### Diff stat

- 1 file changed, 1 insertion(+), 14 deletions(-)

### What changed

`docs/HANDOFF.md`:

- "Last verified" date string bumps from `2026-08-23` to
  `2026-09-25`, matching the last successful governance run.
- Drops the stale "Ahead-batch snapshot (2026-09-24)" section
  whose ahead-commits and per-batch counters were all-zero at
  the time and have since been overtaken by the actual L0
  submit-log snapshot batch.

The trailing "Generated from `docs/project-docs.manifest.json`"
note is preserved.

## Verification

- Tested: `git diff --stat docs/HANDOFF.md` → 1 file, +1/-14.
- Tested: `git diff docs/HANDOFF.md` shows only the date bump
  and the stale-section drop.
- Not-tested: `pnpm project-docs:build` (manifest-driven; runs
  on demand and would re-emit an updated HANDOFF.md).

## Risks

- Low. HANDOFF doc-only refresh. No code, no contract, no
  manifest JSON change.

## Directive

Owner-directed L1+ dirty closure on `products/ielts-vocab`
following the port-fix commit (`42260192`). Final of five
commits (proxy endpoint / test / deps / PRD done; HANDOFF
now). One intent per commit.
