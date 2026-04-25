# Test Report

Last updated: 2026-04-25

## Scope

Continue verification for the current working tree changes around:

- backend catalog/phonetic fallback rollback behavior
- gateway HTTP proxy environment proxy isolation
- game session / word mastery campaign state
- frontend game map UI and asset manifest guardrails

## Environment

- Runtime PATH prefix: `/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin`
- Python: `pytest 9.0.3`
- Node: `v24.14.1`
- pnpm: `9.0.0`

## Results

| Command | Result | Notes |
| --- | --- | --- |
| `pytest backend/tests/test_vocabulary_loader.py backend/tests/test_phonetic_fallback.py backend/tests/test_http_proxy.py -q` | PASS | 14 passed, 16 warnings |
| `pytest backend/tests/test_source_text_integrity.py -q` | PASS | 2 passed |
| `pytest backend/tests/test_word_mastery_support.py -q` | PASS | 4 passed, warning-only SQLAlchemy/datetime noise |
| `pytest backend/tests/test_vocabulary_loader.py backend/tests/test_phonetic_fallback.py backend/tests/test_http_proxy.py backend/tests/test_word_mastery_support.py backend/tests/test_source_text_integrity.py -q` | PASS | 20 passed, 423 warnings |
| `pnpm --dir frontend exec vitest run src/components/practice/page/GameMode.test.tsx` | PASS | 5 passed |
| `pnpm --dir frontend exec vitest run src/components/practice/page/GameMode.test.tsx src/components/practice/page/GameModeSections.audio.test.tsx` | PASS | 7 passed |
| `pnpm --dir frontend verify:repo-guards` | PASS | file-line, design-token, style-discipline, lint all passed |
| `pnpm --dir frontend build` | PASS | Vite production build passed |
| `pnpm --dir frontend test` | FAIL | 507 passed, 1 failed; `SelectionWordLookup.test.tsx` outside-click close assertion timed out |
| `pnpm --dir frontend exec vitest run src/components/layout/navigation/SelectionWordLookup.test.tsx` | PASS | 8 passed when isolated |

## Fixes Made During Testing

- Added an explicit `aria-label="返回学习计划"` to the game map plan button so the accessible control name matches the intended action.
- Minified generated game asset `manifest.json` files so `check:file-lines` stays green without adding generated assets to the hand-edited oversize baseline.
- Converted new game map SCSS hardcoded `z-index`, fixed pixel widths, and raw color literals to existing design tokens / semantic color mixes.

## Asset Manifest Check

`frontend/assets/game/wuwei-transparent-v3/manifest.json` was checked against deliverable PNG files, excluding `_source`, debug, and contact-sheet images:

```json
{
  "deliverable_png": 125,
  "manifest_png": 125,
  "missing_from_manifest": [],
  "stale_manifest": []
}
```

## Follow-Up

- Re-run full `pnpm --dir frontend test` before submit. The only observed failure was not reproducible in the isolated test file and should be treated as a possible flaky timing issue unless it repeats.
