# Follow-Read Pronunciation Boundary PRD

## Summary

Decision update, 2026-05-06: `follow` is a foundational practice mode. It belongs with smart, listening, meaning, dictation, quickmemory, and errors in the stats-linked learning loop. AI-scored speaking belongs to the independent five-dimension / speaking mode family planned for paid capability or a 2.0 release.

## Goals

- Keep `follow` as the foundational entry point for follow-read practice.
- Count assessed follow-read results in normal learning statistics.
- Add wrong attempts to the wrong-word system under a dedicated `speaking` dimension.
- Feed follow-read results into the same Ebbinghaus / quick-memory schedule used by other foundational answer modes.
- Keep AI pronunciation scoring out of `follow` unless a future product decision explicitly moves it back into the foundational tier.

## User Experience

- The page keeps the current follow-read display: word, phonetic segments, meaning, progress, playback, recording, and navigation.
- The learner should not be forced into a paid or AI-scored flow to complete foundational follow-read practice.
- If advanced AI speaking is available, it should be presented as a separate advanced entry, not as the hidden scoring engine for `follow`.

## Data And Product Rules

- Study sessions use `mode = follow`.
- Wrong-word dimension is `speaking`; it must not reuse `listening`.
- `speaking` wrong-word state uses the existing dimension-state structure rather than new scalar columns.
- Passing a `speaking` wrong-word review increments that dimension's pass streak; failing resets the streak.
- Follow-read results participate in Ebbinghaus scheduling through the shared quick-memory record path.
- Advanced AI speaking results may write advanced campaign or AI assessment metrics, but must not replace foundational follow-read stats.

## Acceptance Criteria

- A failed follow-read attempt records a wrong `speaking` attempt.
- A passed follow-read attempt records a correct `speaking` attempt.
- Follow-read attempts appear in normal learning statistics and study sessions.
- Follow-read attempts create or update Ebbinghaus review records.
- AI-scored speaking is documented and implemented as an advanced independent mode, not as a mutation of `follow`.
