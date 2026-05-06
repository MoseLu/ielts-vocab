# Follow-Read Pronunciation Boundary TDD Plan

## Test Strategy

Protect the 2026-05-06 product boundary: `follow` is foundational and stats-linked; AI-scored speaking is advanced and independent. Each production change must first prove which side of that boundary it touches.

## Red-Green Slices

1. Foundational follow-read statistics
   - Add frontend submitter tests proving `follow` records normal study-session and mode-performance facts.
   - Add Ebbinghaus adapter tests proving passed and failed follow-read attempts update quick-memory records.

2. Wrong-word dimension support
   - Add frontend wrong-word store tests proving `speaking` history, pending state, and pass streak work.
   - Add backend model/support tests proving `speaking` is accepted in dimension-state summaries.

3. Advanced AI speaking separation
   - Add route or API tests proving AI speaking assessment is reached through the advanced five-dimension/speaking entry, not through `mode=follow`.
   - Verify advanced speaking writes campaign or AI assessment metrics without mutating foundational Ebbinghaus records unless explicitly bridged by a later product decision.

4. FollowMode integration
   - Keep existing playback and navigation behavior intact.
   - Add component tests proving the foundational follow-read path does not require AI scoring availability.

## Verification Commands

- `PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_ai_speaking_assessment_application.py backend/tests/test_ai_execution_speaking_api.py -q`
- `PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pnpm --dir frontend exec vitest run src/composables/practice/page/usePracticeWordMasterySubmitter.test.tsx src/components/practice/FollowMode.test.tsx`
- `pnpm --dir frontend verify:repo-guards`

## Defaults

- Wrong-word dimension: `speaking`.
- Ebbinghaus integration: enabled for foundational follow-read attempts.
- AI scoring: advanced independent mode only.
