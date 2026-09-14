# Mobile-Web Alignment Assessment

Date: 2026-06-01

## Executive Summary

The mobile app is a real React Native client, not a WebView. It already covers login, a learner home, books, chapter practice, wrong words, stats, exams, journal, AI chat, search, profile/settings, and native speech capture. The gap is that Web has become the product source of truth for route coverage, global chrome, practice depth, AI commands, game/speaking flows, reporting, admin, and test maturity, while Mobile only implements the thinnest end-to-end version of several of those areas.

Status vocabulary used below:

- `aligned`: Mobile covers the same user outcome with native interaction.
- `partial`: Mobile covers a smaller or less reliable version of the Web outcome.
- `missing`: Mobile has no meaningful equivalent.
- `mobile-specific`: Mobile intentionally differs because native behavior is needed.
- `defer`: Do not build for Mobile until product need is explicit.

Priority vocabulary:

- `P0`: core learning loop needed before calling Mobile caught up.
- `P1`: high-value parity after the core loop is stable.
- `P2`: advanced, operational, or admin parity.

## Feature Parity Matrix

| Area | Web baseline | Mobile state | Status | Priority | Acceptance target |
| --- | --- | --- | --- | --- | --- |
| Auth/session | Cookie auth, refresh recovery, cached user hydration, email bind/reset, terms routes. | Mobile token auth, WeChat login path, cached user hydration, register/reset/bind surfaces. | partial | P0 | Mobile keeps cached users through temporary `/me` failure, supports login/register/reset/bind/logout, and shows clear auth expiry handling. |
| Home/plan | `/plan` uses todo actions, book state, guided study, and game routing. | Home reads `home-todos` and stats, renders a native study-room scene and maps limited actions. | partial | P0 | Every `home-todos` action maps to a valid native destination or a disabled explained state. |
| Navigation/chrome | Header, sidebar, bottom nav, floating AI panel, global word search, selection lookup, screenshot shortcut. | Native tab shell, header actions for search/AI, no floating AI, no selection lookup, no screenshot shortcut. | partial | P1 | Native shell exposes search, AI, feedback, and route-safe back behavior without overlay collisions. |
| Books/chapters | Book library, my books, progress, chapter modal, mode progress, custom book edit/update. | Book list, my-book add, chapter list/progress, quick start. Custom book create-only from simple text. | partial | P0 | Mobile can browse, add/remove, inspect chapter mode progress, and create/edit custom books without losing Web metadata. |
| Favorite/familiar words | Optimistic status and mutation hooks for favorites/familiar words; detail panels use them. | API helpers exist but UI usage is limited; no status reconciliation flow. | partial | P0 | Word detail and practice cards expose favorite/familiar with optimistic rollback and status preload. |
| Practice modes | Mature smart, quickmemory, listening, meaning, dictation, follow, radio, errors plus resume, audio, examples, mode contracts, result chain. | One native `PracticeScreen` implements simplified evaluation and progress sync for all labels. | partial | P0 | Mobile preserves Web mode semantics for answer evaluation, progress, wrong-word dimensions, quickmemory sync, resume, audio, and completion. |
| Ebbinghaus/wrong-word recovery | Quickmemory reconciliation, scoped records, review queue, wrong-word dimension history and recovery. | Quickmemory sync per word and compact wrong-word queue. No full reconcile/retry or dimension-rich recovery. | partial | P0 | Mobile merges local/remote review evidence, respects scoped queue context, and never hides completed wrong-word chapters. |
| Global search/word detail | Global search panel, detail panel, notes, selected text lookup, favorite/familiar controls. | Dedicated search screen with raw JSON-ish details and note save. | partial | P1 | Native word detail renders structured meaning, examples, notes, favorite/familiar, and practice actions. |
| Stats/profile | Rich stats page with mode filtering, charts, learner profile, game filtering, skeletons. | Summary cards, simple mode chart, profile summary. | partial | P1 | Mobile shows the same learner-profile decisions and key mode/chapter/wrong-word slices in compact native charts. |
| AI assistant | Floating panel, session tracking, greeting, streaming, correction, examples, synonyms, word family, collocations, pronunciation, review plan, vocab assessment, speaking simulate. | Simple AI screen calls `/api/ai/ask`. | partial | P1 | Mobile supports the core AI command set with session logging and native input/voice affordances. |
| Journal/notes | Learning journal, summaries, markdown rendering, jobs, notes history. | Summary list, notes list, generate job. Markdown/detail handling is basic. | partial | P1 | Mobile renders journal markdown safely, shows job state, and links notes to words/practice context. |
| Exams | Library, attempt route, autosave/flush, grouped questions, submit results, listening/audio handling. | Library/detail in one screen, creates attempt, saves/submits basic responses, speech evaluation path. | partial | P1 | Mobile supports attempt persistence, section navigation, autosave, submitted result display, and listening audio. |
| Speech/follow read | Browser fallback, Socket.IO ASR, upload fallback, pronunciation scoring, resource cleanup tests. | Native PCM capture, Socket.IO ASR, speech evaluation for exam speaking. | mobile-specific | P0 | Native speech has lifecycle parity: permission, stale-event protection, stop/commit, transcript fallback, and scoring error states. |
| Confusable match | Dedicated route and tested confusable practice flow. | No native screen. | missing | P1 | Add a compact native confusable practice screen reusing shared data contracts. |
| Vocab test | Dedicated `/vocab-test` page. | No native route. | missing | P1 | Add native vocab-test or intentionally merge it into practice with equivalent outcomes. |
| Game/AI speaking | Game routes, theme assets, game state/session/attempt API, speaking redirected to game. | Practice entry points link to exams/follow; no game route/state. | missing | P2 | Native has a game/speaking landing and can start/resume/submit game attempts or clearly defers paid/2.0 content. |
| Feedback/bug reports | Global screenshot shortcut and profile wishes. | Profile feedback can create/list wishes, no screenshot attachment flow. | partial | P2 | Mobile feedback supports text plus screenshot/log context using native capture/share constraints. |
| Admin | Web admin dashboard for overview, users, assets, word feedback. | No admin route. | defer | P2 | Keep Web-only unless a mobile operator need is approved; do not block learner parity. |
| Error reporting | Web API client reports sanitized frontend errors to ops endpoint. | Mobile API client surfaces errors but has no comparable sanitized reporting pipeline. | missing | P1 | Mobile reports redacted network/render errors with dedupe and opt-in context. |
| Offline/cache/sync | Web has local storage migration, quickmemory pending retry, smart stats pending retry. | AsyncStorage token/user cache only; no general pending sync queue beyond direct API calls. | partial | P0 | Mobile has a shared pending-sync queue for practice, quickmemory, wrong words, and smart stats. |
| Test maturity | Web has broad unit/component coverage across routes, practice, AI, stats, books, errors, speech, admin, and API client. | Mobile has session/sticker tests; app-core covers API/auth/practice/storage/speech basics. | partial | P0 | Every P0 mobile feature has reducer/core tests plus at least one screen-level smoke or integration test. |

