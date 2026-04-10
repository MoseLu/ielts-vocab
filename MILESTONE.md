# Milestone
Last updated: 2026-04-10 16:20:09 +08:00

## Current Milestone
- Complete the backend transition from a split-service runtime into a classical microservice architecture while keeping the already deployed remote backend stable: `gateway-bff` remains the only browser ingress, service-owned PostgreSQL boundaries replace shared persistence, shared platform support modules absorb monolith helpers, Redis and RabbitMQ become real infrastructure dependencies, event-driven read models replace shared reads, and the monolith is retired only after remote rollout, smoke verification, and rollback paths are in place.

## Completed
- Established local microservice entrypoints for `gateway-bff`, `identity-service`, `learning-core-service`, `catalog-content-service`, `ai-execution-service`, `tts-media-service`, `asr-service`, `notes-service`, and `admin-ops-service`, plus dedicated ASR Socket.IO runtime on `5001`.
- Provisioned one local PostgreSQL database and one role per service on `127.0.0.1:55432`, and aligned split-service env loading with `backend/.env` plus `backend/.env.microservices.local`.
- Added shared readiness checks and a one-command backend orchestration path via [start-microservices.ps1](/F:/enterprise-workspace/projects/ielts-vocab/start-microservices.ps1), including port reservation and forced process cleanup to avoid Windows port-collision regressions.
- Moved browser compatibility routing behind `gateway-bff`, added downstream readiness probing, and kept `/api/*` and `/socket.io` behavior compatible with the current frontend.
- Localized a large slice of service application logic into `packages/platform-sdk`, including identity session and email helpers, learning-core library and progress wrappers, catalog-content read and confusable wrappers, notes word-note writes, admin detail helpers, and the ai-execution support stack.
- Removed direct `platform-sdk` dependence on high-level monolith service modules such as `services.ai_*`, `services.auth_session_helpers`, `services.books_catalog_service`, `services.books_confusable_service`, `services.books_progress_service`, `services.books_favorites_service`, `services.books_familiar_service`, `services.memory_topics`, `services.runtime_async`, and `services.local_time`.
- Landed a real remote deployment baseline on `119.29.182.134` with nginx, systemd-managed split services, PostgreSQL provisioning, and production env-file conventions documented in [cloud-microservices-deployment.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/cloud-microservices-deployment.md).

## In Progress
- Shrinking the remaining `platform-sdk -> services.*` dependency surface to lower-level repositories, provider adapters, schedule/session helpers, learner-profile read logic, and notes summary helpers.
- Turning the split runtime into the canonical backend path in both local and remote environments by keeping service startup, readiness, nginx proxy behavior, and systemd-managed rollout safety green after each refactor slice.
- Preparing the next layer of decoupling work: service-owned repositories, service-owned model modules, and per-service migration baselines instead of shared ORM ownership.
- Converging the backend onto a real microservice delivery target rather than a service-shaped monolith with shared persistence internals, without breaking the already deployed remote single-server production baseline.

## Next
- Execute the remaining migration in six waves and thirty atomic steps, keeping each wave green locally first and then remote-safe through backup, rollout, smoke verification, and rollback discipline.

## 30-Step Plan
### Wave 1: Remove Remaining Shared Helper Coupling
1. Freeze the current remote production baseline: record active systemd units, nginx routing, env-file locations, PostgreSQL backup path, and the exact smoke checks that must stay green after every rollout.
2. Freeze the remaining `platform-sdk -> services.*` dependency inventory and lock the target ownership list for each helper module.
3. Move `quick_memory_schedule` logic into `platform-sdk` support modules and repoint AI and learning-core callers.
4. Move `study_sessions` helper logic into service-local or shared support modules and remove monolith helper imports from split services.
5. Move `learning_events` recording behind a service-local event adapter so split services stop depending on monolith event helper entrypoints.

