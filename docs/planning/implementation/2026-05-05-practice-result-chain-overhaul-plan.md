# Practice Result Chain Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收口当前 practice / review / game / match 链路，让一次学习结果有统一契约、统一追踪、可幂等重放、可恢复同步和可对账的后端落点。

**Architecture:** 采用分阶段收敛：先把 mode contract 变成代码事实，再用前端 `PracticeResultSink` 统一编排现有写入，最后把 answer-centric 写入升级为 `learning-core-service` 的单事务提交端点。保留 quickmemory、game、match 的独立语义，但必须以 adapter 形式声明写入面、幂等键和追踪字段。

**Tech Stack:** React 19 + TypeScript + Vite, Flask/FastAPI split runtime, SQLite/PostgreSQL service models, existing gateway `X-Trace-Id` / `Idempotency-Key`, existing learning-core outbox/domain-event infrastructure.

---

## Current Facts

- Current roadmap: `docs/architecture/specs/2026-05-05-practice-mode-data-flow-roadmap.md` already identifies five data planes and the current confusing boundaries.
- Frontend generic answer writes currently converge at `frontend/src/composables/practice/page/usePracticePageActions.ts`, where `commitAnswerResult` triggers progress, session snapshot, mastery, smart stats, wrong words, error review outcome, and local mode performance separately.
- Study sessions already have local recovery and pagehide flush through `frontend/src/composables/ai-chat/sessionTracking*.ts`, using `active_study_session`.
- Quick memory and smart stats already have separate pending sync keys in `frontend/src/lib/quickMemorySync.ts` and `frontend/src/lib/smartMode.ts`.
- Gateway already forwards `X-Trace-Id` and `Idempotency-Key` downstream; backend outbox/inbox infrastructure already exists for learning-core events, but browser answer commits are not yet a unified idempotent command.

## Public Contract Changes

- Add a frontend mode contract module:
  - `frontend/src/lib/practiceResult/modeContracts.ts`
  - It must declare each runtime as one of: `practice`, `review-overlay`, `quickmemory-review`, `game-campaign`, `match-book`, `radio-session`.
  - It must declare `route`, `queueSource`, `dimensionResolver`, `writes`, `progressPolicy`, `sessionPolicy`, and `resumePolicy`.
- Add a frontend result command contract:
  - `PracticeResultCommand` must include `traceId`, `idempotencyKey`, `userScope`, `route`, `mode`, `dimension`, `word`, `wordPayload`, `result`, `occurredAt`, `session`, `progressScope`, and `adapter`.
  - Use browser-generated UUID-like values for `traceId` and deterministic `idempotencyKey` format: `practice:<sessionId|localSessionId>:<mode>:<scopeKey>:<wordKey>:<dimension>:<attemptIndex>`.
  - Use header `X-Trace-Id` and `Idempotency-Key`; do not introduce `X-Idempotency-Key` because the gateway contract already forwards `Idempotency-Key`.
- Add a durable frontend outbox:
  - Storage key: `practice_result_outbox:user:<id>`.
  - Entry states: `pending`, `sending`, `acked`, `failed`.
  - The browser must persist the command before network writes, mark `acked` only after all required planes succeed, and retry with bounded exponential backoff.
- Add a backend unified endpoint after the frontend adapter is stable:
  - Browser route: `POST /api/ai/practice/results/commit`.
  - Internal learning-core route: `POST /internal/learning/practice/results/commit`.
  - Response shape: `{ ok, traceId, idempotencyKey, duplicate, appliedPlanes, aggregateVersion }`.
  - Keep existing endpoints during migration; do not break `/api/ai/quick-memory/sync`, `/api/ai/wrong-words/sync`, `/api/ai/smart-stats/sync`, `/api/ai/practice/game/attempt`, or progress routes.
- Add a learning-core idempotency table:
  - Table name: `user_practice_result_commands`.
  - Unique key: `(user_id, idempotency_key)`.
  - Required fields: `trace_id`, `idempotency_key`, `mode`, `dimension`, `scope_key`, `word`, `status`, `command_json`, `result_json`, `created_at`, `updated_at`.
  - A replay with the same key must return the stored result without applying counters a second time.

## Task Breakdown

### Task 1: Freeze The Mode Contract

