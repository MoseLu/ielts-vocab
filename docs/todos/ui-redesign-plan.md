# UI Redesign Plan

Last updated: 2026-03-29

## Objective
- Establish a consistent product-wide UI system inspired by the audit findings instead of continuing page-by-page patchwork.
- Execute in phases so each pass is small enough to verify with existing frontend tests.

## Current Focus
- [completed] Phase 1: global baseline
- [completed] Phase 2: shell and navigation polish
- [completed] Phase 3: core learning pages polish
- [in_progress] Phase 4: secondary pages and copy cleanup
- [pending] Phase 5: final visual QA and regression pass

## Phase 1 Scope
- Expand global page spacing and center rhythm.
- Define stronger surface, border, shadow, and typography tokens.
- Normalize shared loading and button visual language.
- Keep changes infrastructure-level so later page work can reuse them.

## Phase 2 Scope
- Refine header, sidebar, and mobile bottom navigation.
- Align navigation hierarchy with the product's primary learning flows.
- Remove shell-level visual drift between desktop and mobile.

## Phase 3 Scope
- Polish vocab books, study center, chapter modal, and practice shell.
- Improve hierarchy, spacing, and section grouping on high-traffic pages.

## Phase 4 Scope
- Polish journal, stats, profile, AI chat, and remaining utility panels.
- Clean corrupted copy and unify empty, loading, and error states.

## Verification
- Run `npm test` after each completed phase.
- Use visual passes to catch layout regressions that unit tests cannot cover.

## Progress Log
- 2026-03-29: created phased UI redesign plan in root TODO.
- 2026-03-29: completed phase 1 baseline tokens, spacing, loading centering, and shared button polish.
- 2026-03-29: started phase 2 shell polish for header, sidebar, and bottom navigation.
- 2026-03-29: completed phase 2 shell polish across header, sidebar, bottom navigation, and practice control chrome.
- 2026-03-29: completed phase 3 polish for vocabulary library, study center, chapter modal, and practice session surfaces.
- 2026-03-29: started phase 4 with loading copy fallback, header navigation spacing, statistics dashboard polish, and journal markdown/layout refinement.
- 2026-03-29: improved admin user-list responsiveness, hardened session duration recording to avoid 0s activity rows, and pushed glassmorphism tokens closer to the reference visual direction.
- 2026-03-29: fixed empty study-session leakage by adding cancel-session handling, required at least one real word interaction before logging, and deleted historical zero-value session rows from the local database.
- 2026-03-30: audited listening, dictation, and radio audio playback; unified example sentence playback onto the shared audio controller, reduced autoplay race conditions, and removed answer-state coloring from option POS tags.
