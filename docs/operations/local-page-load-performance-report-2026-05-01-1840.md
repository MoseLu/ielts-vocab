# Local Page Load Performance Report - 2026-05-01 18:40

## Summary

- Target: local split runtime at `http://127.0.0.1:3002`, API ingress `http://127.0.0.1:8000`, speech service `http://127.0.0.1:5001`.
- Checkout: branch `dev`, commit `15fdf17c`.
- Time window: 2026-05-01 18:17-18:49 +0800.
- Viewport: desktop `1440x900`.
- Account: local `admin` account.
- Thresholds: first visible `<=2s`, core content `<=4s`, stable/settled interactive `<=6s`.
- Evidence JSON: `/tmp/ielts-page-load-report-20260501-1840/results.json`.
- Harness: temporary Playwright script `/tmp/ielts-page-load-perf.mjs`; visual spot check used Computer Use against the already open Chrome tab.

## Headline Findings

1. Cold unauthenticated loading is the biggest user-experience risk. The sweep recorded `/login` blank beyond `13s`, `/register` first visible at `9.7s`, and `/` first visible at `11.2s` / interactive at `13.2s`. A focused control run showed the same login page first visible at `3651ms` normally, but `143ms` when `fonts.googleapis.com` / `fonts.gstatic.com` were blocked, so the external Google Fonts dependency is a direct contributor.
2. Game default entrypoints need attention. `/game` stayed on `加载中...` beyond `13s`; `/game/themes` stayed on `正在载入主题地图...` beyond `9s`. The explicit themed map `/game/themes/study-campus` loaded in `1.9s`, so the slow path is likely the default/theme-selection bootstrap, not the whole game renderer.
3. Several learning surfaces are under the `6s` threshold but close enough to feel heavy: `/vocab-test` settled at `5.6s`, `/practice?review=due` at `5.3s`, and `/practice?mode=errors` at `5.1s`. These correlate with slower book-word fetches and repeated aborted `cache_only=1` TTS preloads.
4. Most regular authenticated pages are acceptable on a warm app shell: `/plan`, `/books`, `/errors`, `/stats`, `/profile`, `/admin`, `/journal`, and `/exams` all became interactive in roughly `1.9s-2.6s`.
5. Core dialogs mostly open quickly. Settings/help/book modal/profile Bug feedback open in under `200ms`; AI assistant opens in `379ms` but waits about `5.4s` for API/context settle.

## Page Timing Table

| Area | Path | Result | First visible | Core visible | API settle | Interactive | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Auth | `/login` | FAIL | - | - | - | - | Blank beyond `13s` in sweep; Google Fonts control points to external font blocking. |
| Auth | `/register` | SLOW | 9705ms | 9707ms | 10209ms | 11412ms | Same cold font/app-shell issue. |
| Auth | `/forgot-password` | PASS | 120ms | 122ms | 625ms | 1827ms | Warm auth route loaded normally. |
| Public | `/terms` | PASS | 426ms | 429ms | 932ms | 2134ms | OK. |
| Public | `/404` | PASS | 413ms | 414ms | 918ms | 2121ms | OK. |
| Redirect | `/` | SLOW | 11199ms | 11210ms | 12017ms | 13220ms | Cold redirect/app-shell path is too slow. |
| Home | `/plan` | PASS | 171ms | 363ms | 867ms | 2068ms | OK. |
| Books | `/books` | PASS | 162ms | 164ms | 770ms | 1972ms | OK. |
| Books | `/books/create` | PASS | 145ms | 461ms | 964ms | 2167ms | OK. |
| Practice | `/practice` | BLOCKED | 192ms | - | - | - | Redirected to `/plan`; direct practice needs usable book/chapter or review context. |
| Practice | `/practice?review=due` | PASS | 663ms | 690ms | 4117ms | 5319ms | Near threshold; multiple aborted TTS cache-only preloads. |
| Practice | `/practice?mode=smart` | BLOCKED | 188ms | - | - | - | Redirected to `/plan` without selection context. |
| Practice | `/practice?mode=listening` | PASS | 190ms | 390ms | 894ms | 2096ms | OK. |
| Practice | `/practice?mode=meaning` | BLOCKED | 187ms | - | - | - | Redirected to `/plan` without selection context. |
| Practice | `/practice?mode=dictation` | BLOCKED | 188ms | - | - | - | Redirected to `/plan` without selection context. |
| Practice | `/practice?mode=radio` | BLOCKED | 166ms | - | - | - | Redirected to `/plan` without selection context. |
| Practice | `/practice?mode=quickmemory` | BLOCKED | 190ms | - | - | - | Redirected to `/plan` without selection context. |
| Practice | `/practice?mode=errors` | PASS | 333ms | 341ms | 3869ms | 5071ms | Near threshold; aborted TTS cache-only preloads. |
| Practice | `/practice/confusable?book=ielts_confusable_match&chapter=1` | PASS | 227ms | 229ms | 836ms | 2038ms | OK. |
| Game | `/game` | FAIL | - | - | - | - | Stayed on `加载中...` beyond `13s`. |
| Game | `/game/themes` | FAIL | 145ms | - | - | - | Stayed on `正在载入主题地图...` beyond `9s`. |
| Game | `/game/themes/study-campus` | PASS | 192ms | 195ms | 700ms | 1900ms | Explicit themed map is OK. |
| Game | `/game/mission` | NEEDS SELECTOR | 444ms | - | - | - | Mission content was visible; harness keyword expected `提交/跳过` but UI showed `检查`. |
| Game | `/game/themes/study-campus/mission` | NEEDS SELECTOR | 204ms | - | - | - | Mission content was visible; same selector mismatch as above. |
| Exams | `/exams` | PASS | 163ms | 164ms | 1072ms | 2274ms | Empty-state list loaded. |
| Exams | `/exams/1?section=reading` | DATA MISSING | 170ms | - | - | - | `GET /api/exams/1` returned 404; page showed `试卷加载失败 Exam paper not found`. |
| Errors | `/errors` | PASS | 154ms | 160ms | 1071ms | 2273ms | OK. |
| Stats | `/stats` | PASS | 150ms | 156ms | 1368ms | 2569ms | OK. |
| Profile | `/profile` | PASS | 181ms | 183ms | 689ms | 1890ms | OK. |
| Vocab test | `/vocab-test` | PASS | 164ms | 165ms | 4401ms | 5603ms | Close to threshold; book-word fetch dominated. |
| Admin | `/admin` | PASS | 155ms | 162ms | 867ms | 2068ms | OK. |
| Journal | `/journal` | PASS | 154ms | 158ms | 1066ms | 2268ms | OK. |

