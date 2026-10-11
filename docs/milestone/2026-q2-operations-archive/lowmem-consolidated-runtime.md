# Low-Memory Consolidated Runtime

Use this local runtime when the machine cannot comfortably keep the full split backend chain resident.

```bash
./start-lowmem.sh
```

This path is for constrained local development on small machines such as `2C4G`. It is not the cloud production topology and it does not replace the normal split startup.

## What Starts

- `backend/app.py` on `127.0.0.1:8000`
- `backend/speech_service.py` on `127.0.0.1:5001`
- `vite preview` on `127.0.0.1:3002`

The frontend keeps using the gateway-shaped API base at `:8000`, so browser code does not need a separate proxy profile.

## Boundary Rules

- Only the browser-facing compatibility surface is enabled.
- Rollback-only route groups, including the TTS admin drill surface, stay out of this runtime.
- `ALLOW_MONOLITH_COMPAT_RUNTIME=1` is still required because the low-memory process reuses the archived compatibility shell.
- `LOWMEM_CONSOLIDATED_RUNTIME=1` and `IELTS_BACKEND_RUNTIME_PROFILE=lowmem-consolidated` identify this as the resource-constrained profile in logs.
- `WAITRESS_THREADS` defaults to `4` when not set, matching the small-host target.

The goal is to reduce resident processes, not to weaken service ownership. Code-side boundaries remain enforced by the split-service contracts, table ownership plans, route-group manifest, and tests.

## When To Use

Use `./start-lowmem.sh` for:

- local UI checks on memory-limited machines
- quick manual verification where one API process is enough
- reproducing browser workflows without booting all HTTP services and workers

Use `./start-project.sh` for:

- normal local production-style split runtime
- domain-runtime bugs
- worker, Redis, RabbitMQ, or service-owned storage checks

Use `./start-monolith-compat.sh` only for:

- rollback drills
- explicit compatibility surface audits
- emergency operator validation of archived monolith routes

## Practical Checks

```bash
bash -n ./start-project.sh ./start-lowmem.sh
PATH=/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin:$PATH pytest backend/tests/test_split_runtime_contract.py -q
```