## P0/P1/P2 Roadmap

### P0 Core Learning Loop

1. Mobile practice contract parity
   - Goal: make Mobile practice behavior match Web for `smart`, `quickmemory`, `listening`, `meaning`, `dictation`, `follow`, `radio`, and `errors`.
   - Main areas: `apps/mobile/src/screens/PracticeScreen.tsx`, `packages/app-core/src/practiceEngine.ts`, mobile practice tests.
   - Dependencies: Web mode contracts, wrong-word dimensions, quickmemory sync and progress endpoints.
   - Acceptance: answer evaluation, wrong-word creation, progress snapshots, completion, resume, and audio/follow handling match Web-visible outcomes.
   - Suggested tests: app-core mode-contract tests; Mobile tests for each mode's submit/progress/wrong-word side effects.

2. Ebbinghaus and wrong-word recovery reliability
   - Goal: Mobile must not regress scoped review, wrong-word completion, or partial legacy/scoped evidence.
   - Main areas: mobile quickmemory sync, wrong-word queue loading, `app-core` storage/sync helpers.
   - Dependencies: `/api/ai/quick-memory`, `/api/ai/quick-memory/sync`, `/api/ai/wrong-words`, chapter progress APIs.
   - Acceptance: due-review and wrong-word entries load with scoped context; failed syncs retry; completed chapters stay completed after app restart.
   - Suggested tests: pending-sync retry, scoped queue mapping, wrong-word dimension pass/fail persistence.

