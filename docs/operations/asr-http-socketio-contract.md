# ASR HTTP and Socket.IO Contract

Last updated: 2026-04-10

## Purpose

This document freezes the split runtime contract for speech features so local startup, nginx routing, and remote systemd rollout all treat HTTP transcription and realtime Socket.IO as two explicit surfaces.

## Runtime Surfaces

### HTTP transcription service

- Process: `services/asr-service/main.py`
- Service name: `asr-service`
- Local and remote port: `8106`
- Readiness endpoints:
  - `GET /health`
  - `GET /ready`
  - `GET /version`
- Browser ingress:
  - browser `POST /api/speech/transcribe`
  - `gateway-bff` forwards to `POST /v1/speech/transcribe`

### Realtime Socket.IO service

- Process: `services/asr-service/socketio_main.py`
- Runtime name in ops scripts: `asr-socketio`
- Local and remote port: `5001`
- Readiness endpoints:
  - `GET /health`
  - `GET /ready`
- Browser ingress:
  - browser `/socket.io/*`
  - reverse proxy forwards directly to `asr-socketio`
- Realtime namespace:
  - `/speech`

## Reverse-Proxy Expectations

### Local runtime

- `start-microservices.ps1` must launch both `asr-service` on `8106` and `asr-socketio` on `5001`.
- Local proxy behavior stays split:
  - `/api/*` goes to `gateway-bff` on `8000`
  - `/socket.io/*` goes directly to `asr-socketio` on `5001`
- `gateway-bff` must not proxy or terminate the realtime Socket.IO channel.

### Remote runtime

- systemd must keep both units active:
  - `ielts-service@asr-service`
  - `ielts-service@asr-socketio`
- nginx must keep the same split routing:
  - `https://axiomaticworld.com/api/*` -> `gateway-bff`
  - `https://axiomaticworld.com/socket.io/*` -> `127.0.0.1:5001`
- Rollout and rollback checks must treat `8106` and `5001` as separate readiness targets.

## Operational Rules

- HTTP transcription failures are governed by the gateway upstream timeout/retry/circuit-breaker policy for `asr-service`.
- Realtime Socket.IO traffic does not use gateway retries; reconnect behavior stays at the browser and Socket.IO transport layer.
- Any port or namespace change must be reflected together in:
  - `start-microservices.ps1`
  - `start-project.bat`
  - `start-project.ps1`
  - `nginx.conf.example`
  - remote systemd and nginx rollout docs

## Verification

- HTTP readiness: `http://127.0.0.1:8106/ready`
- Socket.IO readiness: `http://127.0.0.1:5001/ready`
- Browser upload path: `POST /api/speech/transcribe`
- Browser realtime path: `/socket.io/?EIO=4&transport=polling`
