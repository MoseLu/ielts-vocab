# Five-Dimension Game Mode Next Steps Implementation Plan

Last updated: 2026-04-26

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the five-dimension game mode into an independent AI learning campaign where each word is a map node and the current word advances through five learning defenses.

**Architecture:** The backend campaign state owns task-aware word ordering, map-node windows, and per-word dimension progression. The platform SDK and frontend schema layers pass through `task`, `dimension`, `taskFocus`, and `mapPath` without breaking older responses. The frontend renders `/game` as a word-chain campaign map and `/game/mission` as the current word mission surface, while Todo rows only link into those game tasks.

**Tech Stack:** Flask service code, platform-sdk Python application adapters, React 19 + TypeScript + Vite, SCSS game assets, Zod API schemas, Pytest, Vitest, repo guard scripts.

---

## Product Boundary

- Five-dimension mode is an independent AI learning mode, not a combined launcher for `quickmemory`, `listening`, `meaning`, `dictation`, and `follow`.
- Legacy practice modes remain as focused-practice or compatibility entries.
- `/practice?mode=game` continues to redirect to `/game`.
- The locked dimension order is `recognition -> meaning -> dictation -> speaking -> listening`.
- The storage key `listening` remains for the fifth dimension, while UI copy displays it as `语境应用`.
- A wrong answer does not hard-block the learner. Failed dimensions enter a refill/review queue while the current word can continue to the next unattempted dimension.
- Settlement records learning content, duration, accuracy, weak dimensions, and refill reasons.
- Boss and reward moments remain wave-settlement presentation, not realtime numeric combat.

## Route Contract

- `/game` opens the campaign map.
- `/game/mission` opens the current word mission.
- `/game?task=due-review` starts due review in five-dimension mode.
- `/game?task=error-review&dimension=meaning` starts weak-dimension review.
- `/game?task=continue-book&book=...&chapter=...` continues a book/chapter path.
- `/game/mission?task=...` keeps the same query parameters for direct mission entry.
- Todo rows only produce links. Backend task selection decides node priority.

## File Map

- Modify: `backend/services/word_mastery_campaign_state.py`
  - Owns game level order, active dimension selection, segment/wave state, and the game-practice response.
  - Current line count is 500, so the first backend implementation step must either replace existing segment-only logic or split helpers into a focused support module before adding new behavior.
- Modify: `packages/platform-sdk/platform_sdk/learning_core_word_mastery_application.py`
  - Accepts task query parameters and normalizes backend payload compatibility fields.
- Modify: `frontend/src/lib/gamePractice.ts`
  - Sends task, dimension, book, and chapter query parameters.
- Modify: `frontend/src/lib/schemas/api.ts`
  - Parses `taskFocus` and `mapPath.nodes` while preserving old `segment` fields.
- Modify: `frontend/src/components/home/page/HomePageSections.tsx`
  - Converts Todo action rows into game task links or CTAs.
- Modify: `packages/platform-sdk/platform_sdk/ai_home_todo_task_builders.py`
  - Stops emitting `mode: quickmemory` for due review and emits five-dimension task semantics instead.
- Modify: `frontend/src/components/practice/page/game-mode/GameMapShell.tsx`
  - Reframes the desktop map as a word-chain defense map.
- Modify: `frontend/src/components/practice/page/game-mode/GameStage.tsx`
  - Reframes mobile mission layout as immersive portrait gameplay.
- Update tests:
  - `backend/tests/test_word_mastery_support.py`
  - `frontend/src/components/practice/page/GameMode.test.tsx`
  - `frontend/src/components/home/page/HomePage.test.tsx`
  - `frontend/src/lib/schemas/api.test.ts`

## Task Breakdown

### Task 1: Backend Dimension Progression

**Files:**
- Modify: `backend/services/word_mastery_campaign_state.py`
- Test: `backend/tests/test_word_mastery_support.py`

