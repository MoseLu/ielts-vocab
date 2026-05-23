# Changelog

All notable product, runtime, and operational changes are recorded here.

## [1.2.4] - 2026-05-23

### Fixed
- Kept Ebbinghaus due-review answers moving under browser storage pressure by bounding the practice-result outbox and making smart-mode plus quick-memory local writes quota-safe.
- Added the missing `user_practice_result_commands` ownership to the learning-core split schema so idempotent practice-attempt writes no longer fail when the service database is bootstrapped from migrations.
- Restored split projection closeout by verifying admin, notes, and AI projections against their canonical owner sources and adding a repair path that upserts missing rows and prunes stale derived projection keys.
- Preserved scoped quick-memory and wrong-word completion state across production-style learning-state repairs.

### Operations
- Released and verified the storage-pressure hotfix in production, including split-service schema migration, post-switch smoke, and learning-core log checks.
- Repaired production Wave 5 projection drift from the release path and completed release closeout successfully.

### Validation
- Verified focused backend schema, idempotency, projection, and release-closeout tests; frontend practice-result, smart-mode, and quick-memory quota tests; frontend lint; file-line guards; and production smoke/closeout.

## [1.2.3] - 2026-05-10

### Added
- Added the local Mac app launcher path, admin asset management dashboard, theme color preferences, and richer chapter progress charts.
- Refreshed the mobile study-room visuals and regenerated premium mnemonic data for the production vocabulary catalog.

### Fixed
- Recovered home book data after startup gaps and validated the relevant frontend recovery flows.

### Validation
- Verified focused frontend unit coverage and frontend build for the `v1.2.3` release line.

## [1.2.2] - 2026-05-07

### Fixed
- Removed the accidental `学习中心 · 今日计划` masthead from the study-center page and added a regression check so it does not return.
- Replaced user-visible development-environment verification-code messages with normal product copy in registration, password reset, and email binding flows.
- Removed internal `v1` wording from the mobile home screen subtitle.
- Hardened cold catalog search handling by isolating the search circuit breaker and serializing cold search catalog builds.

### Validation
- Verified file-line guards, frontend repo guards, focused home/auth tests, mobile tests, and targeted backend search/proxy tests.

## [1.2.1] - 2026-05-07

### Highlights
- Shipped the post-`v1.1.1` production line that stabilizes the split backend runtime, OSS-hosted frontend assets, practice result ingestion, and the foundational vocabulary learning loop.
- Kept foundational practice, Ebbinghaus review, wrong-word recovery, and learner statistics on the direct learning path, while leaving the five-dimension game and AI speaking work as an independent advanced mode family.
- Added the first mobile workspace scaffold and shared app-core package for future native client work.

### Learning And Practice
- Added an idempotent practice-result command/outbox flow so practice attempts carry stable metadata and can be retried without double-counting.
- Recorded Ebbinghaus review activity from foundational practice modes, including quick-memory review flows and due-review actions.
- Stabilized quick-memory review, restart, resume, queue pagination, cold-path lookup, audio playback, and local retry behavior.
- Preserved review word ordering and scoped resume snapshots across wrong-word, chapter, and quick-memory practice flows.
- Added chapter-group continuation controls and review-limit-aware grouping for chapter and wrong-word practice.
- Improved follow-read mode with pronunciation scoring, acoustic fallback, chunk audio support, segmentation refinements, and production style fixes.
- Unified practice audio playback and kept normal word audio on the standard track.

### Vocabulary, Books, And Word Detail
- Added protected custom-book export and synchronization flows for wrong words, including sorted word order, filtered selection actions, append/update support, and gateway timeout fixes.
- Hid legacy wrong-word system books from normal book lists and deduplicated wrong-word counts across catalog reads.
- Added premium word mnemonic catalogs, LLM and Qwen snapshot data, enrichment tooling, and regression coverage for premium memory notes.
- Added word-detail enrichment, selection lookup, arrow-key navigation, confusable lookup hardening, and direct word audio GET support in the gateway.
- Corrected phonetic audio entries and made favorite-word audio use phonetic override data.

### AI, Notes, And Learner Profile
- Added AI chat markdown rendering and supporting markdown styles.
- Added frontend error-log collection and backend ingestion for better production diagnosis.
- Added feature-wish APIs and profile modal support.
- Added AI home todos, daily learning rollup consistency fixes, learner-profile recommendation alignment, and session overlap guards.
- Hardened AI/custom-book schema fallback and added follow-read assessment fallback coverage.

### Game And UI
- Shipped the themed five-dimension game route family, campaign state, mission UI, map route split, HUD state, generated UI assets, and text-safe game templates.
- Moved game and frontend UI assets to OSS-backed delivery, including gzip/public-header handling and SPA directory fallback fixes.
- Polished study-center cards, vocab-test layout, follow practice layout, wrong-word pages, global word search, settings, mobile admin users table, and production game map controls.
- Added local web-vitals reporting and stabilized game theme cold startup.

### Backend And Runtime
- Advanced the split-service runtime with macOS local startup, grouped domain workers, low-memory consolidated runtime, slim service shells, readiness probes, and env-loading fixes.
- Added learning-activity truth rollups, backfill tools, daily ledger guards, cutover support, and unified practice-attempt facts.
- Added deadlock retry handling for learning-core practice writes and avoided request-time mastery table checks.
- Hardened catalog schema boundaries, split projection verification, admin projection smoke checks, and release-risk test gates.
- Added service schema migrations for custom book ordering, feature wishes, practice results, learning rollups, and related service-owned models.

### Release And Operations
- Switched production release flow toward single-release deployments with prebuilt artifacts, worker-aware service restarts, release health watchdogs, and safer rollback behavior.
- Added OSS frontend asset publishing from release artifacts, asset-base validation, and storage delivery hardening.
- Added broker/runtime validation, production preflight checks, deployment smoke checks, and CI release artifact streaming fixes.
- Added release closeout/storage drill hardening and production deploy-risk user journey coverage.
- Removed legacy Windows startup scripts and documented the mac-only local runtime baseline.

### Mobile
- Added `apps/mobile` React Native scaffold with Android/iOS project files, session context, storage, basic screens, navigation, API wiring, and native audio capture bridge placeholders.
- Added `packages/app-core` with shared API, auth, speech session, schemas, and storage helpers.

### Documentation
- Added practice mode data-flow documentation, practice result chain overhaul planning, mobile native PRD, premium mnemonic generation PRD, five-dimension game rollout notes, release submit logs, and local UI/API/browser test reports.

### Validation
- Verified the release line with file-line guards, frontend repo guards, focused frontend unit tests, focused backend pytest coverage, production preflight, and post-switch production smoke checks.