**Files:**
- Create: `frontend/src/lib/practiceResult/modeContracts.ts`
- Test: `frontend/src/lib/practiceResult/modeContracts.test.ts`
- Modify: `frontend/src/constants/practiceModes.ts`
- Test: `frontend/src/app/AppRoutes.practice.test.tsx`

- [ ] Add a typed mode matrix covering `smart`, `listening`, `meaning`, `dictation`, `follow`, `radio`, `quickmemory`, `errors`, `game`, and `match`.
- [ ] Encode the special cases explicitly:
  - `quickmemory` chapter practice writes quick-memory, session, chapter progress, and chapter mode progress.
  - `quickmemory` due review writes quick-memory, recognition mastery, wrong-word recognition on unknown, and session; it must not write chapter progress.
  - `errors` writes wrong-word dimension state, mastery, session, and local error progress; it must not write normal book/chapter progress.
  - `radio` is session-centric and must not produce answer-result commands.
  - `game` writes word mastery/game state through the game adapter.
  - `match` writes chapter progress and mode progress with `mode=match`; it does not write per-word mastery in this iteration.
- [ ] Add tests that every study-center route maps to exactly one runtime category and one progress policy.
- [ ] Update the architecture roadmap doc only if the implementation changes a contract named there.

### Task 2: Add Trace And Idempotency Plumbing

**Files:**
- Create: `frontend/src/lib/practiceResult/trace.ts`
- Create: `frontend/src/lib/practiceResult/commandKeys.ts`
- Modify: `frontend/src/lib/index.ts`
- Test: `frontend/src/lib/practiceResult/trace.test.ts`
- Test: `frontend/src/lib/schemas/api.test.ts`

- [ ] Add helpers to create and validate `traceId` and `idempotencyKey`.
- [ ] Extend `apiRequest` options with optional `traceId` and `idempotencyKey`; when present, set `X-Trace-Id` and `Idempotency-Key`.
- [ ] Preserve existing auth-refresh behavior and keepalive behavior.
- [ ] Add tests that mutating requests carry the headers, refresh retries preserve the same headers, and GET requests do not need idempotency keys.
- [ ] Do not put user identity in the idempotency key; backend must still use the cookie/internal user context.

### Task 3: Build The Frontend Result Sink And Outbox

**Files:**
- Create: `frontend/src/lib/practiceResult/types.ts`
- Create: `frontend/src/lib/practiceResult/outbox.ts`
- Create: `frontend/src/lib/practiceResult/sink.ts`
- Create: `frontend/src/lib/practiceResult/adapters.ts`
- Test: `frontend/src/lib/practiceResult/outbox.test.ts`
- Test: `frontend/src/lib/practiceResult/sink.test.ts`

- [ ] Define `PracticeResultCommand`, `PracticeResultPlane`, `PracticeResultAdapter`, and `PracticeResultSink`.
- [ ] Implement durable outbox operations: `enqueue`, `markSending`, `markAcked`, `markFailed`, `listRetryable`, `pruneAcked`.
- [ ] Initial sink behavior must orchestrate existing endpoints, not the new backend commit endpoint:
  - progress via existing `saveProgress` callback.
  - mastery via `submitWordMasteryAttempt` with `clientAttemptId=idempotencyKey`.
  - wrong words via the existing wrong-word action.
  - smart stats via `recordWordResult` and existing sync.
  - session via existing session manager snapshot.
- [ ] The sink must be the only place that decides whether a plane is required, skipped, or retryable.
- [ ] The sink must return `{ traceId, idempotencyKey, planes }` for debug display and tests.

### Task 4: Move Generic Answer Modes To The Sink

**Files:**
- Modify: `frontend/src/composables/practice/page/usePracticePageActions.ts`
- Modify: `frontend/src/composables/practice/page/usePracticePageWrongWordActions.ts`
- Test: `frontend/src/components/practice/PracticePage.test.tsx`
- Test: `frontend/src/components/practice/PracticePage.errorMode.test.tsx`
- Test: `frontend/src/components/practice/FollowMode.test.tsx`

