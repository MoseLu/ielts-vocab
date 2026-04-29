# Test Report

Last updated: 2026-04-30

## 2026-04-30 Production Public API Full Test

Detailed report: `docs/operations/production-api-full-test-report-2026-04-30.md`

| Check | Result | Notes |
| --- | --- | --- |
| Public `/api/*` route baseline | PASS | `109/114` monolith route-methods covered by gateway; the 5 uncovered route-methods are legacy `tts-admin` and not publicly exposed. |
| Authenticated production matrix | PARTIAL | 125 requests: 94 passed, 31 failed. Auth, learning, TTS, speech, admin, and exam groups passed. |
| Targeted AI/notes retest | PARTIAL | 32 requests: 8 passed, 24 failed. Failures centered on AI upstream/gateway circuit, provider quota, and notes generation. |
| Post-restart spot check | PARTIAL | 10 requests: 6 passed, 4 failed. Books/auth/AI context/similar-words recovered; AI ask, review queue, game themes, and confusable custom chapter still failed. |
| Code-fix pass | PASS | Added local fixes for AI review-plan fallback, notes async job failure handling, and confusable custom chapter id collisions. Focused backend tests and repo guards passed. |

Key findings:

- `POST /api/books/ielts_confusable_match/custom-chapters` returned 500 in the full run and 504 after restart; catalog logs show cross-user duplicate `custom_book_chapters.id=1001`. Code now allocates custom chapter ids globally.
- `GET /api/ai/review-plan` and notes context logs show missing production table `user_learning_book_rollups`; review-plan now degrades to an empty profile snapshot instead of 500 on learner-profile build failure.
- Notes synchronous summary generation failed because MiniMax API key was unavailable; async generation returned 202 but its worker logged an app-context rollback error.
- Notes async summary worker rollback now runs inside `app.app_context()` and records failed jobs instead of crashing the worker on generation errors.
- `POST /api/ai/speaking/evaluate` reached provider logic but failed due to model free-tier exhaustion.
- The run left production probe artifacts that cannot be deleted through public API: user `codex_api_probe_20260429175738`, custom book `custom_f84821e7d686`, and a `language` word note.

Code-fix verification:

- `pytest backend/tests/test_ai_execution_speaking_internal_clients.py backend/tests/test_notes.py backend/tests/test_notes_service_api.py backend/tests/test_catalog_content_service_api.py backend/tests/test_confusable_custom_chapter_updates.py backend/tests/test_confusable_custom_lookup.py -q` -> PASS, 27 passed.
- `pnpm check:file-lines` -> PASS.
- `pnpm lint` -> PASS.
- `pytest backend/tests/test_source_text_integrity.py -q` -> PASS, 2 passed.

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
