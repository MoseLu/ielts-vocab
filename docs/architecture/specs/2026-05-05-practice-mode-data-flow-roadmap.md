# Practice Mode Data Flow Roadmap

Last updated: 2026-05-05

## Purpose

This report explains how the current learning center, practice modes, review modes, game mode, and statistics surfaces exchange data. It is written as a roadmap: first describe the current system, then call out confusing boundaries, then list follow-up work that would make the model easier to maintain.

## Executive Summary

The product currently has five overlapping data planes:

1. Catalog plane: words, books, chapters, confusable groups, and media metadata. Frontend reads this through `/api/books/*`, `/api/books/word-list`, and legacy `/api/vocabulary/day/*`. In split runtime these are routed through the gateway into `catalog-content-service` and `learning-core-service`.
2. Practice runtime plane: the browser builds a queue, renders the selected mode, records local interaction state, and chooses which backend writes to perform.
3. Progress plane: book/chapter/day progress and chapter mode progress. This is the resume and completion surface used by study center cards, chapter modal, and stats fallback.
4. Mastery and review plane: quick memory records, wrong words, smart stats, and word mastery attempts. This is the source for due review, error review, five-dimension weakness, and game campaign state.
5. Analytics and recommendation plane: study sessions, learning events, rollups, learner profile, home todos, and downstream projections used by AI, notes, and admin surfaces.

The most important mental model: normal practice modes are answer-centric; radio is session-centric; quickmemory owns its own Ebbinghaus record flow; errors is an overlay that reuses practice layouts but reads and writes wrong-word dimensions; game mode uses word mastery and campaign state instead of the generic progress queue.

## Runtime Topology

Local split runtime:

```text
Browser UI :3002
  -> gateway-bff :8000
    -> catalog-content-service :8101
    -> learning-core-service :8102
    -> ai-execution-service :8104
    -> notes/admin/tts/asr services as needed
Speech Socket.IO :5001
```

Production runtime follows the same logical route behind nginx and the active slot:

```text
axiomaticworld.com
  -> nginx
    -> gateway-bff active slot
      -> same-slot microservices
  -> /socket.io directly to ASR Socket.IO :5001
```

For practice data, `learning-core-service` is the authoritative write owner for progress, sessions, quick memory, smart stats, word mastery, wrong-word facts, and learning activity signals. `ai-execution-service` mostly exposes AI-facing routes and delegates learning writes/reads back to learning-core through internal clients, with legacy fallback only where explicitly allowed.

## Entry Points

| Surface | Route | Main frontend owner | Data meaning |
| --- | --- | --- | --- |
| Study center | `/plan` | `useHomePage` | Aggregates books, progress, learning stats, learner profile, and home todos. |
| Normal practice | `/practice?book=&chapter=&mode=` | `PracticePage` | Generic practice shell for smart/listening/meaning/dictation/follow/radio/quickmemory. |
| Due review | `/practice?review=due` | `PracticePage` + `QuickMemoryMode` | Quick memory due queue, no chapter-progress write in review mode. |
| Error review | `/practice?mode=errors` | `PracticePage` error overlay | Loads wrong words and clears per-dimension pending status. |
| Game campaign | `/game?book=&chapter=&task=&dimension=` | `GameCampaignPage` / `GameMode` | Five-dimension campaign driven by word mastery state. |
| Confusable match | `/practice/confusable?book=&chapter=` | `ConfusableMatchPage` | Matching game for `practice_mode=match` books. |
| Wrong-word management | `/errors` | errors page | Filters and launches error review; not itself the practice runtime. |

Study center starts work in two ways:

1. Book cards call `buildBookStudyEntryPath`. Normal books go to `/practice`, game entry goes to `/game`, and `practice_mode=match` books go to `/practice/confusable`.
2. Home todo tasks choose their route by task type. `due-review` routes to `/practice?review=due`; other learning tasks route to `/game?task=...` with optional dimension and scope.