- [ ] Replace the inline multi-write logic in `commitAnswerResult` with a `PracticeResultCommand` and `PracticeResultSink.apply`.
- [ ] Route `handleOptionSelect`, `handleSpellingSubmit`, `handleMeaningRecallSubmit`, `handleFollowReadEvaluated`, and `handleSkip` through the same command builder.
- [ ] Keep UI state updates local and immediate, but make business writes go through the sink.
- [ ] Preserve current retry behavior: a wrong answer can write mastery/wrong-word state before queue progress advances.
- [ ] Preserve current special behavior for follow: passive page visits must not create meaningful study sessions.

### Task 5: Normalize Quick Memory, Game, And Match Adapters

**Files:**
- Modify: `frontend/src/components/practice/QuickMemoryMode.tsx`
- Modify: `frontend/src/lib/quickMemorySync.ts`
- Modify: `frontend/src/lib/gamePractice.ts`
- Modify: `frontend/src/components/practice/confusable/confusableMatchPageData.ts`
- Test: `frontend/src/components/practice/QuickMemoryMode.test.tsx`
- Test: `frontend/src/components/practice/PracticePage.quickmemoryReview.test.tsx`
- Test: `frontend/src/components/practice/page/GameMode.test.tsx`
- Test: `frontend/src/components/practice/ConfusableMatchPage.test.tsx`

- [ ] Keep each special runtime independent, but make each adapter emit a command envelope with `traceId`, `idempotencyKey`, and declared `planes`.
- [ ] Quick memory sync must persist pending records before network calls and must send trace/idempotency metadata for each batch.
- [ ] Game attempts must always pass `clientAttemptId=idempotencyKey` and the request header `Idempotency-Key`.
- [ ] Match progress writes must use one idempotency key per completed group or final progress snapshot.
- [ ] Add tests for due review no chapter progress, game duplicate attempt metadata, and match progress header propagation.

### Task 6: Add Backend Idempotent Result Commit

**Files:**
- Create: `backend/model_definitions/practice_result_models.py`
- Modify: `backend/models.py`
- Create: `packages/platform-sdk/platform_sdk/learning_core_practice_result_application.py`
- Modify: `packages/platform-sdk/platform_sdk/learning_core_transport.py`
- Modify: `packages/platform-sdk/platform_sdk/gateway_browser_routes.py`
- Test: `backend/tests/test_learning_core_practice_result_commit.py`
- Test: `backend/tests/test_gateway_bff_practice_result_proxy.py`

- [ ] Add `UserPracticeResultCommand` with a unique `(user_id, idempotency_key)` constraint.
- [ ] Add the internal learning-core route and browser gateway route.
- [ ] On first commit, write the idempotency row as `processing`, apply required planes in one transaction, save `result_json`, then mark `applied`.
- [ ] On duplicate commit:
  - If `applied`, return the stored result with `duplicate: true`.
  - If `processing` is stale, allow one recovery attempt.
  - If `failed`, return `409` unless the command body is byte-equivalent to the stored command and marked retryable.
- [ ] Implement only answer-centric planes here first: progress, mastery, wrong words, smart stats, learning event. Keep session finalization on existing session endpoints until the new path is stable.
- [ ] Record `trace_id` and `idempotency_key` inside learning-event payloads for every practice attempt.

### Task 7: Switch The Sink To Unified Backend Commit Behind A Flag

**Files:**
- Modify: `frontend/src/lib/practiceResult/sink.ts`
- Modify: `frontend/src/lib/practiceResult/adapters.ts`
- Modify: `frontend/src/lib/index.ts`
- Test: `frontend/src/lib/practiceResult/sink.test.ts`
- Test: `backend/tests/test_release_risk_user_journey.py`

- [ ] Add feature flag `VITE_PRACTICE_RESULT_COMMIT=unified|legacy`, defaulting to `legacy` locally until backend coverage is green.
- [ ] In `unified` mode, answer-centric adapters call `POST /api/ai/practice/results/commit`.
- [ ] Keep quickmemory, game, and match on existing endpoints until their backend idempotency is separately complete.
- [ ] Add fallback only for transport failures before the server accepts the command; once the backend returns a trace/idempotency response, do not double-write through legacy endpoints.

### Task 8: Add Debug Trace And Consistency Checks

