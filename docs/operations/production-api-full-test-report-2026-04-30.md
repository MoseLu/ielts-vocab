# Production Public API Full Test Report - 2026-04-30

## Summary

- Target: `https://axiomaticworld.com` public `/api/*` surface through nginx and `gateway-bff`.
- Time window: 2026-04-30 01:53-02:11 +0800.
- Accounts: production admin `admin`; existing probe user `codex_api_probe_20260429175738`.
- Route baseline command:
  `PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH python scripts/describe-monolith-route-coverage.py --surface all --json`
- Public gateway baseline: 109 of 114 monolith route-methods covered; 2 gateway-only route-methods; 5 legacy `tts-admin` route-methods not publicly exposed and not tested.

## Result Overview

| Pass | Scope | Result | Notes |
| --- | --- | --- | --- |
| Route coverage baseline | public `/api/*` | PASS | 109/114 covered; uncovered routes are legacy `tts-admin` only. |
| Full production matrix | 125 requests | PARTIAL | 94 passed, 31 failed. Failures concentrated in catalog confusable custom chapters, AI, and notes generation. |
| Targeted AI/notes retest | 32 requests | PARTIAL | 8 passed, 24 failed. Confirms AI failures were not only test ordering, though several failures overlapped service restarts. |
| Post-restart spot check | 10 requests | PARTIAL | 6 passed, 4 failed. Public books/auth/AI context/similar-words recovered; AI ask, review queue, game themes, and confusable custom chapter still failed. |
| Production log inspection | gateway, AI, learning-core, notes | PASS | SSH succeeded; logs captured concrete service-side causes listed below. |

Full matrix by group:

| Group | Total | Passed | Failed |
| --- | ---: | ---: | ---: |
| preflight | 2 | 2 | 0 |
| auth | 15 | 15 | 0 |
| catalog | 19 | 18 | 1 |
| learning | 20 | 20 | 0 |
| ai | 41 | 13 | 28 |
| notes | 6 | 4 | 2 |
| tts | 10 | 10 | 0 |
| speech | 1 | 1 | 0 |
| admin | 5 | 5 | 0 |
| exam | 6 | 6 | 0 |

## Passed Areas

- Public routing and base smoke: `/`, `/api/books`.
- Auth/session: anonymous `me`, admin login/me/refresh/logout, temp-user login/me/logout, non-admin admin denial, avatar same-value update, email/recovery validation paths.
- Catalog read APIs: books, chapters, words, search, categories, levels, stats, examples, word details, vocabulary list/day/stats.
- Learning and personalization APIs: legacy progress, book progress, chapter progress, mode progress, my-books add/remove, favorites add/status/remove, familiar add/status/remove, word note update, word feedback submit.
- TTS and speech: voices, word-audio metadata/head/content, follow-read word/chunked audio, example-audio head/get/metadata-only, TTS generate, speech transcribe.
- Admin/exam: overview, users, user detail, set-admin false on probe user, word-feedback list, exam list and not-found attempt/result paths.

## Failures

| Area | Endpoint | Status | Evidence / likely cause |
| --- | --- | ---: | --- |
| Catalog | `POST /api/books/ielts_confusable_match/custom-chapters` | 500, later 504 | Catalog logs show duplicate global primary key `custom_book_chapters.id=1001`: custom chapter ids were allocated per user book while the table primary key is global. Code fix added 2026-04-30; deploy/retest still required. |
| AI | `GET /api/ai/quick-memory/review-queue` | 503 | Strict boundary: `learning-core-service unavailable`, action `quick-memory-review-queue-read`. Logs show learning-core was unavailable during retest restart window. |
| AI | `GET /api/ai/practice/game/themes` | 503 | Full run: `game themes unavailable`; post-restart spot check: gateway circuit open after prior AI failure. |
| AI | `GET /api/ai/review-plan` | 500 then 503 | Logs show `psycopg2.errors.UndefinedTable: relation "user_learning_book_rollups" does not exist` while building review-plan data. Code fix added empty-profile fallback for this strict AI runtime path; deploy/retest still required. |
| AI | Multiple AI routes after upstream failures | 503 or nginx 502 | Gateway circuit opened for `ai-execution-service`; targeted retest also overlapped systemd restarts of gateway/learning-core/ai-execution/notes. |
| AI provider | `POST /api/ai/speaking/evaluate` | 502 | Response: free tier of model exhausted. This is a provider/account quota failure, not a request-shape failure. |
| AI provider | `POST /api/ai/ask` | 500 after restart | Public response: `AI 服务暂时不可用，请稍后重试`; logs also show notes/AI paths missing MiniMax API key in related generation flow. |
| Notes | `POST /api/notes/summaries/generate` | 400 then 500 | Future-date probe correctly returned 400. Today-date retest returned 500; logs show `No MiniMax API key available`. |
| Notes | `POST /api/notes/summaries/generate-jobs` | 400 then 202 | Future-date probe correctly returned 400. Today-date retest accepted async job with 202, but logs show worker thread later hit app-context rollback after generation failure. Code fix added 2026-04-30; deploy/retest still required. |

