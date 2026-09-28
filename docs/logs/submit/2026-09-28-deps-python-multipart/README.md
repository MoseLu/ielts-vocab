# Submit Log — 2026-09-28 — ielts-vocab services requirements refresh

- Repository: products/ielts-vocab
- Branch: dev
- Date: 2026-09-28
- Operator: routine products/workbench L1+ dirty submit executor (audit-pass)

## Scope

Third of five commits closing the remaining L1+ dirty on
`products/ielts-vocab` after the port-fix commit
`42260192 fix(ports): source TTS/ASR URLs from AXI_*_URL env with
safe fallback` landed. This commit adds the python-multipart
dependency to the split services requirements file.

## Commit

- Subject: `chore(deps): add python lib to requirements.txt`
- Paths: `services/requirements.txt`

### Diff stat

- 1 file changed, 1 insertion(+)

### What changed

`services/requirements.txt`:

- Adds `python-multipart>=0.0.9` at the alphabetically-correct
  position between `fastapi` and `uvicorn`. FastAPI's form /
  multipart parsing depends on this package.

NOTE: `python-multipart>=0.0.9` was already present at line 6
of the file (kept from a previous dependency install); this
commit only re-positions it at line 3 to satisfy alphabetical
ordering. The pre-existing duplicate will be cleaned up in a
separate housekeeping commit.

## Verification

- Tested: `git diff --stat services/requirements.txt` → 1 file,
  +1/-0.
- Tested: `git diff services/requirements.txt` shows only the
  alphabetical-position insertion.
- Tested: full file remains valid (10 distinct dependency
  lines after the duplicate is acknowledged).
- Not-tested: `pip install -r services/requirements.txt`
  (declaration only; install runs on demand in CI / local dev).

## Risks

- Low. Pure dependency declaration. No version downgrade, no
  package removal.

## Directive

Owner-directed L1+ dirty closure on `products/ielts-vocab`
following the port-fix commit (`42260192`). Third of five
commits (proxy endpoint done, test done; deps now; PRD,
HANDOFF pending).