### Wave 2: Finish Notes and AI Shared Support Extraction
6. Move `learner_profile` and `learning_stats_service` composition helpers behind explicit service-local application modules.
7. Move `notes_summary_runtime` into `platform-sdk` and keep notes job progress and streaming behavior unchanged.
8. Move `notes_summary_service_parts` parsing, prompt-building, persistence, and job-serialization helpers into `platform-sdk`.
9. Isolate `llm` access behind explicit provider adapter boundaries so split services no longer bind directly to monolith-facing helper modules.
10. Re-run the AI, notes, auth, learning, admin, and gateway regression packs, then execute the same smoke flow against the deployed remote chain before closing the wave.

### Wave 3: Split Shared Repository and Model Ownership
11. Create service-owned repository modules for `identity`, `learning-core`, `catalog-content`, `ai-execution`, `notes`, `tts-media`, `asr`, and `admin-ops`.
12. Split shared SQLAlchemy model declarations into service-owned model packages with clear table ownership.
13. Remove cross-service repository imports from application layers and replace them with owned repositories or explicit downstream calls.
14. Make each service bootstrap only its owned models and tables instead of touching the global ORM set.
15. Generate an initial migration baseline per service and verify bootstrap plus migration commands against both local PostgreSQL and the remote deployment runbook.

### Wave 4: Close Data-Boundary and Storage Gaps
16. Audit every current table against authoritative service ownership and mark all non-owning access as read-only or transitional.
17. Disable new writes to shared SQLite fallback paths for services that already have PostgreSQL ownership.
18. Finish converging media, exports, and temporary binary artifacts onto Aliyun OSS object references with no disk-primary fallback.
19. Add per-service backfill and repair scripts for PostgreSQL rows and OSS object metadata.
20. Run parity validation between legacy SQLite and the new service-owned PostgreSQL and OSS state, then rehearse the same migration and rollback flow for the deployed remote environment.

### Wave 5: Add Classical Microservice Infrastructure
21. Bring up local Redis runtime and shared service configuration for cache, rate-limit, and ephemeral session workloads.
22. Bring up the corresponding remote Redis runtime and bind the deployed services to it with no behavior regressions under nginx and systemd.
23. Bring up local and remote RabbitMQ runtime plus shared service configuration for asynchronous domain events and work queues.
24. Add transactional outbox support to write-owning services so event publication is durable and replayable.
25. Publish the first event contract set for `identity`, `learning`, `notes`, `tts`, and `ai-execution`, then rebuild admin and other cross-domain read models from events instead of shared table reads.

### Wave 6: Exit the Monolith
26. Add gateway timeout, retry, and circuit-breaker policy per downstream service.
27. Finalize ASR HTTP and Socket.IO deployment contracts, port docs, and reverse-proxy expectations for both local and remote runtime.
28. Make the split-service startup chain the default local backend path and align the remote systemd rollout path with the same contract.
29. Remove or archive monolith-only route registration, startup paths, and shared-SQLite runtime assumptions only after remote fallback and restart procedures are documented and tested.
30. Run the final cutover validation pack, confirm full frontend compatibility through `gateway-bff` on the deployed remote domain, and declare the split backend the canonical architecture.

## Risks
- The backend is already split at the process boundary, but shared repositories and shared ORM ownership still prevent it from being a fully classical microservice backend.
- Redis, RabbitMQ, outbox, and event-driven read models are not fully landed yet, so cross-service consistency still leans on shared database reads in some paths.
- `gateway-bff`, `nginx`, ASR Socket.IO, and the multi-port backend chain now exist in both local and remote environments, so startup ordering, proxy drift, and rollout mistakes can break a live deployed system instead of only a local dev stack.
- The remote deployment is a single-server production baseline rather than the final Kubernetes form, so every remaining migration step needs backward-compatible rollout and rollback discipline before the architecture evolves again.
- AI, notes, and learner-profile flows still contain some deep shared helper and provider-adapter coupling; these are the most likely areas to cause regressions during the next decoupling wave and therefore need remote smoke coverage before closure.