**Files:**
- Create: `scripts/inspect-practice-result-trace.py`
- Create: `backend/tests/test_practice_result_trace_inspector.py`
- Create: `docs/operations/practice-result-chain-runbook.md`
- Modify: `packages/platform-sdk/platform_sdk/learning_stats_payload_support.py` only if stats needs to expose trace diagnostics.

- [ ] The script accepts `--trace-id` or `--idempotency-key`.
- [ ] It prints command status, learning events, mastery state, wrong-word state, progress snapshots, and queued outbox events.
- [ ] Add a backend consistency check for modes that should write both chapter progress and chapter mode progress.
- [ ] Stats/profile fallback must expose a warning marker when it uses compatibility progress because session data is missing.

### Task 9: Retire Legacy Ambiguity Without Deleting Recovery Paths

**Files:**
- Modify: `frontend/src/lib/localStorageMigration.ts`
- Modify: `frontend/src/components/practice/progressStorage.ts`
- Modify: `frontend/src/lib/quickMemorySync.ts`
- Test: `frontend/src/lib/localStorageMigration.test.ts`
- Test: `frontend/src/components/practice/progressStorage.test.ts`

- [ ] Keep one-shot migration exactly once per user; do not change `local_storage_migration_v1_done:user:<id>` semantics.
- [ ] After migration success, legacy keys remain migration input only, not source of truth for new answer commits.
- [ ] Runtime caches must be user-scoped where possible and must include a schema version.
- [ ] Outbox retry takes precedence over stale local progress snapshots when both exist.

### Task 10: Rollout And Release

**Files:**
- Modify docs only as needed after implementation:
  - `docs/architecture/specs/2026-05-05-practice-mode-data-flow-roadmap.md`
  - `docs/operations/practice-result-chain-runbook.md`

- [ ] Run baseline checks before large edits: `pnpm check:file-lines`, `pnpm lint`, focused frontend tests, focused backend tests.
- [ ] Land the feature flag in `legacy` mode first.
- [ ] Enable `unified` mode locally and run split runtime smoke on `/plan`, `/practice`, `/practice?review=due`, `/practice?mode=errors`, `/game`, and `/practice/confusable`.
- [ ] Run data consistency checks against at least one correct and one wrong answer per mode category.
- [ ] Keep remote rollout behind environment config; use the existing production release runbook and revalidate current deploy scripts before release.

## Verification Matrix

- Frontend unit:
  - `pnpm vitest run frontend/src/lib/practiceResult`
  - `pnpm vitest run frontend/src/components/practice/PracticePage.test.tsx`
  - `pnpm vitest run frontend/src/components/practice/PracticePage.errorMode.test.tsx`
  - `pnpm vitest run frontend/src/components/practice/QuickMemoryMode.test.tsx`
- Backend focused:
  - `pytest backend/tests/test_learning_core_practice_result_commit.py -q`
  - `pytest backend/tests/test_gateway_bff_practice_result_proxy.py -q`
  - `pytest backend/tests/test_ai_sessions.py backend/tests/test_learning_events.py backend/tests/test_word_mastery_support.py -q`
- Guardrails:
  - `pnpm check:file-lines`
  - `pnpm lint`
  - `pytest backend/tests/test_source_text_integrity.py -q`
  - `pnpm build`
- Manual smoke:
  - Login as `admin` / `admin123456`.
  - Complete one correct and one wrong answer in smart, listening, meaning, dictation, follow, quickmemory chapter, due review, errors, game, and match.
  - For each smoke, capture `traceId` and verify `scripts/inspect-practice-result-trace.py` can explain every changed plane.

## Assumptions And Defaults

- The current split runtime topology stays unchanged: browser -> `gateway-bff` -> `learning-core-service`; `/socket.io` remains direct to ASR Socket.IO.
- `learning-core-service` remains authoritative for practice result facts.
- Frontend can cache and retry, but it must not become source of truth after a command is acknowledged by learning-core.
- Existing localStorage migration behavior is preserved; this plan does not delete legacy data paths until after unified commits are verified.
- The first backend commit endpoint handles answer-centric practice only; quickmemory/game/match keep their existing endpoints until their adapter idempotency is proven.
- No client-supplied user id is trusted. Backend user identity always comes from the authenticated cookie/internal service context.
- Existing dirty worktree changes must be reviewed before implementation; do not overwrite unrelated user edits.
