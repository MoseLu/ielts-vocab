# Mobile Upgrade Plan With E2E

Date: 2026-06-01

## Executive Summary

This plan turns the mobile-Web parity assessment into an execution roadmap. The mobile app remains a native React Native client. Web stays the parity baseline, while `packages/app-core` becomes the shared home for contracts and pure learning logic.

The upgrade is full-scope across P0/P1/P2, but the delivery order is fixed:

1. Establish Maestro E2E gates and stable native selectors.
2. Close P0 core learning-loop gaps.
3. Close P1 learner-facing product gaps.
4. Close P2 advanced and operational gaps while keeping admin Web-first.

## Phase 0: E2E Foundation

Goal: make every future parity issue prove itself on Android before it is called done.

Main file areas:

- `apps/mobile/e2e/maestro`
- `apps/mobile/scripts/run-maestro-e2e.sh`
- `apps/mobile/src/navigation/RootNavigator.tsx`
- key learner screens and shared primitive controls

Acceptance:

- `pnpm mobile:e2e:smoke` launches the debug app on AVD `ielts_vocab_api35`, logs in with `admin` / `admin123456`, and verifies the learner tabs.
- `pnpm mobile:e2e:android` runs the first parity smoke set: login, books, practice, wrong-word recovery, search route/input, stats, AI entry, journal, exams, and feedback entry.
- Critical navigation and form controls expose stable `testID` or `accessibilityLabel` selectors.

Suggested tests:

- `pnpm mobile:test`
- `pnpm mobile:typecheck`
- `pnpm check:file-lines`
- `pnpm mobile:e2e:smoke` when Maestro and the local split runtime are installed.

## P0: Core Learning Loop

Goal: mobile can support real daily learning without depending on Web fallback.

Issue slices:

1. Practice contract parity
   - Areas: `PracticeScreen`, `packages/app-core/src/practiceEngine.ts`, mobile practice tests.
   - Dependencies: Web mode semantics, wrong-word dimensions, quickmemory sync endpoints.
   - Acceptance: `smart`, `quickmemory`, `listening`, `meaning`, `dictation`, `follow`, `radio`, and `errors` preserve answer evaluation, progress, wrong-word writes, audio/follow handling, completion, and resume.
   - E2E: `book-chapter-practice`, `quickmemory-sync-restart`, `wrong-word-recovery`.

2. Ebbinghaus and wrong-word reliability
   - Areas: quickmemory sync, wrong-word queue loading, pending sync storage.
   - Dependencies: `/api/ai/quick-memory`, `/api/ai/quick-memory/sync`, `/api/ai/wrong-words`.
   - Acceptance: due review and wrong-word entries retain scoped context, failed syncs retry, and completed wrong-word chapters do not regress after restart.
   - E2E: restart after quickmemory submit and verify visible progress.

3. Books, custom books, favorite/familiar basics
   - Areas: `BooksScreen`, `CustomBookScreen`, `SearchScreen`, `learnerApi`.
   - Dependencies: my-books add/remove, custom-book update, favorite/familiar status APIs.
   - Acceptance: users can add/remove books, inspect chapter progress, edit custom books, and toggle favorite/familiar with rollback.
   - E2E: book list, chapter entry, word detail, favorite/familiar toggle.

4. Auth and sync hardening
   - Areas: `SessionContext`, `sessionHydration`, `mobileStorage`, app-core API/storage contracts.
   - Dependencies: mobile auth endpoints and AsyncStorage.
   - Acceptance: cached users survive temporary `/me` failure, refresh is concurrency-safe, and pending practice writes replay.
   - E2E: login, restart, temporary network failure recovery.

## P1: Learner-Facing Product Parity

Goal: all high-value learner-facing Web routes have native mobile outcomes.

Issue slices:

1. Native global chrome
   - Areas: `RootNavigator`, header actions, feedback/search/AI screens.
   - Acceptance: search, AI, feedback, and back behavior work from all learner screens without overlay collision.
   - E2E: global search route/input smoke, then full word-detail coverage once the local search API is responsive.

2. Structured word detail and notes
   - Areas: `SearchScreen`, app-core word schemas.
   - Acceptance: mobile renders meaning groups, examples, notes, favorite/familiar, and practice actions without raw JSON output.
   - E2E: search a known word, open details, save note.

3. AI assistant command parity
   - Areas: `AIChatScreen`, shared AI command adapters.
   - Acceptance: core Web AI commands return native result cards with session logging and graceful unavailable states.
   - E2E: ask study-plan question and verify answer state.

4. Exams, journal, and stats parity
   - Areas: `ExamsScreen`, `JournalScreen`, `StatsScreen`.
   - Acceptance: attempts autosave/resume, summaries render safely, and stats show learner-profile decisions plus mode/chapter/wrong-word slices.
   - E2E: open exam, journal, and stats route smoke.

5. Confusable and vocab-test
   - Areas: new native entries or integrated practice routes.
   - Acceptance: users can complete the same learner outcomes as Web confusable match and vocab-test.
   - E2E: route start, one answer interaction, completion state.

## P2: Advanced and Operational Parity

Goal: advanced learning and mobile observability exist without making admin a mobile blocker.

Issue slices:

1. Game and AI speaking native path
   - Areas: game/speaking screens and app-core game API adapters.
   - Acceptance: mobile can view themes, start/resume sessions, submit attempts, and show progress or an explicit deferred state.
   - E2E: advanced entry route and speech lifecycle smoke.

2. Feedback attachments and sanitized error reporting
   - Areas: feedback screen, mobile API client, redaction helpers.
   - Acceptance: feedback can attach screenshot/device context; network/render errors are deduped and redacted.
   - E2E: feedback form entry plus unit tests for redaction.

3. Admin remains Web-first
   - Areas: documentation only unless a mobile operator need is approved.
   - Acceptance: admin parity stays `defer` and does not block learner releases.

## Verification Gates

Baseline for every phase:

- `pnpm mobile:typecheck`
- `pnpm mobile:test`
- `pnpm app-core:test`

Shared-core changes also require:

- `pnpm app-core:typecheck`
- targeted frontend tests for any shared contract consumed by Web

Release candidate:

- `pnpm verify:clients`
- `pnpm mobile:e2e:android`
- Android emulator screenshot review
- `adb logcat` crash scan for app startup, navigation, speech lifecycle, and auth recovery

## Assumptions

- Maestro is the mobile E2E stack.
- Android AVD `ielts_vocab_api35` is the primary local device.
- Local split runtime uses API `8000`, speech Socket.IO `5001`, and Metro `8081`.
- The first E2E suite uses the local `admin` test account and does not call production.
- Admin/dashboard remains Web-first unless the product explicitly asks for mobile operator workflows.
- Current Phase 0 E2E intentionally avoids asserting AI answer content and search result content because those depend on backend/external service responsiveness; P1 must add content-level coverage after those APIs are stable under the local split runtime.