Production logs captured these concrete backend errors:

- `relation "user_learning_book_rollups" does not exist` in `ai-execution-service` / notes context paths.
- `No MiniMax API key available` during notes summary generation.
- `Working outside of application context` in async notes summary job rollback.
- systemd restarted `gateway-bff`, `learning-core-service`, `ai-execution-service`, and `notes-service` during the targeted retest window.

## Side Effects And Cleanup

| Object | Result | Cleanup status |
| --- | --- | --- |
| `codex_api_probe_20260429175738` user | Created by first run when the temp password was accidentally set to the placeholder value. | No public delete-user endpoint. Admin `set-admin=false` verified. |
| `custom_f84821e7d686` custom book | Created by full authenticated run. | No public delete custom-book endpoint. |
| `language` word note | Updated by full authenticated run. | No public delete note endpoint. |
| Learning progress / mode progress / quick-memory / stats events | Some admin writes succeeded. | No public reset/delete endpoint for these ledgers. |
| Favorites, familiar words, wrong words, my-books | Add/sync operations were followed by delete/all-clear cleanup where public endpoints exist. | Cleanup endpoints returned expected statuses. |
| TTS/example audio cache | Audio generation and metadata probes may have populated media cache. | Cache retained by design. |
| Notes async job | Today-date job returned 202 with job id `694c3b09fe454463ac4ff8c61ca1e82d`. | No public delete job endpoint; worker logged generation failure. |

## Raw Evidence

- Route coverage JSON: `/tmp/ielts-prod-api-route-coverage.json`
- First run with bad admin password handling: `/tmp/ielts-prod-api-full-results.json`
- Authenticated full matrix: `/tmp/ielts-prod-api-full-results-authfixed.json`
- Targeted AI/notes retest: `/tmp/ielts-prod-api-targeted-retest.json`
- Post-restart spot check: `/tmp/ielts-prod-api-post-restart-spotcheck.json`

These raw files are local execution artifacts and intentionally omit passwords/tokens from summaries.

## Fix Status

Code fixes added after this production run:

- `GET /api/ai/review-plan`: now catches learner-profile build failures and returns an empty review-plan snapshot instead of 500 when strict AI runtime cannot use local learning tables.
- `POST /api/notes/summaries/generate-jobs`: async worker rollback and failed-job update now run inside `app.app_context()` in both split service and monolith compatibility paths.
- `POST /api/books/ielts_confusable_match/custom-chapters`: custom chapter id allocation now scans all existing numeric custom chapter ids, avoiding cross-user global primary-key collisions.

Verification run locally:

- `pytest backend/tests/test_ai_execution_speaking_internal_clients.py backend/tests/test_notes.py backend/tests/test_notes_service_api.py backend/tests/test_catalog_content_service_api.py backend/tests/test_confusable_custom_chapter_updates.py backend/tests/test_confusable_custom_lookup.py -q` -> 27 passed.
- `pnpm check:file-lines` -> passed.
- `pnpm lint` -> passed.
- `pytest backend/tests/test_source_text_integrity.py -q` -> 2 passed.

## Follow-Up

- Deploy the code fixes above and rerun the production `/api/*` matrix.
- Audit why production `ai-execution-service` still attempted local learner-profile shared-table reads, and verify the review-plan fallback removes the `user_learning_book_rollups` 500 without weakening strict service boundaries.
- Fix notes summary runtime configuration so MiniMax credentials are available where synchronous and async generation run.
- Re-run the full matrix after the above fixes, preferably with a dedicated cleanup-capable test account or admin-side cleanup endpoint.
