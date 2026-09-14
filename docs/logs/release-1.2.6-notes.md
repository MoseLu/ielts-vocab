# Release v1.2.6 Notes

## Scope
Main commits ahead of `main` (release/1.2.5):
- 8 phonetics fixes (luo audit + catalog-wide 12,396-word audit)
- 4 practice test-mode shortcut improvements
- Several docs/ci/bookkeeping commits

## Highlights

### Phonetic accuracy (luo + catalog-wide)
- **130 catalog-wide unsafe IPA overrides** applied (Wiktionary + Cambridge + ipa-dict, 2-source consensus)
- **16 luo favorites fixed** (12 unsafe + 1 blood pressure phrase + 3 LLM-rejected plurals)
- **100 horizontal-extension words** with full 2-source consensus
- Azure word-tts MP3s synthesized for all 246 fixed words, uploaded to OSS production cache path, **244/246 verified** against production metadata API

### Practice test-mode
- Test-mode shortcut hints now inherit the answer-button theme color (orange/yellow/red)
- Removed the "listening phase shortcut preview" (was confusing users)
- Compact viewport layout preserved

### Tooling
- `scripts/audit_all_phonetics.py`: full catalog IPA audit (Wiktionary + Cambridge + ipa-dict, 3 sources)

## Verified
- `pnpm exec vitest run src/components/practice/TestMode.test.tsx` — 8/8 tests pass
- `pnpm lint` — clean
- Production metadata API byte_length + etag verification: **244/246 OK**, 2 in `ielts_confusable_match.json` books return 404 from the metadata endpoint (separate production-side catalog visibility issue, MP3s are on OSS)

## Out of scope this release
- 24 disagreement fixes (need human spot-check, e.g. multi-POS words like `abuse`)
- 803 phrases (need separate phrase_policy decision)
- `consistency` / `manufacturer` 404 on production (catalog visibility gap, not phonetic)

## Follow-up
- Spot-check 5-10 of the 130 new MP3s in browser to confirm SSML phoneme rendering
- Investigate `consistency` / `manufacturer` 404 — likely production backend catalog filter excluding narrow-scope books from TTS lookup
