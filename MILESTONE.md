# Milestone
Last updated: 2026-04-04 21:09:41 +08:00

## Current Milestone
- Stabilize the local production-style runtime and learning-stat consistency after the speech-service split, while finishing the last round of homepage and secondary-page polish.

## Completed
- Landed the Q1 platform foundation slice across learner profile, guided study, confusable practice, backup tooling, and the reorganized `docs/` structure.
- Split speech handling into a dedicated service on port `5001` and aligned `vite`, `nginx`, and one-click startup scripts with the new topology.
- Added quick-memory sync-before-stats behavior so local newer records no longer lag behind backend dashboard reads.
- Fixed the due-review timezone skew so `learning-stats`, `learner-profile`, and `quick-memory/review-queue` now agree on due counts.

## In Progress
- Homepage and study-center visual cleanup, including the current uncommitted hero background refinement.
- Local runtime smoothing for the `start-project` flow, hidden child-process launch, and proxy-chain verification.

## Next
- Finish phase 4 and phase 5 UI redesign QA for remaining secondary surfaces and mobile polish.
- Add or wire favicon/static asset handling so the deployed proxy chain stops returning fallback `404` for `/favicon.ico`.
- Restore or replace the missing repo-summary automation script so summary documents can sync deterministically instead of manually.

## Risks
- The local deployment chain spans `natapp`, `nginx`, Vite preview, Flask, and the speech service; any port or proxy drift causes immediate user-facing failures.
- The summary workflow referenced by the `summarize` skill is not checked into this repo right now, so documentation sync depends on manual review.
- The repository contains generated/runtime directories such as `dist/`, `logs/`, and test artifacts, which can hide real work if commit scope is not reviewed carefully.