## Mode Registry

There are two practical registries today:

- `frontend/src/constants/practiceModes.ts` is the broad product registry. It includes `errors`, game dimensions, wrong-word dimension mappings, and mode aliases.
- `frontend/src/components/practice/types.ts` defines `PracticeMode` for the generic `PracticePage` shell. It intentionally excludes `errors` because error review is represented by `mode=errors` query state plus a requested practice layout.

| Mode | User intent | Primary dimension | Queue source | Primary writes |
| --- | --- | --- | --- | --- |
| `smart` | Adaptive mixed practice | listening/meaning/dictation, chosen per word | Canonical word list, smart queue | progress, session, smart stats, word mastery, wrong words on failure |
| `listening` | Hear word and choose meaning | listening | Canonical word list filtered to words with confusables | progress, session, word mastery, wrong words on failure |
| `meaning` | Recall meaning | meaning | Canonical word list | progress, session, word mastery, wrong words on failure |
| `dictation` | Spell from audio | dictation | Canonical word list | progress, session, word mastery, wrong words on failure |
| `follow` | Follow-read pronunciation | speaking | Canonical word list | progress, session, word mastery, wrong words on failure |
| `radio` | Passive listening loop | none by default | Canonical word list | session and resume progress; optional favorite/speaking side actions |
| `quickmemory` | Recognition/Ebbinghaus memory | recognition | Canonical word list or due review queue | quick memory records, session, progress only outside due review, wrong words on unknown |
| `errors` | Clear pending wrong dimensions | selected wrong-word dimension | wrong-word store | wrong-word dimension updates, word mastery attempts, session, local error progress |
| `game` | Five-dimension campaign | recognition/meaning/listening/dictation/speaking | game state from learning-core | word mastery, game wrong-word projection, game attempt metadata |
| `match` | Confusable matching | custom `match` mode | chapter words grouped by confusable set | chapter progress and chapter mode progress |

## Generic Practice Load Flow

The generic `/practice` page has three phases.

### 1. Resolve Context

`PracticePage` reads route query state:

- `book` and `chapter` select a canonical book/chapter scope.
- `mode=errors` activates error review.
- `review=due` forces `quickmemory` review mode.
- Missing mode defaults to `smart` unless review mode overrides it.

### 2. Load Data

`usePracticePageData` chooses one of the following loaders:

1. Due review: `loadQuickMemoryReviewQueue` calls `/api/ai/quick-memory/review-queue` and returns due quick-memory words.
2. Error review: `loadErrorModeData` merges local wrong words with `/api/ai/wrong-words`, applies dimension/date/wrong-count filters, and builds the review queue.
3. Book + chapter: fetch chapter list, canonical word list via `/api/books/word-list?scope=book&book_id=...&chapter_id=...`, then load chapter progress from `/api/books/{book}/chapters/progress`.
4. Book only: fetch canonical book word list and load `/api/books/progress/{book}`.
5. Legacy day: fetch `/api/vocabulary/day/{day}` and `/api/progress?day={day}`.

After loading, `applyScopedWordsLoad` restores `queue_words` from progress when available. If no resume queue exists, it builds a new mode-specific queue. `smart` uses smart stats to prioritize weaker words; listening filters to words with enough confusables; chapter mode can slice into review windows.

### 3. Render Mode

`PracticePageContent` selects the mode component:

- `radio` renders `RadioMode`.
- `quickmemory` renders `QuickMemoryMode`.
- `follow` renders follow-read controls.
- `dictation` renders dictation input.
- `smart`, `listening`, and `meaning` use the options/meaning recall layout family.

Favorite and speaking side actions are attached at the page level so most modes can reuse them without owning that data flow.

## Generic Answer Commit Flow

Most answer-centric modes converge through `commitAnswerResult`.

```text
User answers
  -> prepare or recover study session
  -> update local counters and word status
  -> save progress snapshot
  -> submit word mastery attempt
  -> record smart stats when applicable
  -> save wrong word on failure
  -> record error-review outcome when in error overlay
  -> update local mode performance
```

