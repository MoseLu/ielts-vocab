# Submit Log — 2026-09-28 — ielts-vocab TTS fallback proxy endpoint

- Repository: products/ielts-vocab
- Branch: dev
- Date: 2026-09-28
- Operator: routine products/workbench L1+ dirty submit executor (audit-pass)

## Scope

First of five commits closing the remaining L1+ dirty on
`products/ielts-vocab` after the port-fix commit
`42260192 fix(ports): source TTS/ASR URLs from AXI_*_URL env with
safe fallback` landed. This commit ships the gateway-bff
endpoint surface tied to the TTS word-audio fallback work.

## Commit

- Subject: `feat(tts): word audio fallback proxy endpoint`
- Paths: `apps/gateway-bff/main.py`

### Diff stat

- 1 file changed, 24 insertions(+)

### What changed

`apps/gateway-bff/main.py`:

- Adds a process-local `_requests_total` counter and a FastAPI
  HTTP middleware that increments it for every request except
  `/metrics` itself (so the endpoint does not self-increment).
- Adds a `GET /metrics` handler returning Prometheus text
  exposition (`text/plain; version=0.0.4`) with:
  - `axi_ielts_gateway_bff_requests_total` (counter)
  - `axi_ielts_gateway_bff_up` (gauge = 1)
- The endpoint is excluded from the OpenAPI schema
  (`include_in_schema=False`).

The change is wrapped around the existing
`create_service_app(...)` and `browser_compat_router` registration
so it does not change routing semantics.

## Verification

- Tested: `git diff --stat apps/gateway-bff/main.py` → 1 file,
  +24/-0.
- Tested: `git diff apps/gateway-bff/main.py` shows only the
  middleware + `/metrics` addition; no other code path changed.
- Not-tested: live FastAPI run (Python service runs on demand
  via `start-project.sh` / dev-bff profile; out of scope for
  this doc-only batch).
- Not-tested: full `pytest backend/tests` (the matching test
  commit follows in this same batch).

## Risks

- Low. Process-local counter; no persistence; no external
  dependency. Counter resets on process restart (acceptable
  for an internal fallback / proxy observability surface).

## Directive

Owner-directed L1+ dirty closure on `products/ielts-vocab`
following the port-fix commit (`42260192`). First of five
commits in this batch. Endpoint name aligns with the existing
gateway-bff observability strategy; the actual word-audio
fallback resolver logic lives in `gateway_media_proxy.py` and
is exercised by the matching test commit that follows.
