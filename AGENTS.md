# Project Notes
Last updated: 2026-04-04 22:11:58 +08:00

## Repo Summary
- IELTS vocabulary learning web app with React 19 + TypeScript + Vite on the frontend and Flask + SQLite on the backend.
- Main scopes: `src/` for product UI and learning flows, `backend/` for APIs and persistence, `vocabulary_data/` for book assets, and `docs/` for durable plans, audits, and runbooks.
- Runtime now has three local entry points: preview UI on `3002`, main API on `5000`, and speech Socket.IO service on `5001`.

## Working Agreements
- Treat repo text files as UTF-8 unless the file itself proves otherwise.
- Before using `apply_patch`, read exact target lines and anchor on stable ASCII or code structure.
- If a file shows encoding corruption, rewrite the whole logical block instead of stacking small mojibake patches.
- Keep tracked hand-edited text files at `<= 500` lines unless they are covered by the checked-in oversize baseline.
- Treat `vocabulary_data/**`, `package-lock.json`, and `pnpm-lock.yaml` as generated artifacts that are exempt from the `500`-line cap.
- Keep `npm run check:file-lines` and `npm run lint` green before submit; `npm run build` and `npm test` now run the guardrail bundle automatically.
- Keep `pytest backend/tests/test_source_text_integrity.py -q` green after backend or text-heavy edits.
- Treat the local production-style chain as canonical for runtime bugs: `natapp -> nginx(:80) -> vite preview(:3002)` for UI, `/api` to Flask `:5000`, and `/socket.io` to speech service `:5001`.
- When touching runtime startup, keep `start-project.bat` and `start-project.ps1` aligned with `vite.config.ts`, `nginx.conf.example`, and the real service ports.

## Current Focus
- Keep production-style local startup and proxy behavior stable after the speech-service split.
- Keep Ebbinghaus due-review counts consistent across stats, learner profile, and review queue by using the same UTC-safe time conversion path.
- Continue study-center and homepage visual polish without regressing desktop/mobile layout.

## Latest Sync Notes
- Split speech handling out of the main Flask app into `backend/speech_service.py` on port `5001`, and updated proxy/startup flow accordingly.
- Added quick-memory reconciliation before learning-stats fetches so newer local records reach the backend before dashboard reads.
- Fixed the due-review timezone skew that undercounted recently due words in `learning-stats` and `learner-profile`.
- The current working tree includes an uncommitted homepage hero background polish in `src/styles/pages/study-center.scss`.

## Encoding & Patch Strategy
- Assume repo text files are UTF-8 unless the file itself proves otherwise.
- Before using `apply_patch`, read the exact target lines with line numbers and anchor on nearby clean ASCII or stable code structure.
- Prefer patching whole logical blocks over matching a single suspicious line when a file shows any text corruption.
- If `apply_patch` fails to match twice on the same area, stop matching the mojibake literally. Re-anchor on clean surrounding code, or rewrite the full function/component/doc block instead.
- Do not keep stacking partial edits onto a file that shows encoding corruption. Restore or re-read a clean base first, then replay the intended change.
- After any encoding-related fix, inspect the diff and confirm the file did not pick up unrelated text corruption.
- Keep the text-integrity regression green: `pytest backend/tests/test_source_text_integrity.py -q`.

## File Line Guardrail
- The hard cap is `500` lines for tracked hand-edited text files across app code, backend code, tests, scripts, docs, and config.
- `vocabulary_data/**`, `package-lock.json`, and `pnpm-lock.yaml` are explicitly exempt because they are generated data or lockfiles.
- Historical oversize files are frozen in `scripts/file-line-limit.config.json`. They are temporary exceptions, may not grow past their recorded baseline, and should be split down over time.
- `scripts/check-file-line-limits.mjs` is the enforcement gate. It fails when a new oversize file appears, when a baseline file grows, or when the baseline file is not cleaned up after a file drops back to `<= 500` lines.
- `eslint.config.mjs` mirrors the `500`-line cap for tracked JS/TS files, while letting the oversize baseline remain temporarily exempt until those files are split.
- `.github/workflows/ci.yml` runs both the file-line script and ESLint explicitly before frontend tests/build so the rule is enforced in CI, not just locally.

## Technology Stack
- Frontend: React 19 + TypeScript + Vite
- Styling: SCSS + CSS variables
- Validation: Zod runtime schemas in `src/lib/schemas.ts`
- Backend: Python Flask + SQLite
- Auth: JWT + localStorage
- Realtime: Socket.IO / WebSocket for speech

## Project Structure
```text
src/
- app/                      # App router entry
- components/
  - ui/                     # Base UI components
  - layout/                 # Shared shell/layout pieces
  - practice/               # Practice feature components
- contexts/                 # Auth / Settings / Toast / AIChat
- features/
  - vocabulary/hooks/       # Data hooks for books, words, progress, stats
  - ai-chat/                # AI chat feature
  - speech/                 # Speech recognition feature
- hooks/                    # Shared hooks
- lib/                      # Schemas, helpers, sync logic, formatting
- styles/                   # Global and page SCSS

backend/
- app.py                    # Main Flask API on :5000
- speech_service.py         # Dedicated speech Socket.IO service on :5001
- models.py                 # Database models
- routes/                   # API route modules
- services/                 # Backend service logic
- tests/                    # Backend tests

docs/
- architecture/             # Specs and audits
- governance/               # Product and UI governance logs
- milestones/               # Durable delivery snapshots
- operations/               # Runbooks and operator docs
- planning/                 # Design and implementation plans
- logs/submit/              # Append-only submit records
```

## Zod Validation
- Schema location: `src/lib/schemas.ts`
- Validation utilities: `src/lib/validation.ts`
- Form hook: `src/lib/useForm.ts`
- Auth, settings, toast, AI chat, and vocabulary hooks all validate inputs or API payloads through Zod-backed helpers.

## Key Features
1. Authentication and user profile management
2. Vocabulary books, chapters, and progress tracking
3. Practice modes: `smart`, `listening`, `meaning`, `dictation`, `radio`, `quickmemory`, `errors`
4. Guided study homepage and learner-profile driven recommendations
5. AI assistant, journal, and daily summary flows
6. Dedicated speech recognition service and TTS tooling

## Backend API
- `/api/auth`: register, login, logout, avatar, current user
- `/api/books`: books, chapters, words, progress
- `/api/progress`: legacy day-based progress
- `/api/ai`: learning stats, learner profile, quick memory, AI assistant, practice helpers
- `/api/notes`: notes, summaries, exports
- `/api/tts`: TTS audio and generation state
- `/api/admin`: admin capabilities

## Development
```bash
# Frontend
npm install
npm run dev
npm run build
npm run preview

# Backend
cd backend
pip install -r requirements.txt
python app.py
python speech_service.py

# One-click local production-style startup
start-project.bat
```

## Local Proxy Topology
1. Vite preview serves the browser UI on `http://127.0.0.1:3002`
2. Local `nginx` listens on port `80` and proxies UI traffic to `3002`
3. `natapp` exposes `https://axiomaticworld.com` and forwards to local `:80`
4. `nginx` proxies `/api/*` to Flask on `127.0.0.1:5000`
5. `nginx` proxies `/socket.io/*` to the speech service on `127.0.0.1:5001`

When debugging domain issues, treat the whole chain as the deployment context instead of blaming only frontend code.

## Browser APIs
- `speechSynthesis`: pronunciation playback
- `localStorage`: auth, settings, progress, quick-memory caches
- `WebSocket` / Socket.IO: realtime speech recognition