The dimension is resolved by mode:

- `quickmemory` -> `recognition`
- `listening` -> `listening`
- `meaning` -> `meaning`
- `dictation` -> `dictation`
- `follow` -> `speaking`
- `smart` -> current smart dimension for that word

Wrong answers usually remain on the same word until the user corrects or retries. This means wrong-word and mastery writes can happen before progress moves to the next queue index.

## Progress Flow

`saveProgress` branches by scope:

| Scope | Local key | Backend route | Notes |
| --- | --- | --- | --- |
| Error review | `wrong_words_progress:user:<id>` | no generic progress write | Local-only resume for the current wrong-word review queue. |
| Book | `book_progress` | `POST /api/books/progress` | Stores current index, correct/wrong counts, completion, answered/queue words. |
| Chapter | `chapter_progress` | `POST /api/books/{book}/chapters/{chapter}/progress` | Stores chapter snapshot and queue resume data. |
| Chapter mode | `chapter_mode_progress` indirectly | `POST /api/books/{book}/chapters/{chapter}/mode-progress` | Per-mode accuracy/completion, separate from chapter resume snapshot. |
| Legacy day | `day_progress` | `POST /api/progress` | Compatibility path for day-based vocabulary. |

Backend progress saving is monotonic for important counters such as current index and words learned. It also records learning events and learning activity rollups so stats and todo signals can read a stable aggregate rather than raw local browser state.

## Session Flow

Study sessions are separate from progress. A session answers: "what did the learner actively do today, for how long, in which mode?"

Generic modes use `usePracticePageSession` and `AIChat` session helpers:

1. Start or recover a session with `/api/ai/start-session`.
2. Keep an `active_study_session` snapshot in localStorage for refresh/pagehide recovery.
3. On each learning action, update unique words, correct/wrong counts, active timestamp, and session snapshot.
4. On mode change, idle segmentation, unmount, or pagehide, finalize through `/api/ai/log-session` or cancel passive placeholders.

Special cases:

- `quickmemory` bypasses the generic page session manager and uses its own quick-memory session hook.
- `radio` tracks words studied by current radio index, not unique answered words.
- `follow` has extra interaction marking so passive page visits do not become meaningful study sessions.

Backend `persist_study_session` writes `UserStudySession`, records a `study_session` learning event, updates learning activity rollups, and queues a study-session domain event for downstream consumers.

## Quick Memory Flow

Quick memory is the most independent mode.

Normal chapter quickmemory:

1. Loads canonical chapter/book words.
2. `QuickMemoryMode` records `known` or `unknown` through `updateQuickMemoryRecord`.
3. Local records are stored in user-scoped `quick_memory_records`.
4. `quickMemorySync` posts `/api/ai/quick-memory/sync`.
5. Unknown words call the wrong-word path for recognition failure.
6. Non-review chapter quickmemory also writes chapter progress and mode progress.

Due review quickmemory:

1. `/api/ai/quick-memory/review-queue` returns due words based on `nextReview`.
2. The review result updates quick-memory records and recognition mastery.
3. It does not write chapter progress, because the scope is "due review" rather than "advance this chapter".
4. Learning stats and learner profile reconcile quick-memory records before fetching stats so recent local records are not missed.

Backend quick-memory sync updates `UserQuickMemoryRecord`, records `quick_memory_review` events when source is provided, updates recognition word mastery, and ensures wrong-word recognition failure for unknown answers.

## Smart Mode Flow

Smart mode has two responsibilities:

1. Queue selection: `buildSmartQueue` prioritizes unseen or weak words based on local/server smart stats.
2. Dimension selection: `chooseSmartDimension` picks the weakest of listening, meaning, and dictation for the current word.

On answer:

