# Local Redis for Microservices

Last updated: 2026-04-11 23:51:32 +08:00

## Purpose

Wave 5 starts by adding one project-owned local Redis runtime for split-service cache, rate-limit, and ephemeral session workloads.

The current local baseline uses `127.0.0.1:56379` so Redis does not collide with a system-wide default `6379` instance.

## Shared Config Shape

Split services now resolve Redis config in this order:

1. `<SERVICE_PREFIX>_REDIS_URL`
2. generic `REDIS_URL`
3. `<SERVICE_PREFIX>_REDIS_HOST`, `_PORT`, `_DB`, `_PASSWORD`, `_SSL`
4. generic `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL`

The checked-in example file [backend/.env.microservices.local.example](/F:/enterprise-workspace/projects/ielts-vocab/backend/.env.microservices.local.example) now includes:

- shared host and port for the local Redis runtime
- one logical Redis DB index per split service
- a shared `REDIS_KEY_PREFIX`

## Current Workloads

The local Redis baseline is no longer only infrastructure scaffolding.

- `identity-service` auth/email throttling now uses `Redis-first` counters with database fallback for login, bind-email code, and forgot-password rate limits.
- `asr-service` now mirrors realtime session metadata into Redis with TTL-backed snapshots and active-session counting, while keeping WebSocket handles and queued audio in process-local memory.
- Those ASR snapshots now also carry bounded `partial_transcript` and `final_transcript` excerpts plus `last_event` / `transcript_updated_at`, and the Socket.IO runtime exposes `/internal/sessions/<session_id>` so operators can read the current Redis-first session snapshot during local debugging.

## Startup

Run the Redis runtime directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-redis-microservices.ps1
```

Or start the whole split backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-microservices.ps1
```

`start-microservices.ps1` now starts the local Redis runtime before bringing up the HTTP services unless `-SkipRedis` is passed.

## Binary Resolution

The Redis startup script resolves the server binary in this order:

1. `-RedisServerPath`
2. `REDIS_SERVER_PATH`
3. `redis-server` on `PATH`

If none are available, the script fails with a clear error instead of silently skipping Redis startup.

## Verification

The startup script performs a raw RESP `PING` check and waits for `+PONG`.

Expected local endpoint after startup:

```text
redis://127.0.0.1:56379/0
```