- [ ] **Step 1: Add failing backend assertions for the locked dimension order**

  In `backend/tests/test_word_mastery_support.py`, assert that `levelCards` are ordered by dimensions:

  ```python
  ['recognition', 'meaning', 'dictation', 'speaking', 'listening']
  ```

  Run:

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_word_mastery_support.py -q
  ```

  Expected before implementation: at least one order assertion fails if the current order still reflects the old game-card order.

- [ ] **Step 2: Add failing backend assertions for non-hard-block progression**

  Create or extend a test fixture where the active word has `recognition` failed, `meaning` not started, and other dimensions not started. Assert that the active level becomes `meaning`, while `recognition` remains present in failed/refill dimensions.

  Expected before implementation: the old active-level logic may return the failed dimension first.

- [ ] **Step 3: Implement the dimension selection rule without growing the 500-line file**

  Update `GAME_LEVELS` to the locked order. Update `_active_game_level_for_states()` so it:

  1. returns the first `not_started` dimension in `GAME_LEVELS`;
  2. if no unattempted dimension exists, returns the first due or pending refill dimension;
  3. only falls back to `None` when the word has no actionable dimension.

  If extra helpers are needed, move map-window or settlement helper logic into a new focused module rather than pushing `word_mastery_campaign_state.py` above 500 lines.

- [ ] **Step 4: Keep wave sizing as rhythm only**

  Preserve `GAME_SEGMENT_WORD_COUNT = 5`, but describe it in response fields as wave/Boss rhythm. Do not expose it as "five levels".

- [ ] **Step 5: Re-run backend support tests**

  Run:

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_word_mastery_support.py -q
  ```

  Expected after implementation: all word-mastery support tests pass.

### Task 2: Backend Task-Aware State Shape

**Files:**
- Modify: `backend/services/word_mastery_campaign_state.py`
- Modify: `packages/platform-sdk/platform_sdk/learning_core_word_mastery_application.py`
- Test: `backend/tests/test_word_mastery_support.py`

- [ ] **Step 1: Add failing tests for task parameters**

  Cover these inputs:

  ```text
  task=due-review
  task=error-review&dimension=meaning
  task=continue-book&book=<book-id>&chapter=<chapter-id>
  ```

  Assert the response includes `taskFocus` and that task-specific node priority is reflected in the active word or active dimension.

- [ ] **Step 2: Extend `build_game_practice_state()` inputs**

  Add optional `task`, `dimension`, `book`, and `chapter` inputs. Normalize unsupported task values to the default campaign state.

- [ ] **Step 3: Add `taskFocus` output**

  Return a compact object such as:

  ```json
  {
    "task": "error-review",
    "dimension": "meaning",
    "book": null,
    "chapter": null
  }
  ```

  Keep values nullable when a query parameter is absent.

- [ ] **Step 4: Add `mapPath.nodes` output**

  Return a word-node window where each node represents a word, not a dimension card. Node states should include the product states needed by the frontend: locked, current, cleared, refill, boss, and reward.

- [ ] **Step 5: Preserve old response compatibility**

  Keep existing `segment`, `levelCards`, `speakingBoss`, and `speakingReward` fields until frontend call sites no longer need them.

### Task 3: API And Schema Compatibility

**Files:**
- Modify: `frontend/src/lib/gamePractice.ts`
- Modify: `frontend/src/lib/schemas/api.ts`
- Test: `frontend/src/lib/schemas/api.test.ts`

- [ ] **Step 1: Add schema tests for new fields**

  Add a fixture with `taskFocus` and `mapPath.nodes`, then parse it through the existing game-practice schema.

- [ ] **Step 2: Keep legacy fixture passing**

  Keep the current fixture with `segment` and no `mapPath` valid. Defaults must not break old responses.

- [ ] **Step 3: Send task query parameters**

  Update `fetchGamePracticeState()` so it passes through `task`, `dimension`, `book`, and `chapter` when provided.

- [ ] **Step 4: Run schema tests**

  Run:

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pnpm --dir frontend exec vitest run src/lib/schemas/api.test.ts
  ```

### Task 4: Todo Entry Routing

**Files:**
- Modify: `frontend/src/components/home/page/HomePageSections.tsx`
- Modify: `packages/platform-sdk/platform_sdk/ai_home_todo_task_builders.py`
- Test: `frontend/src/components/home/page/HomePage.test.tsx`

- [ ] **Step 1: Add Todo navigation tests**

  Cover these mappings:

  ```text
  due-review -> /game?task=due-review
  error-review + dimension=meaning -> /game?task=error-review&dimension=meaning
  continue-book + book/chapter -> /game?task=continue-book&book=...&chapter=...
  add-book -> existing book/plan entry
  ```

- [ ] **Step 2: Add a small route helper**

  Keep the helper local to `HomePageSections.tsx` unless multiple components need it. Encode query parameters through `URLSearchParams`.

- [ ] **Step 3: Update due-review builder semantics**

  In `ai_home_todo_task_builders.py`, remove `mode: quickmemory` from the due-review action. Emit the five-dimension task action instead:

  ```python
  {'kind': 'due-review', 'cta_label': '进入五维复习', 'task': 'due-review', 'dimension': None}
  ```

- [ ] **Step 4: Run home tests**

  Run:

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pnpm --dir frontend exec vitest run src/components/home/page/HomePage.test.tsx
  ```