- The generic answer flow records progress, session, word mastery, and wrong words.
- `recordWordResult` updates local `smart_word_stats`.
- `syncSmartStatsToBackend` uploads deltas to `/api/ai/smart-stats/sync`, often on session close or retry intervals.

Backend smart-stat sync writes per-word dimension counters and emits dimension events such as `listening_review`, `meaning_review`, and `writing_review`. This makes smart mode feed the same dimension analytics as explicit listening/meaning/dictation practice.

## Error Review Flow

Error review is not a standalone `PracticeMode` type. It is an overlay:

1. `/errors` lets the user filter pending/history wrong words.
2. The user enters `/practice?mode=errors` with optional dimension/filter query.
3. `loadErrorModeData` loads local plus remote wrong words, filters to pending target dimensions, and maps each wrong word back into a practice word.
4. The selected layout is based on wrong-word dimension: recognition uses quickmemory-like recognition, meaning uses meaning recall, listening uses listening, speaking uses follow, dictation uses dictation.
5. Passing or failing updates the wrong-word dimension state and syncs `/api/ai/wrong-words/sync`.
6. A word can leave the pending queue only when the target dimension reaches its pass rule.

Error review writes local `wrong_words_progress` for resume, but it does not write normal book/chapter progress. It still records mastery attempts and sessions, because it is real learning activity.

## Game Campaign Flow

Game mode is a separate campaign engine, not the generic queue.

Frontend:

1. Reads `/api/ai/practice/game/state` for nodes, segments, boosts, failed dimensions, and campaign progress.
2. Starts a campaign session with `/api/ai/practice/game/session/start`.
3. Submits each word or speaking node to `/api/ai/practice/game/attempt`.

Dimension mapping:

- `definition` -> `meaning`
- `spelling` -> `dictation`
- `example` -> `listening`
- `speaking` word nodes -> `recognition`
- speaking boss/reward nodes -> `speaking`

Backend:

1. `ai-execution-service` accepts browser API traffic.
2. It delegates game state and attempts to `learning-core-service`.
3. Learning-core updates `UserWordMasteryState`, records practice attempt facts, syncs game wrong-word projection, and returns rebuilt game state.

This means game progress is primarily word-mastery progress, not chapter resume progress.

## Confusable Match Flow

Confusable match is selected by book metadata `practice_mode=match`.

1. `buildBookPracticePath` routes the book to `/practice/confusable`.
2. The page loads chapters from `/api/books/{book}/chapters`, words from `/api/books/{book}/chapters/{chapter}`, and previous chapter progress from `/api/books/{book}/chapters/progress`.
3. The browser groups words into match groups and stores a snapshot with answered word keys, counts, and round group keys.
4. Progress is persisted both locally and remotely:
   - `POST /api/books/{book}/chapters/{chapter}/progress` with `mode=match`
   - `POST /api/books/{book}/chapters/{chapter}/mode-progress` with `mode=match`

It does not currently go through the generic word mastery attempt flow. Its outcome is chapter/mode progress rather than per-dimension mastery.

## Statistics and Recommendation Flow

Study center and stats are read-model surfaces. They should not be treated as the source of truth.

Frontend reads:

- `/api/ai/learning-stats` through `useLearningStats`
- `/api/ai/learner-profile` for profile, memory system, due review count, focus words, daily plan
- `/api/ai/home-todos` for ranked daily tasks
- `/api/books/progress/*` and `/api/books/{book}/chapters/progress` for book/chapter cards

Backend builds:

1. Learning stats from reportable `UserStudySession` rows, live pending session snapshots, chapter progress fallback, quick-memory summaries, wrong-word lists, chapter breakdowns, and word mastery summary.
2. Learner profile from sessions, smart stats, wrong words, quick memory records, notes, learning events, and activity timeline.
3. Home todos from learning-core signals: due review count, pending wrong words, focus book progress, activity today, weakest mode, and speaking activity.

Home todo ranking is fixed by priority: due review, error review, continue/add book, then speaking. The study center book card list is separate and currently sorted by completion percentage descending.

