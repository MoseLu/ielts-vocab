# Gateway Service Contracts

Last updated: 2026-04-09

## Purpose

This document defines the first-pass contract skeleton between `gateway-bff` and the first extraction wave:

- `asr-service`
- `tts-media-service`
- `catalog-content-service`
- `ai-execution-service`

It is intentionally narrower than a full API reference.
Its job is to freeze the service-to-service rules before capability extraction starts.

## Global Rules

### Browser to Gateway

- Browsers authenticate only against `gateway-bff`.
- Browser cookies, refresh tokens, and frontend compatibility stay at the gateway edge.
- Browsers do not call internal services directly.

### Gateway to Service

- Gateway calls downstream services over explicit versioned contracts such as `/v1/...`.
- Gateway propagates user context; downstream services must not parse browser cookies.
- Gateway must set timeouts on every downstream call.
- Mutating requests must support idempotency when retries are possible.
- Streaming responses must preserve `request_id` and `trace_id` in the first response frame or headers.

## Required Headers

| Header | Direction | Purpose |
| --- | --- | --- |
| `X-Request-Id` | gateway -> service | per-request correlation ID |
| `X-Trace-Id` | gateway -> service | distributed trace root |
| `X-User-Id` | gateway -> service | authenticated user identity |
| `X-User-Scopes` | gateway -> service | authorization scope list |
| `X-Service-Name` | gateway -> service | caller identity such as `gateway-bff` |
| `Authorization: Bearer <internal-token>` | gateway -> service | internal service authentication |
| `Idempotency-Key` | gateway -> service | required for retryable mutating operations |

## Standard Response Rules

- Success responses return JSON unless the endpoint is explicitly streaming or returning media bytes.
- Error responses use one envelope shape.
- Health endpoints must not depend on browser auth.

### Error Envelope

```json
{
  "error": {
    "code": "UPSTREAM_TIMEOUT",
    "message": "tts-media-service timed out",
    "retryable": true
  },
  "request_id": "req_123",
  "trace_id": "trace_456"
}
```

## Standard Operational Endpoints

Every extracted service must expose:

- `GET /health`
- `GET /ready`
- `GET /version`

`/health` means the process is alive.

`/ready` means the service can actually serve traffic, including critical dependencies.

## Timeout Baseline

| Service | Baseline timeout | Retry default |
| --- | --- | --- |
| `asr-service` realtime control APIs | 5s | no automatic retry for active session mutations |
| `asr-service` file transcription job submission | 15s | retryable with idempotency key |
| `tts-media-service` cache lookup | 5s | safe retry |
| `tts-media-service` generation request | 30s | retryable only for idempotent job creation |
| `catalog-content-service` reads | 5s | safe retry |
| `ai-execution-service` non-streaming prompt run | 30s | retry only if provider call did not start |
| `ai-execution-service` streaming run | connect timeout 5s, stream budget 90s | no transparent retry mid-stream |

## Contract Skeletons

### `asr-service`

#### Responsibilities

- realtime speech session lifecycle
- file transcription jobs
- ASR provider adaptation
- transient audio-session state

#### Initial inbound contracts

- `POST /v1/transcriptions/file-jobs`
  - create a file-transcription job
  - requires `Idempotency-Key`
- `GET /v1/transcriptions/file-jobs/{job_id}`
  - fetch job status and transcript result
- `POST /v1/realtime-sessions`
  - create or resume a realtime ASR session
- `DELETE /v1/realtime-sessions/{session_id}`
  - close a realtime ASR session
- Socket.IO namespace or equivalent realtime channel for transcript events

#### Response shape notes

- file job creation returns `job_id`, `status`, `created_at`
- realtime session creation returns `session_id`, `transport`, `expires_at`
- transcript events must carry `request_id`, `trace_id`, `session_id`, `sequence`

### `tts-media-service`

#### Responsibilities

- word audio generation
- sentence audio generation
- cache lookup and cache persistence
- batch media jobs and generated artifacts

#### Initial inbound contracts

- `POST /v1/tts/word-audio`
  - resolve or generate one word audio asset
- `POST /v1/tts/sentence-audio`
  - resolve or generate one sentence audio asset
- `POST /v1/tts/batch-jobs`
  - create a batch generation job
  - requires `Idempotency-Key`
- `GET /v1/tts/batch-jobs/{job_id}`
  - query batch job status
- `GET /v1/media/{media_id}`
  - fetch generated media metadata or signed access URL

#### Response shape notes

- cache hits should clearly return `cache_hit: true`
- long-running generation should return a `job_id` instead of blocking indefinitely
- gateway should not need to know provider-specific voice or storage details

### `catalog-content-service`

#### Responsibilities

- book catalog
- chapter and word listings
- word detail and enrichment
- examples, confusables, and content indexes

#### Initial inbound contracts

- `GET /v1/books`
- `GET /v1/books/{book_id}`
- `GET /v1/books/{book_id}/chapters`
- `GET /v1/books/{book_id}/chapters/{chapter_id}/words`
- `GET /v1/words/{word}`
- `GET /v1/confusables/{group_key}`

#### Response shape notes

- content identifiers must be stable across services
- gateway and learning-core should treat catalog IDs as foreign references, not local ownership
- enrichment fields should be additive and versioned, not silently repurposed

### `ai-execution-service`

#### Responsibilities

- LLM provider routing
- prompt execution
- streaming token output
- tool execution adaptation
- low-level AI runtime concerns

#### Initial inbound contracts

- `POST /v1/prompt-runs`
  - execute one non-streaming prompt run
- `POST /v1/prompt-runs/stream`
  - execute one streaming prompt run
- `GET /v1/prompt-runs/{run_id}`
  - inspect recorded run metadata
- `POST /v1/tools/execute`
  - run one gateway-approved tool invocation

#### Response shape notes

- gateway sends assembled prompt context and policy flags
- downstream service returns model output, usage, finish reason, provider metadata, and trace identifiers
- gateway remains responsible for product-level response shaping and permission checks

## What Stays in Gateway During Early Phases

- browser authentication and cookie handling
- product-specific aggregation
- backward-compatible frontend response shapes
- composition of user context from learning-core, notes, and catalog
- edge rate limiting and request admission

## What Must Not Stay in Gateway Long Term

- direct provider-specific LLM calls
- direct audio generation workflows
- direct ownership of catalog content
- long-lived realtime ASR session management
- direct writes to downstream-service-owned persistence once ownership is frozen

## Rollout Rules

- new service contracts launch behind gateway feature flags or routing switches
- gateway must support fallback to the in-process implementation until contract tests and production canaries pass
- removing the in-process fallback requires observability, rollback, and ownership gates to be green

## Related Docs

- Service ownership matrix: [service-ownership-matrix.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/service-ownership-matrix.md)
- Layered source architecture: [backend-layered-architecture.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/backend-layered-architecture.md)
- Backend migration TODO: [backend/TODO.md](/F:/enterprise-workspace/projects/ielts-vocab/backend/TODO.md)
