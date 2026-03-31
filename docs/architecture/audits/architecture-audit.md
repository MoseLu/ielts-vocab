# Architecture Audit

> Architecture-focused audit items across security, scalability, and maintainability.

## Critical

### 1. Hard-coded JWT fallback secrets
- File: `backend/config.py`
- Risk: predictable fallback secrets allow forged JWTs when env vars are missing.
- Fix: remove `or '...'` fallback and fail startup if secrets are absent.

### 2. WebSocket CORS allows all origins
- File: `backend/app.py`
- Risk: REST is restricted but Socket.IO is open to every origin.
- Fix: align Socket.IO CORS with `app.config['CORS_ORIGINS']`.

### 3. Default admin password created in app startup
- File: `backend/app.py`
- Risk: weak bootstrap credential is effectively documented in code/logs.
- Fix: use env-provided bootstrap credential or move to manual init flow.

## High Risk

### 4. Email verification endpoints lack rate limiting
- File: `backend/routes/auth.py`
- Risk: brute-force on short verification codes.
- Fix: apply the same rate limiting used by login plus per-code attempt limits.

### 5. In-memory rate limiting breaks under multi-process deployment
- File: `backend/routes/auth.py`
- Risk: each worker has its own bucket state.
- Fix: move to Redis-backed rate limiting.

### 6. Refresh token theft handling is too weak
- File: `backend/routes/auth.py`
- Risk: replay detection only rejects one request, leaving active access tokens alive.
- Fix: revoke all active tokens for the user and emit a security alert.

### 7. Access token lifetime is too long
- File: `backend/config.py`
- Risk: leaked access tokens remain valid for too long.
- Fix: shorten token lifetime and use silent refresh.

## Medium Risk

### 8. Email sending is still mocked
- File: `backend/routes/auth.py`
- Risk: production verification and reset flows silently fail.
- Fix: integrate a real provider and return explicit failures.

### 9. Multiple frontend `JSON.parse` paths bypass Zod
- File: `src/hooks/useAIChat.ts`
- Risk: corrupt localStorage data can break runtime assumptions.
- Fix: unify storage reads through validated helpers.

### 10. Email validation is too weak
- File: `backend/routes/auth.py`
- Risk: invalid addresses pass basic checks.
- Fix: use `email-validator` or equivalent strict validation.

### 11. `apiFetch` has no request timeout
- File: `src/lib/index.ts`
- Risk: hung requests stall UI indefinitely.
- Fix: add timeout support via `AbortSignal.timeout(...)`.

### 12. Production build exposes sourcemaps
- File: `vite.config.js`
- Risk: source is disclosed in production bundles.
- Fix: disable production sourcemaps or switch to hidden sourcemaps.

### 13. Verbose Flask/Socket.IO logging is enabled
- File: `backend/app.py`
- Risk: sensitive request or path information may leak into logs.
- Fix: enable only in debug builds.

### 14. No global request body size limit
- File: `backend/config.py` / `backend/app.py`
- Risk: oversized payload DoS.
- Fix: configure `MAX_CONTENT_LENGTH`.

## Low Risk / Structural

### 15. `AIChatContext` uses module-level mutable state
- File: `src/contexts/AIChatContext.tsx`
- Risk: React state flow is bypassed.
- Fix: move to reducer/context or a dedicated state library.

### 16. Database migrations are handwritten in startup flow
- File: `backend/app.py`
- Risk: no rollback/versioning discipline.
- Fix: adopt Alembic.

### 17. SQLite is not suitable for production concurrency
- File: `backend/config.py`
- Risk: file locks and poor scaling under write-heavy load.
- Fix: keep SQLite for dev, migrate production to PostgreSQL.

### 18. Token revocation checks always hit the database
- File: `backend/models.py`
- Risk: revocation reads add load to every authenticated request.
- Fix: cache revocation state in Redis with TTL.

### 19. AI context is rebuilt on every call
- File: `src/hooks/useAIChat.ts`
- Risk: repeated localStorage parsing and unnecessary recompute.
- Fix: memoize or cache aggregated context.

### 20. Entire vocabulary pool is loaded into memory
- File: `backend/routes/ai.py`
- Risk: linear memory growth and duplicated worker memory.
- Fix: query/index selectively or page high-frequency subsets.

### 21. LLM responses are not cached
- File: `backend/routes/ai.py`
- Risk: repeated identical greeting/context calls waste API budget.
- Fix: cache low-variance outputs by `(user_id, book_id, day)`.

### 22. No account deletion endpoint
- Risk: compliance gap for user data deletion.
- Fix: add account deletion/deactivation flow.

### 23. Learning context is sent to third-party LLMs in clear form
- File: `src/hooks/useAIChat.ts`
- Risk: privacy exposure.
- Fix: disclose, anonymize, or allow users to disable enhanced context.

## Priority Summary

| Priority | Focus |
| --- | --- |
| P0 | #1, #2, #3 |
| P1 | #4, #12, #14 |
| P2 | #8, #9, #11 |
| P3 | #5, #16, #17 |
| P4 | #15, #19, #21 |