## Local Storage Compatibility

The app still has local storage in two roles:

1. Active runtime cache: resume queues, active session snapshot, quick-memory pending sync, wrong-word local mirror, and current UI selections.
2. Legacy migration input: older anonymous/local learning data that is uploaded once after login.

Important keys:

- `book_progress`
- `chapter_progress`
- `day_progress`
- `wrong_words:user:<id>`
- `wrong_words_progress:user:<id>`
- `quick_memory_records:user:<id>`
- `quick_memory_records:user:<id>:pending_sync`
- `smart_word_stats`
- `smart_word_stats_pending`
- `active_study_session`

The one-shot migration route `/api/ai/local-storage-migration` processes smart stats, quick-memory records, wrong words, chapter progress, book progress, and day progress through existing write paths. After successful migration, legacy local keys should stop being treated as the source of truth.

## Backend Write Ownership

| Data | Primary owner | Typical route |
| --- | --- | --- |
| Catalog words/books/chapters | catalog-content / learning-core read model | `/api/books/*`, `/api/books/word-list` |
| Book/chapter/day progress | learning-core | `/api/books/progress`, `/api/books/{book}/chapters/{chapter}/progress`, `/api/progress` |
| Chapter mode progress | learning-core | `/api/books/{book}/chapters/{chapter}/mode-progress` |
| Study sessions | learning-core through AI routes | `/api/ai/start-session`, `/api/ai/log-session`, `/api/ai/cancel-session` |
| Quick memory records | learning-core through AI routes | `/api/ai/quick-memory`, `/api/ai/quick-memory/sync`, `/api/ai/quick-memory/review-queue` |
| Smart stats | learning-core through AI routes | `/api/ai/smart-stats`, `/api/ai/smart-stats/sync` |
| Wrong words | learning-core through AI routes | `/api/ai/wrong-words`, `/api/ai/wrong-words/sync` |
| Word mastery/game attempts | learning-core through AI routes | `/api/ai/practice/game/*` and mastery attempt helpers |
| Stats/profile/todos | learning-core signals + ai-execution read assembly | `/api/ai/learning-stats`, `/api/ai/learner-profile`, `/api/ai/home-todos` |

## Current Confusing Boundaries

1. `errors` appears in the canonical mode list but is not a `PracticeMode` type. This is correct today, but it is easy to misread.
2. `quickmemory` sometimes means "chapter recognition practice" and sometimes means "due review". These have different progress writes.
3. `radio` looks like a practice mode but is not answer-centric. It mainly affects session duration and words-studied counts.
4. Chapter progress and chapter mode progress are separate writes. A mode can show accuracy even if resume snapshot semantics differ.
5. Smart stats are local-first and sync later, so immediate weakness calculations can differ between local page state and backend stats until reconciliation.
6. Game mode and generic practice both update mastery-like facts, but game does not use the generic `PracticePage` progress queue.
7. Confusable match writes `mode=match` progress but does not currently emit per-word mastery attempts.
8. Stats has a fallback path from chapter progress when session data is absent. This is useful for compatibility but can hide missing session writes.
9. AI routes often proxy to learning-core internally. When debugging, do not assume an `/api/ai/*` route means AI owns the underlying learning data.

## Roadmap

### Phase 1: Make the Mode Contract Explicit

- Add a single documented mode matrix in code or generated docs that distinguishes `practice mode`, `review overlay`, `game task`, and `book practice_mode`.
- Add a type-level guard for mode aliases and wrong-word dimension mappings.
- Add a smoke test that every visible study-center entry route lands on the intended runtime: practice, game, confusable, or errors.

### Phase 2: Normalize Result Writes

- Introduce a small frontend write contract such as `PracticeResultSink` for answer-centric modes.
- Keep quickmemory, game, and match as explicit adapters rather than forcing them into the generic path.
- Make each adapter declare which planes it writes: progress, session, mastery, wrong words, smart stats, quick memory, or game state.

