# Shared Aliyun OSS SDK

Last updated: 2026-04-09

## Purpose

Freeze the first reusable object-storage baseline for the microservice transition.

This implementation reuses the existing Aliyun OSS private bucket strategy instead of introducing a new object store.

## Source of Truth

- Shared SDK package: [packages/platform-sdk/platform_sdk/storage/aliyun_oss.py](../../../packages/platform-sdk/platform_sdk/storage/aliyun_oss.py)
- Backward-compatible TTS wrapper: [backend/services/word_tts_oss.py](../../../backend/services/word_tts_oss.py)
- Shared ASR runtime package: [packages/platform-sdk/platform_sdk/asr_runtime/__init__.py](../../../packages/platform-sdk/platform_sdk/asr_runtime/__init__.py)
- Shared learning-core runtime: [packages/platform-sdk/platform_sdk/learning_core_runtime.py](../../../packages/platform-sdk/platform_sdk/learning_core_runtime.py)
- Shared catalog-content runtime: [packages/platform-sdk/platform_sdk/catalog_content_runtime.py](../../../packages/platform-sdk/platform_sdk/catalog_content_runtime.py)
- Shared AI runtime: [packages/platform-sdk/platform_sdk/ai_runtime.py](../../../packages/platform-sdk/platform_sdk/ai_runtime.py)
- Shared notes runtime: [packages/platform-sdk/platform_sdk/notes_runtime.py](../../../packages/platform-sdk/platform_sdk/notes_runtime.py)
- Shared admin-ops runtime: [packages/platform-sdk/platform_sdk/admin_ops_runtime.py](../../../packages/platform-sdk/platform_sdk/admin_ops_runtime.py)

## Environment Variables

The shared SDK continues to use the existing environment names:

- `AXI_ALIYUN_OSS_ACCESS_KEY_ID`
- `AXI_ALIYUN_OSS_ACCESS_KEY_SECRET`
- `AXI_ALIYUN_OSS_STS_TOKEN`
- `AXI_ALIYUN_OSS_PRIVATE_BUCKET`
- `AXI_ALIYUN_OSS_REGION`
- `AXI_ALIYUN_OSS_ENDPOINT`

Word TTS keeps its current compatibility prefix knobs:

- `WORD_TTS_OSS_PREFIX`
- `WORD_TTS_OSS_SIGNED_URL_EXPIRES_SECONDS`
- `WORD_TTS_OSS_METADATA_CACHE_TTL_SECONDS`

Example-audio now has service-owned OSS knobs:

- `EXAMPLE_AUDIO_OSS_PREFIX`
- `EXAMPLE_AUDIO_OSS_SIGNED_URL_EXPIRES_SECONDS`
- `EXAMPLE_AUDIO_OSS_METADATA_CACHE_TTL_SECONDS`

Notes export now has service-owned OSS knobs:

- `NOTES_EXPORT_OSS_PREFIX`
- `NOTES_EXPORT_OSS_SIGNED_URL_EXPIRES_SECONDS`
- `NOTES_EXPORT_OSS_METADATA_CACHE_TTL_SECONDS`

## Object Rules

- Browser-facing media should continue to use signed URLs for private bucket access.
- Databases store object references and metadata, not the binary body.
- Shared metadata shape is:
  - `provider`
  - `bucket_name`
  - `object_key`
  - `content_type`
  - `byte_length`
  - `cache_key`
  - `signed_url`

## Object Key Strategy

New service-owned object keys should use service-prefixed namespaces:

- `tts-media-service/...`
- `asr-service/...`
- `notes-service/...`
- `exports/...`

Current word-TTS cache keeps its legacy prefix for compatibility:

- default prefix: `projects/ielts-vocab/word-tts-cache/...`

Example-audio now uses the service namespace by default:

- default prefix: `tts-media-service/example-audio/...`

## Current Service Skeletons

The following FastAPI scaffolds now exist and expose `/health`, `/ready`, and `/version`:

- [apps/gateway-bff/main.py](../../../apps/gateway-bff/main.py)
- [services/identity-service/main.py](../../../services/identity-service/main.py)
- [services/learning-core-service/main.py](../../../services/learning-core-service/main.py)
- [services/catalog-content-service/main.py](../../../services/catalog-content-service/main.py)
- [services/ai-execution-service/main.py](../../../services/ai-execution-service/main.py)
- [services/tts-media-service/main.py](../../../services/tts-media-service/main.py)
- [services/asr-service/main.py](../../../services/asr-service/main.py)
- [services/notes-service/main.py](../../../services/notes-service/main.py)
- [services/admin-ops-service/main.py](../../../services/admin-ops-service/main.py)

## Active Compatibility Slices

The browser-compatible gateway path has started to move real traffic away from the Flask monolith:

- `gateway-bff -> tts-media-service`
  - `/api/tts/voices`
  - `/api/tts/generate`
  - `/api/tts/word-audio`
  - `/api/tts/word-audio/metadata`
  - `/api/tts/example-audio`
- `gateway-bff -> asr-service`
  - `/api/speech/transcribe`
- `gateway-bff -> identity-service`
  - `/api/auth/register`
  - `/api/auth/login`
  - `/api/auth/refresh`
  - `/api/auth/logout`
  - `/api/auth/me`
  - `/api/auth/avatar`
  - `/api/auth/send-code`
  - `/api/auth/bind-email`
  - `/api/auth/forgot-password`
  - `/api/auth/reset-password`
