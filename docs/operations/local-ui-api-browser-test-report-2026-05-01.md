# Local UI/API Browser Test Report - 2026-05-01

## Summary

- Target: local checkout at commit `15fdf17c`, branch `dev`.
- Time window: 2026-05-01 14:50-15:02 +0800.
- Browser target: `http://localhost:3002`.
- API ingress: `http://127.0.0.1:8000`.
- Speech service: `http://127.0.0.1:5001`.
- Account: local admin account `admin`.
- Scope: UI/UX-reachable public APIs only. `/internal/*`, legacy `tts-admin`, and public endpoints without a stable UI path are listed as out of UI scope rather than failures.
- Browser tool: Browser Use in-app browser, session `IELTS UI API test`.

## Baseline

Route baseline command:

```bash
PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH \
  python scripts/describe-monolith-route-coverage.py --surface all --json
```

Route baseline result:

| Metric | Count |
| --- | ---: |
| Monolith routes | 108 |
| Monolith route-methods | 117 |
| Gateway-covered monolith route-methods | 112 |
| Gateway-uncovered monolith route-methods | 5 |
| Gateway route-methods | 56 |
| Gateway-only route-methods | 2 |

Runtime preflight:

| Check | Result |
| --- | --- |
| `http://127.0.0.1:3002/plan` | `200 text/html` |
| `http://127.0.0.1:8000/api/books` | `200 application/json` |
| `http://127.0.0.1:8000/api/auth/me` | `200 application/json` |
| `http://127.0.0.1:8000/health` | `200 application/json` |
| `http://127.0.0.1:5001/health` | `200 application/json` |

Raw evidence:

- Route coverage JSON: `/tmp/ielts-local-ui-api-route-coverage-20260501.json`
- Browser result JSON: `/tmp/ielts-ui-api-browser-results-20260501.json`
- API spot-check JSON: `/tmp/ielts-local-ui-api-spotcheck-20260501-adjusted.json`
- Screenshots: `/tmp/ielts-ui-api-screenshots-20260501/`

## Browser Coverage

| Area | UI path / action | Result | API groups exercised |
| --- | --- | --- | --- |
| Auth/Profile | Logout from profile, log back in as admin | PASS | `auth/login`, `auth/logout`, `auth/me` |
| Home/Plan | `/plan` loaded today todos and book progress | PASS | `auth`, `books`, `ai/learner-profile`, `ai/home-todos`, `progress` |
| Books/Catalog | `/books` loaded IELTS catalog | PASS | `books`, `books/progress`, `books/my` |
| Global Search | Header search for `quit` | PASS | `books/search`, `books/word-details` |
| Practice/Learning | `/practice?review=due` loaded due-review surface | PASS | `ai/quick-memory`, `books`, `progress` |
| Confusable Practice | `/practice/confusable?book=ielts_confusable_match&chapter=1` loaded after slow settle | PASS | `books/<book>/chapters`, chapter progress |
| Errors | `/errors` loaded wrong-word search/review controls | PASS | `ai/wrong-words`, custom-book helpers |
| Stats | `/stats` loaded learning and review stats | PASS | `ai/learning-stats`, `ai/learner-profile`, `progress` |
| Game | `/game` loaded map and started current mission | PASS | `ai/practice/game/themes`, `state`, `session/start` |
| TTS | `/vocab-test` replay button stayed active after click | PASS | `tts/word-audio`, TTS audio metadata/content |
| AI Assistant | Opened assistant and sent `给我 quit 的真题例句` | PASS | `ai/greet`, `ai/ielts-example` or degraded assistant response path |
| Journal/Notes | `/journal` loaded journal shell | PASS | `notes/summaries`, `notes`, `ai/learner-profile` |
| Admin | `/admin` loaded dashboard/users/feedback shell | PASS | `admin/overview`, `admin/users`, `admin/word-feedback` |
| Exam | `/exams` loaded empty state | PARTIAL | `exams` list only; no local paper data for attempt flow |
| Vocab Test | `/vocab-test` loaded question and replay controls | PASS | `books/<listening>/words`, TTS audio |
| Bug Feedback | Profile `Bug反馈` modal opened, create attempt visible, later reload showed request failure | FAIL | `feature-wishes` |

## API Spot Check

Authenticated spot check: 36 requests, 35 passed, 1 failed.

Passed groups:

- `auth`: anonymous probe, login, `me`, logout.
- `books/catalog`: books, search, word details, my books, progress.
- `progress` and `vocabulary`: legacy stats/progress reads.
- `ai`: learning stats, learner profile, home todos, game themes/state, wrong words, quick-memory queue, IELTS example, word family, collocations, review plan, vocab assessment.
- `notes`: summaries, notes list, export.
- `admin`: overview, users, word feedback.
- `exam`: papers list.
- `tts`: voices, word audio metadata, follow-read word with `w=language`.

Failure:

| Priority | Endpoint | Evidence | User-visible impact |
| --- | --- | --- | --- |
| P1 | `GET /api/feature-wishes` | Authenticated API spot-check returned `500 Internal Server Error`; browser modal showed `请求失败，请稍后重试`. | Profile `Bug反馈` cannot reliably list existing feedback, so the user cannot inspect or manage submitted bugs from the UI. |

## Out Of UI Scope

- `/internal/*` service-to-service routes.
- Legacy `tts-admin` route-methods not exposed through the public gateway.
- Exam attempt save/submit/result flow: local `/exams` showed `暂无可用真题`, so the browser could only verify the list empty state.
- Notes summary generation: not executed because it depends on configured generation provider availability; existing page/list/export paths were checked.
- Real microphone permission and live ASR audio: not forced; the plan allowed visible fallback behavior instead of requiring real mic input.
- Destructive cleanup such as deleting the temporary Bug feedback item was not performed in this run.

## Side Effects

- Browser session logged out and then logged back in as `admin`.
- A local Bug feedback create attempt used title `codex-ui-api-test-20260501`; because subsequent listing failed with `500`, persistence and cleanup could not be confirmed from the UI.
- Game mission start likely created or updated local learning/game session state.
- Vocab test audio replay may have touched TTS/audio cache.
- No production or remote environment was touched.

## Verification Notes

- Browser console errors from the app under test were not observed during the page sweep; Browser Use's own Statsig/network diagnostic messages were ignored as plugin-side noise.
- The first page sweep captured some slow pages before data settled; `/game`, `/practice/confusable`, and `/vocab-test` passed on a slower recheck.
- Current worktree already had unrelated dirty files under `frontend/src/components/errors`, `frontend/src/composables/errors`, `frontend/src/features/vocabulary`, and `frontend/src/styles/pages/errors`; this report did not modify those files.

## Follow-Up

- Fix `GET /api/feature-wishes` under the local split/gateway runtime, then retest the Profile `Bug反馈` modal list/create/update/delete path.
- Seed or import at least one local exam paper before the next UI/API browser sweep so `/exams/:paperId`, attempt save, submit, and result can be exercised at UI level.
- If provider credentials are intentionally available, run a separate notes/AI generation pass that distinguishes provider failures from UI/API regressions.
