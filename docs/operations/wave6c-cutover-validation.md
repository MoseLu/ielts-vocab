# Wave 6C Cutover Validation

Wave 6C retires the monolith as the default browser path while keeping one explicit rollback drill.

## Canonical Local Startup

Use the split runtime by default:

```bash
./start-project.sh
```

This must produce the canonical chain:

- `vite preview :3002`
- `/api/* -> gateway-bff :8000`
- `gateway-bff -> services :8101-8108`
- `/socket.io/* -> asr-socketio :5001`

## Local Validation Pack

Run the canonical local startup, then validate the browser path:

```bash
pwsh ./scripts/validate-wave6c-cutover.ps1 -SkipRemote
```

That validation pack now also runs the browser-surface route coverage audit by default and prints a separate rollback-only summary. If you only want the route audit without HTTP smoke checks, you can run:

```bash
pwsh ./scripts/validate-wave6c-cutover.ps1 -SkipLocal -SkipRemote
```

Recommended guardrails before calling the cutover green:

```bash
pytest backend/tests/test_source_text_integrity.py -q
pnpm check:file-lines
pnpm lint
```

## Remote Validation Pack

After the deployed split backend is updated, verify both browser compatibility and service readiness:

```bash
pwsh ./scripts/validate-wave6c-cutover.ps1 -SkipLocal
```

The server-side release flow must still keep the stronger remote smoke script green:

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com bash /opt/ielts-vocab/current/scripts/cloud-deploy/smoke-check.sh
```

## Rollback Drill

The monolith is no longer the default local backend path. Use it only for an explicit rollback or compatibility drill:

```bash
./start-monolith-compat.sh
```

That wrapper starts:

- `backend/app.py :5000`
- `backend/speech_service.py :5001`
- `vite preview :3002` with `/api` pointed back to `:5000`

Direct `python app.py` or `python speech_service.py` is now blocked unless `ALLOW_MONOLITH_COMPAT_RUNTIME=1` is set explicitly. The wrapper sets that override for a controlled rollback drill.

If you need to rehearse retirement group by group, the wrapper also accepts a subset through `MONOLITH_COMPAT_ROUTE_GROUPS` or `--monolith-compat-route-groups`, for example `auth,books,tts`.

For the common presets, prefer the explicit surface switch instead of hand-writing group names:

```bash
./start-monolith-compat.sh --monolith-compat-surface rollback
./start-monolith-compat.sh --monolith-compat-surface browser
```

`rollback` currently resolves to the isolated `tts-admin` route group, while `browser` resolves to the archived browser-facing compatibility groups.

The startup wrapper now also switches the compatibility readiness canary with the selected surface. For `rollback`, the canary is `/api/tts/books-summary`, so a narrow `tts-admin` drill no longer waits on browser-only paths such as `/api/books/stats`.

If you need to run that rollback drill from an intentionally dirty Wave 6C working tree, use the explicit local-only override:

```bash
./start-monolith-compat.sh --monolith-compat-surface rollback --allow-dirty-compatibility-drill
```

That override only skips the Git clean-tree and remote-sync gate for the compatibility runtime drill. It must not become the normal split-runtime startup path.

If the local host cannot bind compatibility backend port `5000`, rerun the rollback drill on a different local port and point the validator at the same backend base:

```bash
./start-monolith-compat.sh --monolith-compat-surface rollback --allow-dirty-compatibility-drill --monolith-compat-backend-port 5050
pwsh ./scripts/validate-wave6c-rollback-drill.ps1 -LocalBackendBase http://127.0.0.1:5050
```

After the compatibility runtime is up, validate the local rollback path with the dedicated drill pack:

```bash
pwsh ./scripts/validate-wave6c-rollback-drill.ps1
```

That drill resolves the same compatibility surface preset, reuses the same probe path, and treats `401` / `403` / other non-`404` browser auth responses as proof that the archived route still exists behind the rollback surface.

Do not leave the compatibility path running as the normal local baseline after the drill.

## Compatibility Surface Audit

The remaining monolith browser route surface is now archived in one explicit manifest:

- [monolith_compat_manifest.py](../../backend/monolith_compat_manifest.py)

You can print the current compatibility route inventory as JSON with:

```bash
python ./scripts/describe-monolith-compat-surface.py
```

The current archived route groups are:

- `auth`
- `progress`
- `vocabulary`
- `speech`
- `books`
- `ai`
- `notes`
- `tts`
- `tts-admin`
- `admin`

Before retiring a compatibility group, compare the archived monolith `/api/*` surface against the current gateway `/api/*` surface:

```bash
python ./scripts/describe-monolith-route-coverage.py
python ./scripts/describe-monolith-route-coverage.py --json
python ./scripts/describe-monolith-route-coverage.py --surface all
python ./scripts/describe-monolith-route-coverage.py --surface rollback
```

The report is method-aware and normalizes Flask plus FastAPI path parameters so catch-all gateway proxies count as coverage where they really replace a legacy monolith route. By default it audits only the browser-facing compatibility surface, while `--surface all` or `--surface rollback` includes rollback-only groups such as `tts-admin`. Use it to separate:

- monolith route-methods already covered by `gateway-bff`
- monolith-only route-methods that still require compatibility runtime
- gateway-only route-methods that represent new split-runtime browser surface

After the latest archive split, normal browser-facing TTS endpoints stay in `tts`, while the remaining operator-only batch endpoints are isolated in `tts-admin` so they can be retired or replaced independently of frontend cutover.

`validate-wave6c-cutover.ps1` treats the browser-surface audit as a hard gate and only reports rollback-surface gaps as informational output, so `tts-admin` no longer blocks the main cutover validation result.

## Closure State

Wave 6C is now considered closed under this contract:

- Browser cutover is complete when `validate-wave6c-cutover.ps1` reports browser coverage `94/94`, local split-runtime smoke is green, and the remote domain smoke is green.
- `tts-admin` is intentionally retained as a rollback-only operator surface, not a browser-ingress requirement. It stays outside `gateway-bff` and frontend code paths.
- Compatibility runtime is no longer a normal local baseline. It exists only for rollback drills and emergency operator access, with the latest drill verified through `./start-monolith-compat.sh --monolith-compat-surface rollback` plus `pwsh ./scripts/validate-wave6c-rollback-drill.ps1`.
