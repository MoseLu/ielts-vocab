# Multi-Client Monorepo Architecture

Last updated: 2026-05-07

## Decision

Keep this project as a single monorepo. Do not split Web, Android, iOS, backend, or future mini-program clients into Git submodules by default.

Use the repository layout as the ownership boundary:

- `frontend/`: Web client.
- `apps/mobile/`: React Native Android and iOS client.
- `apps/miniprogram/`: future WeChat mini-program client, created only when that work starts.
- `apps/ios/`: future native Swift iOS client, created only if React Native is no longer the iOS path.
- `packages/app-core/`: platform-neutral client contracts, schemas, API clients, practice logic, and storage abstractions.
- `backend/`, `services/`, and `apps/gateway-bff/`: backend APIs, split services, and browser API ingress.

## Code Boundaries

- Put reusable client business logic in `packages/app-core`.
- Keep platform capabilities inside each app: Web cookies and browser storage in `frontend`, React Native native modules and AsyncStorage wiring in `apps/mobile`, and future mini-program request/storage/login adapters in `apps/miniprogram`.
- Do not force UI sharing across Web, React Native, and mini-program surfaces. Share pure data contracts or design-token values only when they remain platform-neutral.
- Keep backend API contracts platform-agnostic. Avoid request or response shapes that only make sense for one client unless the endpoint itself is client-specific.
- Do not import `frontend/src` modules from mobile or future mini-program code.

## Git And Commit Rules

- Commit by feature boundary, not by platform boundary.
- Single-client UI changes should touch only that app.
- Cross-client capability changes should include `packages/app-core` plus the affected app adapters in the same commit.
- Backend contract changes should include backend/API schema updates plus at least one verified client caller.
- Reconsider a split repository or submodule only if a client needs separate access control, a fully independent release process, or private code separation.

## Verification

Before submitting mobile or shared-client changes, run:

```bash
pnpm verify:clients
```

For narrower checks, use:

```bash
pnpm mobile:typecheck
pnpm mobile:test
pnpm app-core:typecheck
pnpm app-core:test
```

When a future mini-program app is added, add root scripts for `miniprogram:typecheck` and `miniprogram:test`, then include them in `verify:clients`.