- `gateway-bff -> learning-core-service`
  - `/api/progress`
  - `/api/progress/<day>`
  - `/api/books/progress`
  - `/api/books/progress/<book_id>`
  - `/api/books/<book_id>/chapters/progress`
  - `/api/books/<book_id>/chapters/<chapter_id>/progress`
  - `/api/books/<book_id>/chapters/<chapter_id>/mode-progress`
  - `/api/books/my`
  - `/api/books/my/<book_id>`
  - `/api/books/favorites`
  - `/api/books/favorites/status`
  - `/api/books/familiar`
  - `/api/books/familiar/status`
- `gateway-bff -> catalog-content-service`
  - `/api/books`
  - `/api/books/search`
  - `/api/books/categories`
  - `/api/books/levels`
  - `/api/books/stats`
  - `/api/books/examples`
  - `/api/books/word-details`
  - `/api/books/<book_id>`
  - `/api/books/<book_id>/chapters`
  - `/api/books/<book_id>/chapters/<chapter_id>`
  - `/api/books/<book_id>/words`
  - `/api/books/ielts_confusable_match/custom-chapters`
  - `/api/books/ielts_confusable_match/custom-chapters/<chapter_id>`
  - `/api/vocabulary`
  - `/api/vocabulary/day/<day>`
  - `/api/vocabulary/stats`
- `gateway-bff -> notes-service`
  - `/api/notes`
  - `/api/notes/summaries`
  - `/api/notes/summaries/generate`
  - `/api/notes/summaries/generate-jobs`
  - `/api/notes/summaries/generate-jobs/<job_id>`
  - `/api/notes/export`
  - `/api/books/word-details/note`
- `gateway-bff -> ai-execution-service`
  - `/api/ai/*`
  - includes `/api/ai/context`, `/api/ai/learner-profile`, `/api/ai/learning-stats`, `/api/ai/start-session`, `/api/ai/log-session`, `/api/ai/quick-memory/*`, `/api/ai/wrong-words*`, `/api/ai/ask`, `/api/ai/ask/stream`, and custom-book endpoints
- `gateway-bff -> admin-ops-service`
  - `/api/admin/overview`
  - `/api/admin/users`
  - `/api/admin/users/<user_id>`
  - `/api/admin/users/<user_id>/set-admin`

These compatibility routes preserve the existing browser-facing URLs while shifting implementation ownership into dedicated FastAPI services.

Realtime speech ownership has also moved out of `backend/speech_service.py`:

- New service entry: [services/asr-service/socketio_main.py](../../../services/asr-service/socketio_main.py)
- Shared runtime builder: [packages/platform-sdk/platform_sdk/asr_runtime/socketio_service.py](../../../packages/platform-sdk/platform_sdk/asr_runtime/socketio_service.py)
- Legacy compatibility shim: [backend/speech_service.py](../../../backend/speech_service.py)

Identity runtime ownership now follows the same pattern:

- Shared runtime builder: [platform_sdk/identity_runtime.py](../../../packages/platform-sdk/platform_sdk/identity_runtime.py)
- Service entry: [services/identity-service/main.py](../../../services/identity-service/main.py)

Learning-core runtime now follows the same compatibility pattern for user progress and book-library state:

- Shared runtime builder: [platform_sdk/learning_core_runtime.py](../../../packages/platform-sdk/platform_sdk/learning_core_runtime.py)
- Service entry: [services/learning-core-service/main.py](../../../services/learning-core-service/main.py)

Catalog-content runtime now owns the content-facing `books` and `vocabulary` compatibility routes:

- Shared runtime builder: [platform_sdk/catalog_content_runtime.py](../../../packages/platform-sdk/platform_sdk/catalog_content_runtime.py)
- Service entry: [services/catalog-content-service/main.py](../../../services/catalog-content-service/main.py)

Notes runtime now follows the same compatibility pattern for notes, summaries, and export flows:

- Shared runtime builder: [platform_sdk/notes_runtime.py](../../../packages/platform-sdk/platform_sdk/notes_runtime.py)
- Service entry: [services/notes-service/main.py](../../../services/notes-service/main.py)

Admin-ops runtime now owns the admin compatibility routes:

- Shared runtime builder: [platform_sdk/admin_ops_runtime.py](../../../packages/platform-sdk/platform_sdk/admin_ops_runtime.py)
- Service entry: [services/admin-ops-service/main.py](../../../services/admin-ops-service/main.py)

AI runtime now follows the same compatibility pattern for prompt helpers, learning context, wrong words, quick-memory sync, study sessions, and chat endpoints:

- Shared runtime builder: [platform_sdk/ai_runtime.py](../../../packages/platform-sdk/platform_sdk/ai_runtime.py)
- Service entry: [services/ai-execution-service/main.py](../../../services/ai-execution-service/main.py)

Gateway browser-compatible proxy routes are now centralized in:

- [platform_sdk/gateway_browser_routes.py](../../../packages/platform-sdk/platform_sdk/gateway_browser_routes.py)

The shared gateway proxy now preserves streaming `text/event-stream` responses so `/api/ai/ask/stream` can pass through `gateway-bff` without collapsing into a buffered JSON-style response.

`tts-media-service` example-audio now prefers OSS-backed object references on the split-service path:

- `/v1/media/example-audio/metadata` checks OSS first, then legacy local cache if needed
- `/v1/media/example-audio/content` serves OSS payloads when present and writes newly generated audio to OSS instead of treating local disk as the primary store
- [backfill_example_audio_to_oss.py](../../../scripts/backfill_example_audio_to_oss.py) uploads legacy `backend/tts_cache/*.mp3` files into the service-owned OSS namespace

`notes-service` export responses now also emit object references when OSS is configured:

- `/api/notes/export` still returns inline `content`, `filename`, and `format`
- the same response now includes `provider`, `bucket_name`, `object_key`, `byte_length`, `cache_key`, `signed_url`, and `signed_url_expires_at` when the export text is written to OSS
- default export namespace: `exports/notes-service/user-<id>/...`
