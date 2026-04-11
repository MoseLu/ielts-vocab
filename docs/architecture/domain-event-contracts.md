# Domain Event Contracts

Last updated: 2026-04-11 13:48:35 +08:00

## Purpose

Wave 5 introduces one shared contract registry for the first domain events that will move cross-service reads away from shared PostgreSQL shadow tables.

The checked-in contract registry lives in [domain_event_contracts.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/domain_event_contracts.py), and the shared outbox helpers live in [outbox_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/outbox_runtime.py).

## Contract Set

| Topic | Publisher | Consumers | Aggregate |
| --- | --- | --- | --- |
| `identity.user.registered` | `identity-service` | `admin-ops-service` | `user` |
| `learning.session.logged` | `learning-core-service` | `admin-ops-service`, `notes-service` | `study-session` |
| `learning.wrong_word.updated` | `learning-core-service` | `admin-ops-service`, `ai-execution-service`, `notes-service` | `wrong-word` |
| `notes.summary.generated` | `notes-service` | `admin-ops-service`, `ai-execution-service` | `daily-summary` |
| `tts.media.generated` | `tts-media-service` | `admin-ops-service` | `tts-media` |
| `ai.prompt_run.completed` | `ai-execution-service` | `admin-ops-service`, `notes-service` | `prompt-run` |

## Persistence Pattern

Each service now has dedicated event tables in its own schema boundary:

- `<service>_outbox_events` stores unpublished or retryable events written in the same transaction as owned state changes.
- `<service>_inbox_events` stores consumer-side idempotency and processing status.
- `admin_projection_cursors` stores replay progress for admin read-side rebuilds.

The model declarations live in [eventing_models.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/model_definitions/eventing_models.py), and the service bootstrap plan is extended in [service_table_plan.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/service_table_plan.py).

Some publishers also materialize a service-owned write fact before queueing the event, such as `tts_media_assets` for TTS cache/materialization state and `ai_prompt_runs` for completed AI prompt executions. Some consumers also materialize service-owned read facts from subscribed events, such as `notes_projected_study_sessions`, `notes_projected_wrong_words`, and `notes_projected_prompt_runs` inside `notes-service`, and `ai_projected_wrong_words` plus `ai_projected_daily_summaries` inside `ai-execution-service`.

## Current Scope

The current local Wave 5 slice now includes live publisher workers for `identity`, `learning-core`, `notes`, `tts-media`, and `ai-execution`, plus `admin-ops-service` consumer workers that project user, study-session, wrong-word, daily-summary, prompt-run, and TTS-media read models from events. `notes-service` now consumes `learning.session.logged` into `notes_projected_study_sessions`, `learning.wrong_word.updated` into `notes_projected_wrong_words`, and `ai.prompt_run.completed` into `notes_projected_prompt_runs`, while `ai-execution-service` consumes `learning.wrong_word.updated` into `ai_projected_wrong_words` and `notes.summary.generated` into `ai_projected_daily_summaries`; notes summary prompt building, notes summary wrong-word context, AI wrong-word reads, and AI context summary fallback now all use those local projections.

Still pending in the next slice:

- remote RabbitMQ rollout and supervised worker startup in the deployed environment
- more shared-read retirement behind the now-landed local projections and internal contracts
- the remaining admin read-model rebuilds that still read shared learning, catalog, or identity shadow tables directly
