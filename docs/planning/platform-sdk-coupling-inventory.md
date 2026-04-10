# Platform SDK Coupling Inventory
Last updated: 2026-04-10 18:05:00 +08:00

## Purpose
- Freeze the remaining `packages/platform-sdk/platform_sdk -> backend/services/*` dependency surface before the next extraction wave.
- Lock the intended ownership target for each helper family so later refactors do not reintroduce broad service imports by accident.

## Baseline
- Inventory source: repository scan of `packages/platform-sdk/platform_sdk/**/*.py` for `from services` and `import services`.
- Baseline date: `2026-04-10`.
- This file is the reference for Wave 1 and Wave 2 decoupling work.

## Ownership Targets
| Helper family | Current service dependency shape | Target owner | Planned direction |
| --- | --- | --- | --- |
| Quick memory schedule | `services.quick_memory_schedule` | `platform-sdk` support | Move schedule math and normalization into `platform-sdk`, keep repository callbacks injected from service owners. |
| Study session helpers | `services.study_sessions` | `learning-core` service support | Split pure normalization/window helpers from persistence-backed session operations. |
| Learning event writes | `services.learning_events` | service-local event adapter | Route writes through explicit adapters first, then move to outbox publishing in Wave 5. |
| Learner profile composition | `services.learner_profile` | `ai-execution` and `notes` application support | Keep repository reads explicit and remove high-level orchestration imports from shared package code. |
| Learning stats composition | `services.learning_stats_service` | `learning-core` application layer | Preserve repository access, move payload composition into shared or service-owned application helpers. |
| Notes summary runtime | `services.notes_summary_runtime` | `platform-sdk` notes support | Extract job-state, streaming, and formatting helpers out of monolith service package. |
| Notes summary parts | `services.notes_summary_service` | `platform-sdk` notes support | Split parsing and prompt helpers from Flask route concerns. |
| LLM provider access | `services.llm` | provider adapter boundary | Replace direct imports with adapter interfaces for chat, search, and tool streaming. |
| Book catalog and structure reads | `services.books_*` | `catalog-content` and `learning-core` repositories | Later waves move these behind service-owned repository/application adapters. |
| Auth and admin repositories | `services.auth_*`, admin repositories | `identity-service` and `admin-ops-service` repositories | Keep repository imports explicit until service-owned packages are split in Wave 3. |

## Current Remaining Imports By Slice
### Wave 1 targets
- `platform_sdk.ai_assistant_tool_support`
  target: quick memory schedule constant only
- `platform_sdk.ai_learning_summary_support`
  target: quick memory schedule logic, later repository ownership split
- `platform_sdk.ai_progress_sync_application`
  target: quick memory schedule math, later learning event adapter split
- `platform_sdk.ai_session_application`
  target: quick memory schedule loading, later study-session helper split

### Wave 1 and Wave 2 follow-up
- `platform_sdk.ai_context_application`
  target: learner profile composition extraction
- `platform_sdk.ai_learning_stats_application`
  target: study session helper split plus learning-stats composition extraction
- `platform_sdk.ai_metric_support`
  target: learning event adapter
- `platform_sdk.ai_practice_speaking_application`
  target: learner profile composition plus learning event adapter
- `platform_sdk.ai_wrong_words_application`
  target: learning event adapter
- `platform_sdk.notes_summary_jobs_application`
  target: learner profile, notes summary runtime, notes summary service parts, llm adapter

### Service-owned repository dependencies still expected before Wave 3
- `platform_sdk.identity_*`
  target: `identity-service` repository package
- `platform_sdk.catalog_content_*`
  target: `catalog-content-service` repository package
- `platform_sdk.learning_core_*`
  target: `learning-core-service` repository package
- `platform_sdk.notes_*`
  target: `notes-service` repository package
- `platform_sdk.admin_*`
  target: `admin-ops-service` repository package

## Immediate Execution Order
1. Finish the `quick_memory_schedule` extraction and repoint `platform-sdk` callers.
2. Extract pure `study_sessions` helpers used by `platform-sdk`.
3. Introduce a thin learning-event adapter so `platform-sdk` no longer imports `services.learning_events`.
4. Move learner-profile and notes-summary orchestration helpers into shared support modules before touching repository ownership.