## Dialog And Popup Timing

| Surface | Route | Result | Open time | API settle | Notes |
| --- | --- | --- | ---: | ---: | --- |
| Header settings | `/plan` | PASS | 81ms | 787ms | Fast. |
| Header help | `/plan` | PASS | 85ms | 791ms | Fast. |
| AI assistant | `/plan` | PASS | 379ms | 5420ms | Panel opens quickly, but context/API settle is close to threshold. |
| Avatar menu | `/plan` | PASS | 371ms | 1377ms | OK. |
| Book chapter modal | `/books` | PASS | 160ms | 767ms | OK. |
| Practice word list | `/practice` | PASS | 257ms | 1063ms | OK after practice shell is available. |
| Practice settings | `/practice` | PASS | 84ms | 890ms | Fast. |
| Confusable help/popover | `/practice/confusable?...` | PASS | 52ms | 556ms | Fast. |
| Errors save-to-custom-book modal | `/errors` | PASS | 39ms | 643ms | Fast after selecting one wrong word. |
| Profile Bug feedback | `/profile` | PASS | 67ms | 874ms | Fast; no `feature-wishes` 500 in this run. |
| Global search | `/plan` | HEADLESS FAIL / MANUAL PASS | - | - | Headless harness timed out, but Computer Use opened the overlay immediately and searching `quit` rendered word detail normally. |
| Practice pronunciation | `/practice` | NOT FOUND | - | - | The expected `发音练习/跟读` button was not visible on the tested practice shell. |
| Confusable custom groups | `/practice/confusable?...` | SKIPPED | - | - | Custom import trigger was not visible in this chapter state. |
| Admin users tab | `/admin` | SELECTOR FAIL | - | - | Dashboard content already showed `用户管理 2`; harness role selector did not find a clickable tab button. |
| Admin feedback tab | `/admin` | SELECTOR FAIL | - | - | Dashboard content already showed `问题反馈`; harness role selector did not find a clickable tab button. |

## Slow/Failure Causes

- External font dependency: `index.html` loads Google Fonts from `fonts.googleapis.com`. In a local/offline/unstable proxy context this can block first paint. Control run: normal cold login first visible `3651ms`; aborting Google Fonts produced first visible `143ms`.
- Game bootstrap: default `/game` and theme picker `/game/themes` stay in loading copy, while explicit `/game/themes/study-campus` is fast. This points to default theme/state discovery rather than rendering cost.
- Practice direct-link semantics: many `/practice?mode=...` links redirect to `/plan` unless a book/chapter/review context is present. That is not a render crash, but it makes direct deep links feel broken.
- TTS preloading: due review/errors/vocab-test generated repeated aborted `cache_only=1` TTS requests. They did not crash the page, but they add noise and correlate with pages close to the `6s` interactive threshold.
- Missing local exam fixture: `/exams/1` returned `404`; list empty-state loaded correctly.
- Screenshot capture: Playwright screenshot capture timed out while waiting for web fonts, so the reliable persisted evidence for this run is the JSON timing output plus Computer Use visual confirmation.

## Recommended Fix Order

1. Self-host the Inter / Noto Sans SC font files or add a local-first fallback with `font-display: swap`; do not let Google Fonts block first paint in local or production-like builds.
2. Debug `/game` and `/game/themes` bootstrap separately from the explicit theme route, using `/game/themes/study-campus` as the known-good control.
3. Decide whether bare `/practice?mode=...` should load a default current book/chapter or show an explicit lightweight selection screen instead of redirecting to `/plan`.
4. Defer or dedupe `cache_only=1` TTS preloads on review-heavy pages so initial interactivity is not delayed by audio cache probes.
5. Seed one local exam paper before the next performance sweep if `/exams/:paperId` detail timing should be measured.
6. Add stable test ids or accessible names for admin tab buttons, global search result state, and game mission action buttons so future timing harnesses can distinguish real loading failures from selector misses.

## Side Effects

- Logged into the local app as `admin` in Playwright context.
- Selected one wrong word in `/errors` to open the custom-book export modal; did not submit the export.
- Opened global search in the visible Chrome tab and searched `quit`; no data-changing action was performed.
- No production or remote environment was touched.
