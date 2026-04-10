# Domain Event Contracts

Last updated: 2026-04-10

## Purpose

Wave 5 introduces one shared contract registry for the first domain events that will move cross-service reads away from shared PostgreSQL shadow tables.

The checked-in contract registry lives in [domain_event_contracts.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/domain_event_contracts.py), and the shared outbox helpers live in [outbox_runtime.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/outbox_runtime.py).

## Contract Set

| Topic | Publisher | Consumers | Aggregate |
| --- | --- | --- | --- |
| `identity.user.registered` | `identity-service` | `admin-ops-service` | `user` |
| `learning.session.logged` | `learning-core-service` | `admin-ops-service`, `notes-service` | `study-session` |
| `learning.wrong_word.updated` | `learning-core-service` | `admin-ops-service`, `ai-execution-service` | `wrong-word` |
| `notes.summary.generated` | `notes-service` | `admin-ops-service`, `ai-execution-service` | `daily-summary` |
| `tts.media.generated` | `tts-media-service` | `admin-ops-service` | `tts-media` |
| `ai.prompt_run.completed` | `ai-execution-service` | `admin-ops-service`, `notes-service` | `prompt-run` |

## Persistence Pattern

Each service now has dedicated event tables in its own schema boundary:

- `<service>_outbox_events` stores unpublished or retryable events written in the same transaction as owned state changes.
- `<service>_inbox_events` stores consumer-side idempotency and processing status.
- `admin_projection_cursors` stores replay progress for admin read-side rebuilds.

The model declarations live in [eventing_models.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/model_definitions/eventing_models.py), and the service bootstrap plan is extended in [service_table_plan.py](/F:/enterprise-workspace/projects/ielts-vocab/packages/platform-sdk/platform_sdk/service_table_plan.py).

## Current Scope

This landing slice adds the durable table shape, contract registry, and helper functions for queueing, claiming, and idempotent inbox registration.

Still pending in the next slice:

- service-local publisher loops that drain outbox rows into RabbitMQ
- consumer workers that write inbox rows and advance service-local projections
- admin read-model rebuilds that stop reading shared learning and identity shadow tables directly
