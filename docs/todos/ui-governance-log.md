# UI Governance Log

## 2026-03-30

- Fixed `src/styles/pages/vocab-book-grid.css`: `.vb-grid` gap is now `10px`.
- Fixed `src/styles/pages/journal.css`: removed remaining orange gradient styling and normalized the main spacing/radius values to the `10px` rhythm.
- Fixed `src/styles/pages/errors.css`: `.errors-empty` now stretches to the available page height and centers correctly.
- Continued round-two style governance:
  - `src/components/ChapterModal.tsx` and `src/styles/pages/chapter-modal.css` no longer use inline badge/progress styles.
  - `src/components/VocabTestPage.tsx` and `src/styles/pages/vocab-test.css` no longer use inline progress/ring/badge styles.
- Added shared empty-state infrastructure:
  - `src/components/ui/EmptyState.tsx` and `src/styles/components/empty-state.css` now provide reusable page/component empty states.
  - `src/components/ErrorsPage.tsx` now uses the shared empty state, and `src/styles/pages/errors.css` defines the correct parent height chain for true page-level centering.
- Journal rendering follow-up:
  - Removed the top-level `.journal-page .page-content` gap so section spacing is controlled by the section boxes themselves.
  - Added `src/lib/journalMarkdown.ts` to normalize compressed one-line markdown before rendering, then wired `src/components/LearningJournalPage.tsx` to use it for summaries and note answers.
  - Reworked the AI note record area in `src/styles/pages/journal.css` away from the old table layout into a two-column note card pattern, and deleted the stale responsive table rules that were no longer used.
- Large-file decomposition pass:
  - Split `src/components/StatsPage.tsx` into the `src/components/stats/` feature folder (`index.tsx`, `constants.ts`, `helpers.ts`, `pieCharts.tsx`, `ebbinghausChart.tsx`, `charts.tsx`) and left `src/components/StatsPage.tsx` as a thin entry file.
  - Audited remaining frontend files still above 500 lines: `src/components/practice/PracticePage.tsx`, `src/components/AdminDashboard.tsx`, `src/styles/pages/stats.css`, `src/styles/pages/admin.css`, `src/styles/pages/journal.css`, `src/components/practice/QuickMemoryMode.tsx`.
- Style-tree follow-up:
  - Re-audited frontend style usage and confirmed inline-style leakage still exists in `AdminDashboard`, `Header`, `StatsPage`, `AIChatPanel`, `Popover`, `Scrollbar`, `AvatarUpload`, and several practice subcomponents.
  - Installed `sass` and switched the frontend style entry from `src/styles/index.css` to `src/styles/index.scss` so the CSS-to-SCSS migration can proceed incrementally from a single root entry.
