# Follow-Read Pronunciation Scoring PRD

## Summary

Upgrade the existing `follow` practice mode from guided playback into a scored pronunciation practice mode. Learners listen to the standard word audio, record their own pronunciation, and receive multimodal AI scoring that compares the user recording against the target word and reference pronunciation.

## Goals

- Keep `follow` as the single entry point for follow-read practice.
- Score each recorded attempt with three bands: `<60`, `60-79`, and `>=80`.
- Count `>=80` as correct and `<80` as wrong in normal learning statistics.
- Add wrong attempts to the wrong-word system under a dedicated `speaking` dimension.
- Exclude follow-read results from Ebbinghaus and quick-memory review scheduling.

## User Experience

- The page keeps the current follow-read display: word, phonetic segments, meaning, progress, playback, recording, and navigation.
- The learner plays the standard audio, records their pronunciation, then sees a score and feedback before moving on.
- Score bands:
  - `<60`: `needs_work`, shown as clearly inaccurate and counted wrong.
  - `60-79`: `near_pass`, shown as close but not passed and counted wrong.
  - `>=80`: `pass`, shown as passed and counted correct.
- Scoring errors, empty audio, or model failures show retry feedback and do not change statistics or wrong-word state.

## Data And Product Rules

- Study sessions use `mode = follow`.
- Correct/wrong counts are binary: only `>=80` is correct.
- Wrong-word dimension is `speaking`; it must not reuse `listening`.
- `speaking` wrong-word state uses the existing dimension-state structure rather than new scalar columns.
- Passing a `speaking` wrong-word review increments that dimension's pass streak; failing resets the streak.

## Acceptance Criteria

- A follow-read attempt below 60 returns `band = needs_work`, `passed = false`, and records a wrong `speaking` attempt.
- A follow-read attempt from 60 through 79 returns `band = near_pass`, `passed = false`, and records a wrong `speaking` attempt.
- A follow-read attempt at or above 80 returns `band = pass`, `passed = true`, and records a correct `speaking` attempt.
- Follow-read attempts appear in normal learning statistics and study sessions.
- No follow-read attempt creates or mutates quick-memory/Ebbinghaus review records.
