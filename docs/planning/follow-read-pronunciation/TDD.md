# Follow-Read Pronunciation Scoring TDD Plan

## Test Strategy

Implement behavior in thin vertical slices. Each production change must follow a failing test.

## Red-Green Slices

1. Wrong-word dimension support
   - Add frontend wrong-word store tests proving `speaking` history, pending state, and pass streak work.
   - Add backend model/support tests proving `speaking` is accepted in dimension-state summaries.

2. Scoring band helper
   - Add backend tests for `<60`, `60-79`, and `>=80` band mapping.
   - Implement a small helper returning `{band, passed}` from numeric score.

3. Follow-read scoring API
   - Add API tests for multipart `POST /api/ai/follow-read/evaluate`.
   - Mock multimodal scoring and learning-core writes.
   - Verify response shape, three-band result, learning event, and `speaking` mastery attempt.

4. Frontend API client
   - Add tests for building multipart follow-read evaluation requests.
   - Validate the response with Zod and expose typed score bands.

5. FollowMode integration
   - Add component tests for showing banded feedback after a scoring response.
   - Add component tests that scoring failures do not navigate or record results.
   - Keep existing playback and navigation behavior intact.

## Verification Commands

- `PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_ai_speaking_assessment_application.py backend/tests/test_ai_execution_speaking_api.py -q`
- `PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pnpm --dir frontend exec vitest run src/features/vocabulary/wrongWordsStore.test.ts src/components/practice/followReadScoring.test.ts src/components/practice/FollowMode.test.tsx`
- `pnpm --dir frontend verify:repo-guards`

## Defaults

- Passing score: `80`.
- Score bands: `needs_work`, `near_pass`, `pass`.
- Wrong-word dimension: `speaking`.
- No Ebbinghaus integration for follow-read mode.
