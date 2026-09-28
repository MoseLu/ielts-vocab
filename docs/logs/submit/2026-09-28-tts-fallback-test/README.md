# Submit Log — 2026-09-28 — ielts-vocab TTS fallback proxy test

- Repository: products/ielts-vocab
- Branch: dev
- Date: 2026-09-28
- Operator: routine products/workbench L1+ dirty submit executor (audit-pass)

## Scope

Second of five commits closing the remaining L1+ dirty on
`products/ielts-vocab` after the port-fix commit
`42260192 fix(ports): source TTS/ASR URLs from AXI_*_URL env with
safe fallback` landed. This commit extends the word-audio
fallback candidate resolver tests.

## Commit

- Subject: `test(tts): fallback proxy test`
- Paths: `backend/tests/test_gateway_bff_tts_word_audio_fallback.py`

### Diff stat

- 1 file changed, 30 insertions(+)

### What changed

`backend/tests/test_gateway_bff_tts_word_audio_fallback.py`:

- `test_resolve_word_audio_request_uses_phonetic_specific_identity`
  now asserts that `resolve_word_audio_request_candidates`
  returns **two** candidates for `"the rest of"` (was 1). The
  second candidate is the production-override model:
  `azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer`.
- Adds a new test
  `test_resolve_word_audio_request_falls_back_to_production_override_upload`
  that exercises the production-override fallback path for
  the word `"consistency"` with an explicit phonetic override
  (`/kənˈsɪs.tə/`). It asserts that two candidates are
  returned: an IPA-prefixed model on the candidate that
  carries the phonetic, and the production-override buffer
  model as the fallback.

Both tests use `monkeypatch` to stub
`resolve_normal_word_audio_identity` and
`phonetic_identity.explicit_word_audio_phonetic`, so the test
scope is local to the resolver module.

## Verification

- Tested: `git diff --stat backend/tests/test_gateway_bff_tts_word_audio_fallback.py`
  → 1 file, +30/-0.
- Tested: `git diff` shows only test additions; no production
  code change.
- Not-tested: `pytest backend/tests/test_gateway_bff_tts_word_audio_fallback.py`
  (Python runtime not invoked from this environment; CI /
  local pytest runs on demand).
- Not-tested: live FastAPI run (test-only commit).

## Risks

- Low. Test additions only. Production resolver behavior was
  already in place; this commit just makes the
  fallback-candidate contract explicit.

## Directive

Owner-directed L1+ dirty closure on `products/ielts-vocab`
following the port-fix commit (`42260192`). Second of five
commits (proxy endpoint done; test now; deps, PRD, HANDOFF
pending). The new tests assert the existing contract and are
the safety net for the future fallback candidates emitted by
the proxy endpoint.
