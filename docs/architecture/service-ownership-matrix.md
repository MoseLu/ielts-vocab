# Service Ownership Matrix

Last updated: 2026-04-09

## Purpose

This document freezes the first-pass ownership model for the target microservice system.

Use it to answer four questions before any capability is extracted:

1. Which service is authoritative for writes?
2. Which services may read the data directly, and which must go through an API?
3. Which storage boundary should eventually belong to the service?
4. Which code in the current modular monolith is the extraction source?

## Ownership Rules

- A service that owns a capability owns the write path for that capability.
- `gateway-bff` may orchestrate requests, but it must not remain a long-term shared write surface for downstream service data.
- During transition, multiple services may still share the same physical SQLite or future PostgreSQL cluster, but shared storage does not imply shared write authority.
- Cross-service reads should prefer API calls, read projections, or cached views.
- Cross-service shared-write tables are a temporary migration smell and should be removed once a service becomes authoritative.

## Matrix

| Service | Primary responsibility | Authoritative writes | Allowed reads | Target storage boundary | Current source modules | Extraction phase |
| --- | --- | --- | --- | --- | --- | --- |
| `gateway-bff` | Browser-facing gateway, auth edge, aggregation, compatibility | No long-term business-domain writes; temporary request/session orchestration only | May read downstream APIs and compatibility caches | Minimal edge-only state | [app.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/app.py), [routes/**](/F:/enterprise-workspace/projects/ielts-vocab/backend/routes), [routes/middleware.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/routes/middleware.py) | Phase 3 |
| `asr-service` | Realtime ASR, file transcription, audio-session lifecycle | Realtime session state, transcription job state, ASR temp artifacts | May read gateway-propagated user context and content hints | ASR session store and temp artifact store | [speech_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/speech_service.py), [speech_socketio.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/routes/speech_socketio.py), [asr_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/asr_service.py) | Phase 2 |
| `tts-media-service` | TTS generation, audio cache, media batch jobs | Audio cache metadata, media job state, generated artifacts | May read catalog content and gateway user context | Media cache store and generated object/file storage | [tts.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/routes/tts.py), [word_tts.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/word_tts.py), [word_tts_service](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/word_tts_service) | Phase 2 |
| `catalog-content-service` | Vocabulary catalog, chapters, word detail, enrichment, examples | Books, chapters, content metadata, word detail enrichment, content indexes | May expose read APIs to gateway, TTS, AI execution, learning-core | Catalog/content database and search indexes | [books_vocabulary_loader_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/books_vocabulary_loader_service.py), [word_catalog_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/word_catalog_service.py), [word_detail_enrichment.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/word_detail_enrichment.py) | Phase 2 |
| `ai-execution-service` | LLM execution, streaming, provider routing, prompt runtime | Prompt-run records, model routing config, tool execution logs, LLM cache | May read gateway-provided user context, catalog snippets, notes context payloads | AI execution database and provider cache | [llm_service](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/llm_service), [ai_assistant_ask_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/ai_assistant_ask_service.py), [ai_assistant_tool_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/ai_assistant_tool_service.py) | Phase 2 |
| `learning-core-service` | Learning facts, quick-memory, wrong words, sessions, stats source-of-truth | Study sessions, quick-memory records, wrong words, chapter progress, learner-profile source facts | May read catalog IDs and AI summaries through explicit interfaces | Learning-state database and derived read models | [study_sessions.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/study_sessions.py), [session_logging_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/session_logging_service.py), [learning_stats_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/learning_stats_service.py), [ai_wrong_words_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/ai_wrong_words_service.py) | Phase 4 |
| `notes-service` | Notes, summaries, exports, journal outputs | Notes, summary jobs, exports, rendered summary records | May read learning-core facts and AI execution outputs through service APIs | Notes database and export artifact storage | [notes_query_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_query_service.py), [notes_summary_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_summary_service.py), [notes_summary_job_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/notes_summary_job_service.py) | Phase 4 |
| `identity-service` | Identity, sessions, refresh tokens, email verification, account security | Users, revoked tokens, email verification, auth audit records | May expose identity and permission claims to gateway and internal services | Identity database and security audit store | [auth_session_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/auth_session_service.py), [auth_repository.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/auth_repository.py), [auth_email_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/auth_email_service.py) | Phase 4 |
| `admin-ops-service` | Admin dashboards, user-management operations, audit and reporting | Admin audit records, moderation state, ops read models | May read identity, learning-core, notes, and catalog through service contracts | Admin operations database and analytics read models | [admin_overview_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_overview_service.py), [admin_user_management_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/services/admin_user_management_service.py) | Phase 4 |

## Initial Read Rules

- `gateway-bff` may call every downstream service, but should not bypass their ownership by writing shared tables directly.
- `learning-core-service` may read catalog identifiers and word metadata, but catalog content remains owned by `catalog-content-service`.
- `notes-service` may read learning facts and AI outputs, but should not write study-session or quick-memory state.
- `ai-execution-service` may receive assembled prompt context from gateway or notes, but should not directly mutate learning-state tables.
- `tts-media-service` and `asr-service` may consume catalog or user context inputs, but should not own learning progress or auth state.

## Transition Constraints

- Until `identity-service` exists, `gateway-bff` temporarily remains the authentication edge.
- Until `learning-core-service` is extracted, current study-state writes remain inside the main Flask backend, but new interfaces should be shaped as if the service already existed.
- `speech_service.py` already proves process separation, but it is not yet a full service boundary until it has a frozen contract, independent config policy, and service-to-service auth.
- `tts` and `catalog` should be extracted before `learning-core`; they have clearer provider/content boundaries and fewer cross-service transactions.

## Readiness Checklist Per Service

Before a row in the matrix is treated as a true service, all of the following must be true:

- the service has a stable API contract
- the service has a clear authoritative write boundary
- the service has `/health` and `/ready`
- the service emits structured logs with request and trace IDs
- the service has timeout, retry, and idempotency rules
- the service can be deployed and rolled back independently
- the gateway no longer writes the service's data directly

## Related Docs

- Layered source architecture: [backend-layered-architecture.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/backend-layered-architecture.md)
- Gateway contract skeleton: [gateway-service-contracts.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/gateway-service-contracts.md)
- Backend migration TODO: [backend/TODO.md](/F:/enterprise-workspace/projects/ielts-vocab/backend/TODO.md)
