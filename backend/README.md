# Backend Overview

## Current Position

The backend is no longer a flat file layout.
It is best described as a **microservice-inspired layered modular monolith in transition**:

- One deployable Flask backend process for HTTP APIs
- One dedicated speech process for long-lived realtime audio sessions
- Capability modules split by domain or external-provider ability
- Shared data model and SQLite persistence
- Current runtime path no longer relies on direct route-to-route imports or route-level ORM queries

It is **not** a full microservice system yet because storage, deployment, and most business logic still live in one codebase and mostly one database.
The current backend is the migration source architecture for the planned microservice split, not the final long-term runtime shape.

## Layer Map

### L0 Runtime and Bootstrap

- `app.py`
- `speech_service.py`
- `config.py`
- `services/runtime_async.py`

Responsible for process startup, Flask wiring, Socket.IO wiring, proxy/runtime behavior, and startup-time repairs.

### L1 Transport and Interface

- `routes/**`
- `routes/middleware.py`

Responsible for HTTP and Socket.IO contracts, request parsing, auth guards, response formatting, and endpoint registration.

### L2 Application Services

- `services/*_service.py`
- `services/study_sessions.py`
- `services/session_logging_service.py`
- `services/notes_query_service.py`

Responsible for use-case orchestration. This layer coordinates domain rules, persistence, and provider calls for one backend capability.

### L3 Domain Modules

- `services/learner_profile_service/**`
- `services/learning_stats_service_parts/**`
- `services/notes_summary_service_parts/**`
- `services/books_confusable_service_parts/**`
- `services/word_catalog_service_parts/**`

Responsible for domain rules, calculations, normalization, planning, and business policy that should not depend on transport details.

### L4 Provider and Integration Adapters

- `services/llm_service/**`
- `services/word_tts_service/**`
- `services/asr_service.py`
- `services/asr_service_parts/**`
- `services/db_backup.py`

Responsible for talking to external systems or runtime infrastructure such as LLM, TTS, ASR, backup, and streaming adapters.

### L5 Persistence and Data Model

- `models.py`
- `model_definitions/**`
- `migrations/**`
- `services/*_repository.py`
- `database.sqlite`

Responsible for ORM models, schema shape, migration state, and persistence contracts.

### L6 Scripts, Tests, and Operations

- `scripts/**`
- `tests/**`
- root-level `test_*.py`
- logs, caches, generated audio artifacts

Responsible for verification, one-off operators, local diagnostics, and asset generation.

## Capability Modules

- `auth`: login, register, refresh, logout, email verification
- `books`: book catalog, familiar/favorite/confusable books, progress
- `ai`: assistant, learner profile, learning stats, tool context, summaries
- `notes`: summaries, jobs, exports, note queries
- `speech`: realtime ASR process and upload transcription
- `tts`: word audio, sentence audio, batch generation, OSS/audio cache
- `shared runtime`: async helpers, local time, db backup, safety checks

## Main Data Flows

1. Browser -> `routes/*` -> `services/*` -> `models/db` -> JSON response
2. Browser -> `speech_service.py` -> `services/asr_service*` -> DashScope realtime ASR -> Socket.IO events
3. Browser -> `routes/tts*` -> `services/word_tts*` or `services/tts_*` -> provider adapter -> audio bytes or URLs

## Recommended Dependency Direction

`Runtime -> Transport -> Application -> Domain -> Provider/Persistence`

Rules:

- `routes/*` should prefer calling `services/*`, not querying models directly
- current transport modules already follow that rule in the runtime path; remaining cleanup is mostly compatibility exports
- domain modules should not depend on Flask request objects
- provider adapters should not know HTTP response shapes
- persistence concerns should stay out of frontend-facing transport code

## Documentation

- API reference: [API.md](./API.md)
- Detailed layer architecture: [backend-layered-architecture.md](../docs/architecture/backend-layered-architecture.md)
- Service ownership matrix: [service-ownership-matrix.md](../docs/architecture/service-ownership-matrix.md)
- Gateway service contracts: [gateway-service-contracts.md](../docs/architecture/gateway-service-contracts.md)

Browser-facing auth now assumes `HttpOnly Cookie + gateway-bff` as the canonical contract. Any user-facing API example should reference `/api/*` through `gateway-bff`, not a browser-side header-token flow.
