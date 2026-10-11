# Frontend Boundary Architecture

Last updated: 2026-05-07

## Core Rule

Use directories as ownership boundaries, files as capability wrappers, and small adapters to hide routing, transport, storage, env, and platform details.

## Current Framework Map

- Web app: React 19, React Router, Vite, TypeScript, SCSS.
- Mobile app: React Native under `apps/mobile`.
- Shared client core: `packages/app-core`, used by mobile today and eligible for web/mobile shared business logic.
- Package manager: pnpm workspace.

## Target Dependency Direction

```text
frontend/src/app
  -> frontend/src/components/<domain>/page
  -> frontend/src/composables/<domain>
  -> frontend/src/features/<domain>
  -> frontend/src/lib
  -> frontend/src/components/ui
```

Rules:

- `app` owns router, providers, shell policy, route guards, route-level preload, and app-wide error boundaries.
- `components/ui` owns primitive UI only. It must not import routes, features, contexts, data clients, or domain stores.
- `components/<domain>/page` owns page composition and visual structure.
- `composables/<domain>` owns page orchestration, effects, navigation decisions, and view-model state.
- `features/<domain>` owns reusable business services, schemas, stores, and cross-route domain hooks.
- `lib` owns low-level adapters and pure helpers. Domain-heavy logic should move to `features/<domain>`.
- `styles` is a single SCSS entry with layered import order: base, layout, components, pages, utils.

## Route Boundary

Route modules should stay thin.

Allowed in `app`:

- Route table and lazy page imports.
- Auth and guest guards.
- Shell/chrome visibility policy.
- Route-level redirects and legacy URL compatibility.
- Route-level asset preload adapters.

Not allowed in `app`:

- Feature API calls.
- Local storage reads and writes for domain state.
- Page-specific business derivation beyond route parameter normalization.

Current route refactor baseline:

- `AppRoutes.tsx` remains the route table and shell composition point.
- `PracticeRouteElement.tsx` owns practice query-mode compatibility and legacy `mode=game` redirect.
- `GameRouteElement.tsx` owns game theme route parameter adaptation.
- `routeGuards.tsx` owns guest/auth wrappers.
- `routeAssetsPreload.ts` owns game route image preloads.

## Data And Storage Boundary

Raw `apiFetch`, `apiRequest`, `fetch`, `localStorage`, `sessionStorage`, `import.meta.env`, and platform storage must be behind adapters.

Preferred placement:

- Transport and auth refresh: `lib/apiClient` or existing `lib/index` until split.
- Web storage helpers: `lib/storage` or feature-owned storage adapters.
- Domain endpoint functions: `features/<domain>/services`.
- Page data orchestration: `composables/<domain>/page`.
- Runtime schemas: `features/<domain>/schemas` or `lib/schemas` for cross-domain contracts.

Migration rule:

- Do not add new API calls directly in `components`.
- When touching an existing component API call, move that call to the nearest feature service or page composable if the change scope allows.
- Do not add new untyped `JSON.parse(localStorage...)` call sites. Add typed storage helpers near the owning domain.

## Practice And Game Boundary

Foundational practice and advanced game are product siblings, not one nested feature.

- Foundational practice owns `smart`, `listening`, `meaning`, `dictation`, `follow`, `radio`, `quickmemory`, and wrong-word recovery.
- Game owns five-dimension campaign map, mission UI, AI speaking assessment, and game progression.
- Shared answer/result concepts should move to `features/practice` or `packages/app-core` before both web and mobile depend on them.
- Reusable practice services now live under `features/practice`: progress storage, learner profile derivation, session helpers, confusable-match logic, audio services, word playback settings, and game-mode data helpers.
- Keep `components/practice/page/game-mode` focused on visual game composition. Put campaign labels, answer builders, game scope construction, and audio command helpers in `features/practice/gameMode`.
- Keep component wrappers for legacy import paths only when they preserve existing tests or callers during an incremental migration. New feature code should not import from `components/practice`.

## Mobile And Shared Core Boundary

Mobile should depend on `packages/app-core` for platform-neutral contracts.

Preferred direction:

```text
apps/mobile/screens -> apps/mobile/hooks/services -> packages/app-core
frontend/src/...    -> frontend feature services -> packages/app-core only when logic is platform-neutral
```

Rules:

- Keep React Native UI, native modules, AsyncStorage wiring, and navigation in `apps/mobile`.
- Keep schemas, API client primitives, auth/session contracts, and practice engine helpers in `packages/app-core`.
- Do not import web `frontend/src` modules from mobile.

## File Size Rule

- New hand-edited text files must stay at or below 500 lines.
- Start extraction around 350-400 lines when a file has multiple responsibilities.
- Split by responsibility, not by arbitrary line count.
- Existing 450+ line files are priority candidates when touched.

## Review Checklist

- Does this file live at the narrowest stable ownership boundary?
- Does the file name describe its capability?
- Does dependency direction still flow from route/page to feature/lib/ui?
- Are raw endpoint strings, storage keys, env reads, and platform APIs hidden behind adapters?
- Are UI primitives free of business and network concerns?
- Are route-private helpers kept in `app` instead of shared folders?
- Are feature-private helpers imported only through a narrow public API when crossing domains?
- Did the change keep line limits, lint, and focused tests green?