3. Books, custom books, favorite/familiar basics
   - Goal: Mobile can manage the same learner vocabulary surfaces needed to start and maintain practice.
   - Main areas: `BooksScreen`, `CustomBookScreen`, `SearchScreen`, learner API helpers.
   - Dependencies: my-books add/remove, favorites/familiar status, custom-book create/update contracts.
   - Acceptance: add/remove books, inspect mode progress, edit custom books, and toggle favorite/familiar with rollback on failure.
   - Suggested tests: API helper tests and screen-level tests for optimistic mutation and custom-book edit payloads.

4. Mobile sync and auth hardening
   - Goal: Mobile survives temporary backend failure without losing practice or session state.
   - Main areas: `packages/app-core` storage/API client, `SessionContext`, mobile storage.
   - Dependencies: current mobile token auth endpoints and AsyncStorage.
   - Acceptance: cached session survives temporary `/me` and refresh failures; protected calls refresh tokens; pending practice writes are retained and retried.
   - Suggested tests: token refresh concurrency, temporary-unavailable hydration, pending write replay.

### P1 High-Value Product Parity

1. Native global learning chrome
   - Goal: close the Web chrome gap with native search, AI, feedback, and route actions.
   - Main areas: `RootNavigator`, `SearchScreen`, `AIChatScreen`, `ProfileFeedbackScreen`.
   - Dependencies: word detail, AI command, feedback APIs.
   - Acceptance: global search and AI are reachable from all learner screens; feedback can include useful device/screen context; back behavior is predictable.
   - Suggested tests: navigation reducer tests and screen smoke tests for search/AI entry points.

2. Structured word detail and notes
   - Goal: replace raw detail rendering with Web-equivalent learner actions.
   - Main areas: `SearchScreen`, word detail components, app-core word schemas.
   - Dependencies: `/api/books/search`, `/api/books/word-details`, notes/favorite/familiar APIs.
   - Acceptance: Mobile renders meaning groups, examples, notes, favorite/familiar, and "practice this word" actions.
   - Suggested tests: schema parse tests and detail render tests for missing optional fields.

3. AI assistant command parity
   - Goal: support the high-value Web AI commands in a native Mobile flow.
   - Main areas: `AIChatScreen`, app-core AI command helpers if extracted.
   - Dependencies: `/api/ai/greet`, `/api/ai/correct-text`, `/api/ai/ielts-example`, `/api/ai/synonyms-diff`, `/api/ai/word-family`, `/api/ai/collocations/practice`, `/api/ai/review-plan`, `/api/ai/vocab-assessment`, `/api/ai/pronunciation-check`, `/api/ai/speaking-simulate`.
   - Acceptance: Mobile supports command results, session logging, and graceful unavailable states for voice/audio commands.
   - Suggested tests: command parser/core tests plus screen tests for loading/error/result states.

4. Exams, journal, stats parity pass
   - Goal: make existing Mobile partial screens robust enough for real learner use.
   - Main areas: `ExamsScreen`, `JournalScreen`, `StatsScreen`.
   - Dependencies: exam attempt autosave, notes markdown, learner profile/stat payloads.
   - Acceptance: exam attempts autosave and resume; journal markdown renders safely; stats show profile decisions and mode/chapter/wrong-word slices.
   - Suggested tests: exam response flushing, markdown normalization, stats payload rendering.