### Task 5: Desktop Word-Chain Map

**Files:**
- Modify: `frontend/src/components/practice/page/game-mode/GameMapShell.tsx`
- Modify related SCSS only if required by the existing component structure.
- Test: `frontend/src/components/practice/page/GameMode.test.tsx`

- [ ] **Step 1: Add tests that the map nodes represent words**

  Assert the map renders `mapPath.nodes` when present and does not label the path as "current segment five words".

- [ ] **Step 2: Reframe map copy and accessibility labels**

  Use "词链防线地图" and word-node status language. Keep `levelCards` as current-word defenses.

- [ ] **Step 3: Render node states**

  Use existing game assets, HUD, tower-defense nodes, character art, reward layer, and Boss/reward affordances. Avoid plain webpage card treatment.

- [ ] **Step 4: Preserve fallback behavior**

  If `mapPath.nodes` is missing, derive a minimal word path from the legacy `segment` object so older responses still render.

### Task 6: Mobile Mission Surface

**Files:**
- Modify: `frontend/src/components/practice/page/game-mode/GameStage.tsx`
- Modify related SCSS only if required by the existing component structure.
- Test: `frontend/src/components/practice/page/GameMode.test.tsx`

- [ ] **Step 1: Add tests for direct mission route layout**

  Assert `/game/mission` auto-starts the active task, renders the current word mission, and exposes the five-dimension order in the locked sequence.

- [ ] **Step 2: Reorder stage kinds**

  Align mission order with:

  ```text
  recognition -> meaning -> dictation -> speaking -> listening
  ```

- [ ] **Step 3: Build portrait-first structure**

  Keep a top mini-map or wave strip, a middle current-word scene, and a bottom interaction zone for choice/input/recording.

- [ ] **Step 4: Keep game visual system in the mission**

  Continue using current game assets, HUD, scene backgrounds, mic states, tower-defense nodes, rewards, stars, and resource UI. Do not replace the mission with ordinary web cards.

### Task 7: Verification And Guard

**Files:**
- No production file should change in this task unless verification exposes a concrete mismatch.

- [ ] **Step 1: Run backend word-mastery tests**

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_word_mastery_support.py -q
  ```

- [ ] **Step 2: Run focused frontend tests**

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pnpm --dir frontend exec vitest run src/components/practice/page/GameMode.test.tsx src/components/home/page/HomePage.test.tsx src/lib/schemas/api.test.ts
  ```

- [ ] **Step 3: Run repo guards**

  ```bash
  PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pnpm --dir frontend verify:repo-guards
  ```

- [ ] **Step 4: Record outcome**

  If implementation is completed in a later turn, add a submit record under `docs/logs/submit/` with the final test results and notable compatibility decisions.

## First-Release AI Scope

- Use `word.image` for AI-backed visual context where available.
- Use confusables for recognition and meaning-choice distractors.
- Use examples or an application prompt for `语境应用`.
- Continue using existing pronunciation and speech capabilities for speaking feedback.
- Defer full-time AI tutor narration and weak-dimension summary to a later pass.

## Risks

- `word_mastery_campaign_state.py` is already at the 500-line cap. Treat file splitting or replacement as part of the backend task, not cleanup.
- Old clients may still rely on `segment` and current card labels. Preserve compatibility fields until all call sites are migrated.
- `listening` has two meanings: persisted dimension key and UI experience label. Keep storage key stable and centralize display copy as `语境应用`.
- Mobile mission polish can easily become a generic card layout. Verify it still uses the game asset system.
- Todo routing must stay declarative. Do not move task execution rules into the homepage component.

## Acceptance Criteria

- A learner entering from Todo or `/game` sees a word-chain campaign plus the current word's five-step learning progression.
- The map nodes represent words, not five total game levels.
- Wrong dimensions refill into review without trapping the learner on the same failed step.
- `due-review`, `error-review`, and `continue-book` enter the same five-dimension game experience with task-aware priority.
- Existing legacy responses still parse and render.
- Focused backend tests, focused frontend tests, and `verify:repo-guards` pass.
