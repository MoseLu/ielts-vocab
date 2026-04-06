# Styles README

This directory is the single style entry for the frontend.

The root entry is:

- [index.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/index.scss)

Import order is fixed and must stay:

1. `base`
2. `layout`
3. `components`
4. `pages`
5. `utils`

## Directory rules

### `base/`

Base tokens, theme variables, reset, typography, spacing, radius, shadow, z-index.

Primary file:

- [base.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/base.scss)

When changing:

- Edit design tokens here first.
- Do not redefine global colors or spacing in page files if a token can be used.

### `layout/`

Global shell and navigation only.

Files:

- [app.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/layout/app.scss)
- [header-base.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/layout/header-base.scss)
- [header-selectors.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/layout/header-selectors.scss)

When changing:

- Use this layer for page shell, header, sidebar, bottom nav, shared page containers.
- Do not put feature-specific card/table styling here.

### `components/`

Reusable component styling.

Files:

- [avatar.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/avatar.scss)
- [complete.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/complete.scss)
- [dropdowns.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/dropdowns.scss)
- [empty-state.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/empty-state.scss)
- [global-word-search-detail.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/global-word-search-detail.scss)
- [global-word-search.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/global-word-search.scss)
- [popover.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/popover.scss)
- [scrollbar.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/scrollbar.scss)
- [settings.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/settings.scss)
- [toast.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/toast.scss)
- [ui-primitives.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/components/ui-primitives.scss)

When changing:

- If the same UI pattern appears on more than one page, move it here.
- Component styles should not know page route context.
- Shared UI primitives such as button, card, input, modal, and global search belong here instead of TSX utility strings or the `layout/` layer.

### `pages/`

Page composition and page-scoped visuals.

Current files:

- [admin.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/admin.scss)
- [ai-chat.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/ai-chat.scss)
- [auth.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/auth.scss)
- [chapter-modal.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/chapter-modal.scss)
- [day-card.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/day-card.scss)
- [errors.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/errors.scss)
- [home-banner.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/home-banner.scss)
- [home-sections.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/home-sections.scss)
- [journal.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/journal.scss)
- [plan-modal.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/plan-modal.scss)
- [practice-complete.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-complete.scss)
- [practice-dictation.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-dictation.scss)
- [practice-layout.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-layout.scss)
- [practice-options.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-options.scss)
- [practice-quickmemory.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-quickmemory.scss)
- [practice-radio.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-radio.scss)
- [practice-spelling.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-spelling.scss)
- [practice-wordlist.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-wordlist.scss)
- [profile.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/profile.scss)
- [stats.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/stats.scss)
- [study-center.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/study-center.scss)
- [vocab-book-grid.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/vocab-book-grid.scss)
- [vocab-cards.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/vocab-cards.scss)
- [vocab-filters.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/vocab-filters.scss)
- [vocab-test.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/vocab-test.scss)

When changing:

- Use this layer for page-only layout and visuals.
- Do not redefine tokens here.
- If a rule becomes shared, move it to `components` or `layout`.
- Page partial file names must describe the slice they own, for example `_dashboard-overview.scss`, `_learning-curve.scss`, `_user-detail-modal.scss`.
- Do not create anonymous sequence names such as `_part-1.scss`, `_part-2.scss`, or similar non-semantic numbering.

### `utils/`

Last-loaded utility layer.

Files:

- [\_mixins.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/utils/_mixins.scss)
- [utilities.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/utils/utilities.scss)
- [responsive.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/utils/responsive.scss)

When changing:

- Use for utility classes, helper states, and responsive overrides.
- Avoid feature-specific selectors here unless the rule is truly global.
- Put reusable SCSS mixins here when the same layout/panel/progress pattern appears across pages.

## Reuse-first SCSS rules

Before adding new page rules, check whether one of these existing mixins already fits:

- `page-stack`
- `page-shell-fill`
- `page-content-fill`
- `panel-surface`
- `toolbar-surface`
- `table-shell`
- `metric-card`
- `data-table-base`
- `data-table-head-cell`
- `data-table-body-cell`
- `control-button`
- `accent-button`
- `input-control`
- `pill-badge`
- `native-progress`
- `flex-center-column`

Current mixin entry:

- [\_mixins.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/utils/_mixins.scss)

Current pages already using them:

- [admin.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/admin.scss)
- [errors.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/errors.scss)
- [journal.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/journal.scss)
- [practice-complete.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/practice-complete.scss)
- [stats.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/stats.scss)
- [study-center.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/study-center.scss)
- [vocab-book-grid.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/vocab-book-grid.scss)
- [vocab-cards.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/pages/vocab-cards.scss)

## How to find the right file

If you want to change:

- Theme color, spacing, radius, shadow: start in [base.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/base.scss)
- Light/dark semantic surface tokens: start in [base.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/base.scss)
- Header, page shell, top-level spacing: start in [app.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/layout/app.scss) or [header-base.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/layout/header-base.scss)
- Reusable widget styling: check `components/`
- A single route/page look: check `pages/`
- Helper classes or last-layer overrides: check `utils/`

## Editing rules

- Do not reintroduce `index.css`.
- Do not use inline `style={{ ... }}` in TSX for normal visual styling.
- Prefer tokens over raw values.
- Outside [base.scss](/F:/enterprise-workspace/projects/ielts-vocab/src/styles/base.scss), do not introduce raw `#hex`, raw `rgb(...)` / `rgba(...)` / `hsl(...)`, `color: white`, or `color-mix(... white)`.
- If a themed page needs special colors, define page-scoped semantic CSS variables near the page root first, then consume those variables in descendants instead of scattering one-off color values.
- Prefer pure orange accent surfaces over gradients unless explicitly approved.
- Spacing rhythm is `10px` based unless a token defines otherwise.
- If a style needs dynamic geometry, prefer CSS variables set by refs over ad-hoc JSX inline styles.
- Dark theme should be driven by semantic tokens first. Prefer `surface-*`, `border-*`, `focus-ring`, `chart-*`, and `text-*` tokens over page-level `[data-theme="dark"]` overrides.
- Page-level `[data-theme="dark"]` overrides should be reserved for data-viz semantics or truly exceptional states; shared UI surfaces, inputs, dropdowns, modals, and buttons should inherit from the token layer automatically.
- When a page needs a toolbar, data shell, or metric card, reuse `toolbar-surface`, `table-shell`, and `metric-card` before adding a new page-specific container pattern.
- When a page needs table sizing or shared head/body cell treatment, start with `data-table-base`, `data-table-head-cell`, and `data-table-body-cell` instead of redefining table typography and cell padding locally.
- When a page needs buttons, inputs, or badges, start with `control-button`, `accent-button`, `input-control`, and `pill-badge` before adding route-specific variants.