5. Confusable and vocab-test native entries
   - Goal: cover the remaining Web learning routes that are not admin/ops.
   - Main areas: new native screens or integrated practice entries.
   - Dependencies: Web confusable data contract and listening-book vocab-test contract.
   - Acceptance: users can launch and complete confusable match and vocab-test outcomes on Mobile.
   - Suggested tests: route/navigation tests and app-core scoring tests.

### P2 Advanced, Operational, and Admin

1. Game and AI speaking native path
   - Goal: add a native landing/resume path for Web game/speaking work without coupling it to foundational practice.
   - Main areas: new game/speaking screens and app-core game API adapters.
   - Dependencies: `/api/ai/practice/game/*`, theme assets, speaking simulation/evaluation endpoints.
   - Acceptance: Mobile can view themes, start/resume sessions, submit attempts, and show progress; if unavailable, it clearly marks advanced mode as deferred.
   - Suggested tests: game API adapter tests and a native landing smoke test.

2. Mobile error reporting and feedback attachments
   - Goal: bring Mobile closer to Web's operational visibility.
   - Main areas: app-core/mobile API client, feedback screen, native screenshot/log capture.
   - Dependencies: `/api/ops/frontend-error-logs`, feature wish APIs, platform permissions.
   - Acceptance: sanitized network/render errors are deduped; feedback can attach screenshot/device context without leaking secrets.
   - Suggested tests: redaction, dedupe, and feedback payload tests.

3. Admin remains Web-first
   - Goal: avoid spending Mobile capacity on low-frequency operator dashboards until there is a clear use case.
   - Main areas: none unless requested.
   - Dependencies: Web admin remains available.
   - Acceptance: admin parity is documented as `defer`; Mobile does not block learner release on admin.
   - Suggested tests: none for Mobile.

## Shared Core/API Gaps

- Move mode semantics out of Web-only practice components and into `packages/app-core`: mode labels, answer evaluation, wrong-word dimension mapping, progress snapshot shape, quickmemory records, and retryable sync payloads.
- Add shared API adapters or schemas for areas currently split by convention: word detail, favorite/familiar status, custom-book update, AI commands, exam attempts, journal summaries, stats/profile slices, and game attempts.
- Normalize Mobile and Web auth differences intentionally: Web stays cookie-based; Mobile stays token-based, but both should share session expiry, temporary failure, and cached-user behavior tests.
- Add a Mobile pending-sync abstraction over AsyncStorage instead of fire-and-forget writes from screens.
- Keep native speech Mobile-specific, but share transcript/session reducer behavior with Web where possible.

## Test & Verification Matrix

| Stage | Required checks | Manual/device checks |
| --- | --- | --- |
| Baseline assessment | `pnpm mobile:typecheck`, `pnpm mobile:test`, `pnpm app-core:test` | Existing emulator launch, login, home, practice start, search, stats, exams, AI, journal smoke. |
| P0 implementation | Above plus new app-core practice/sync tests and Mobile mode tests. | Complete one chapter in quickmemory, listening, dictation, follow, and errors; restart app and confirm progress. |
| P1 implementation | Above plus screen tests for search/AI/exams/journal/stats where feasible. | Native route smoke across all learner tabs; offline/temporary failure retry; exam attempt resume; journal render. |
| P2 implementation | Targeted game/error-reporting/feedback tests. | Game/speaking path on emulator; feedback payload with screenshot/device context; redaction review. |
| Release candidate | `pnpm verify:clients`; targeted frontend tests for shared-core changes; backend tests for touched API contracts. | Android emulator screenshot pass and logcat check for crashes, layout overlap, microphone lifecycle, and auth recovery. |

## Open Risks

- Web practice behavior is broad and heavily tested; porting behavior screen-by-screen without shared core will keep Mobile behind.
- Existing Mobile screens call APIs directly from UI code, which makes pending sync, retries, and parity testing harder than Web's hook/core split.
- Custom-book editing, favorite/familiar status, and word detail are easy to underestimate because API helpers exist but native UX is incomplete.
- Mobile speech must stay native; trying to copy browser fallback logic directly would create false parity.
- Admin parity should remain deferred unless the product explicitly needs operator workflows on mobile.