### Phase 3: Clarify Progress vs Session Semantics

- Document when a mode advances book/chapter progress and when it only creates learning activity.
- Add tests for the special cases: due review no chapter progress, errors local error progress only, radio session words-studied, match mode progress.
- Add a backend consistency check that chapter mode progress does not drift unexpectedly from chapter progress for modes where both are expected.

### Phase 4: Improve Observability

- Add a per-attempt debug trace id from frontend answer commit through backend learning event, word mastery, wrong-word sync, and session update.
- Add a developer-only route or script that shows "what changed" after one practice answer.
- Add compact e2e coverage for one correct and one wrong answer in smart, listening, meaning, dictation, follow, quickmemory, errors, game, and match.

### Phase 5: Retire Legacy Ambiguity

- Keep the one-shot localStorage migration path, but make post-migration source-of-truth rules visible in docs and tests.
- Prefer learning-core internal reads for stats/profile/todos and keep AI local fallbacks strict in split runtime.
- Continue moving downstream needs into service-owned projections rather than shared-table fallback reads.

## Verification Checklist For Future Mode Changes

For any mode change, verify these questions:

1. What route starts the mode?
2. What queue source does it use?
3. Which dimension does a correct/wrong answer affect?
4. Does it write book/chapter/day progress?
5. Does it write chapter mode progress?
6. Does it write quick-memory records?
7. Does it write wrong words?
8. Does it submit word mastery attempts?
9. Does it start/finalize a study session?
10. Does it affect learner profile, home todos, or learning stats immediately, or only after sync/reconciliation?
11. Does reload resume from backend, localStorage, or both?
12. Does pagehide/offline handling preserve the most important write?

## Source Map

Frontend:

- `frontend/src/constants/practiceModes.ts`
- `frontend/src/components/practice/PracticePage.tsx`
- `frontend/src/components/practice/page/PracticePageContent.tsx`
- `frontend/src/composables/practice/page/usePracticePageData.ts`
- `frontend/src/composables/practice/page/usePracticePageActions.ts`
- `frontend/src/composables/practice/page/usePracticePageControls.ts`
- `frontend/src/composables/practice/page/usePracticePageSession.ts`
- `frontend/src/components/practice/QuickMemoryMode.tsx`
- `frontend/src/lib/quickMemory.ts`
- `frontend/src/lib/quickMemorySync.ts`
- `frontend/src/lib/smartMode.ts`
- `frontend/src/features/vocabulary/wrongWordsStore/*`
- `frontend/src/components/practice/page/GameMode.tsx`
- `frontend/src/composables/practice/confusable/useConfusableMatchPage.ts`
- `frontend/src/components/practice/confusable/confusableMatchPageData.ts`
- `frontend/src/composables/home/page/useHomePage.ts`
- `frontend/src/features/vocabulary/hooks/useLearningStats.ts`
- `frontend/src/features/home/hooks/useHomeTodos.ts`

Backend and platform SDK:

- `packages/platform-sdk/platform_sdk/gateway_browser_routes.py`
- `packages/platform-sdk/platform_sdk/ai_progress_sync_application.py`
- `packages/platform-sdk/platform_sdk/ai_learning_stats_application.py`
- `packages/platform-sdk/platform_sdk/ai_context_application.py`
- `packages/platform-sdk/platform_sdk/ai_home_todo_application.py`
- `packages/platform-sdk/platform_sdk/learning_core_home_todo_signals_application.py`
- `packages/platform-sdk/platform_sdk/learning_core_word_mastery_application.py`
- `packages/platform-sdk/platform_sdk/learning_stats_payload_support.py`
- `backend/services/books_progress_service.py`
- `backend/services/ai_progress_sync_service.py`
- `backend/services/session_logging_service.py`
- `backend/services/word_mastery_service.py`
- `backend/services/learning_attempt_service.py`
- `backend/services/learner_profile_service/profile_builder.py`
