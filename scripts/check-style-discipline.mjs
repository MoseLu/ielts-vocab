import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const rootDir = process.cwd()
const frontendDir = 'frontend'

function frontendAwarePath(relativePath) {
  if (relativePath === 'src' || relativePath.startsWith('src/')) {
    return path.posix.join(frontendDir, relativePath)
  }
  return relativePath
}

function read(relativePath) {
  return readFileSync(path.join(rootDir, frontendAwarePath(relativePath)), 'utf8')
}

function listScssFiles(relativeDir) {
  const displayDir = frontendAwarePath(relativeDir)
  const absoluteDir = path.join(rootDir, displayDir)
  const entries = readdirSync(absoluteDir, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const relativePath = path.join(displayDir, entry.name).replace(/\\/g, '/')
    if (entry.isDirectory()) {
      files.push(...listScssFiles(relativePath))
      continue
    }
    if (entry.isFile() && relativePath.endsWith('.scss')) {
      files.push(relativePath)
    }
  }

  return files
}

function reportFailure(errors, relativePath, message) {
  errors.push(`${frontendAwarePath(relativePath)}: ${message}`)
}

const errors = []

const sharedUiFiles = [
  'src/components/ui/Button.tsx',
  'src/components/ui/Card.tsx',
  'src/components/ui/Input.tsx',
  'src/components/ui/Modal.tsx',
  'src/components/layout/MainLayout.tsx',
]

const utilityPattern = /\b(?:inline-flex|items-center|justify-center|rounded-(?:[a-z0-9[\]-]+)|bg-[a-z]|px-\d|py-\d|min-h-\d|text-(?:sm|base|lg)|focus:ring|hover:|shadow-\[|max-w-(?:sm|md|lg|xl|4xl)|min-h-screen)\b/

for (const relativePath of sharedUiFiles) {
  const content = read(relativePath)
  if (utilityPattern.test(content)) {
    reportFailure(errors, relativePath, 'shared UI primitives must use SCSS/token classes instead of utility-style class strings')
  }
}

const overlayFiles = [
  'src/styles/components/avatar.scss',
  'src/styles/components/scrollbar.scss',
  'src/styles/components/settings.scss',
  'src/styles/components/toast.scss',
  'src/styles/components/dropdowns.scss',
  'src/styles/components/popover.scss',
  'src/styles/layout/header-base.scss',
  'src/styles/layout/app.scss',
  'src/styles/components/global-word-search.scss',
  'src/styles/pages/profile/index.scss',
  'src/styles/pages/admin/_users-table.scss',
  'src/styles/pages/ai-chat/_panel-shell.scss',
  'src/styles/pages/books/chapter-modal.scss',
  'src/styles/pages/books/plan-modal.scss',
  'src/styles/pages/practice/confusable/_cards-overlays.scss',
  'src/styles/pages/practice/practice-complete.scss',
  'src/styles/pages/practice/practice-layout.scss',
  'src/styles/pages/practice/practice-options.scss',
  'src/styles/pages/stats/_chart-legends-tooltips.scss',
  'src/styles/pages/stats/_learning-curve.scss',
  'src/styles/pages/practice/practice-wordlist.scss',
]

const hardcodedLayerPattern = /z-index:\s*-?\d{2,}/

for (const relativePath of overlayFiles) {
  const content = read(relativePath)
  if (hardcodedLayerPattern.test(content)) {
    reportFailure(errors, relativePath, 'shared overlays must use layer tokens instead of hard-coded multi-digit z-index values')
  }
}

const statsFiles = [
  'src/components/stats/statsPageCharts.tsx',
  'src/styles/pages/stats/_overview-cards.scss',
  'src/styles/pages/stats/_chart-legends-tooltips.scss',
]

const hardcodedStatsColorPattern = /#[0-9A-Fa-f]{3,8}\b|rgba\(255,\s*126,\s*54,\s*0\.10\)/

for (const relativePath of statsFiles) {
  const content = read(relativePath)
  if (hardcodedStatsColorPattern.test(content)) {
    reportFailure(errors, relativePath, 'stats charts and legends must consume chart tokens instead of hard-coded palette values')
  }
}

const pageStyleFiles = [
  'src/styles/components/navigation.scss',
  'src/styles/pages/admin/_dashboard-overview.scss',
  'src/styles/pages/admin/_users-table.scss',
  'src/styles/pages/admin/_user-detail-modal.scss',
  'src/styles/pages/ai-chat/_panel-shell.scss',
  'src/styles/pages/ai-chat/_interaction-controls.scss',
  'src/styles/pages/auth/index.scss',
  'src/styles/pages/books/vocab-book-grid.scss',
  'src/styles/pages/errors/index.scss',
  'src/styles/pages/journal/journal-markdown.scss',
  'src/styles/pages/journal/_workspace-shell.scss',
  'src/styles/pages/journal/_detail-panels.scss',
  'src/styles/pages/profile/index.scss',
  'src/styles/pages/special/index.scss',
  'src/styles/pages/stats/_review-breakdown.scss',
  'src/styles/pages/stats/_learning-curve.scss',
  'src/styles/pages/stats/_accuracy-review.scss',
  'src/styles/pages/study-center/_dashboard-panels.scss',
  'src/styles/pages/study-center/_guide-workflow.scss',
  'src/styles/pages/study-center/home-sections.scss',
  'src/styles/pages/practice/confusable/_board-layout.scss',
  'src/styles/pages/practice/confusable/_cards-overlays.scss',
  'src/styles/pages/practice/dictation/_input-example.scss',
  'src/styles/pages/practice/practice-radio.scss',
  'src/styles/pages/practice/practice-complete.scss',
  'src/styles/pages/practice/practice-layout.scss',
  'src/styles/pages/practice/practice-options.scss',
  'src/styles/pages/practice/practice-quickmemory.scss',
  'src/styles/pages/practice/practice-spelling.scss',
  'src/styles/pages/practice/practice-stage-guide.scss',
  'src/styles/pages/practice/practice-wordlist.scss',
  'src/styles/pages/vocab-test/index.scss',
  'src/styles/layout/header-selectors.scss',
  'src/styles/pages/books/chapter-modal.scss',
  'src/styles/pages/books/plan-modal.scss',
  'src/styles/utils/utilities.scss',
]

const pageHardcodedColorPattern = /#[0-9A-Fa-f]{3,8}\b|color:\s*white\b|var\(--danger\)|color-mix\([^\n]*white/

for (const relativePath of pageStyleFiles) {
  const content = read(relativePath)
  if (pageHardcodedColorPattern.test(content)) {
    reportFailure(errors, relativePath, 'page styles in the cleanup set must use tokens instead of hard-coded colors or undefined danger aliases')
  }
}

const tokenSourceRootFiles = new Set([
  frontendAwarePath('src/styles/base.scss'),
])

const allStyleFiles = listScssFiles('src/styles').filter((relativePath) => !tokenSourceRootFiles.has(relativePath))
const rawColorSourcePattern = /#[0-9A-Fa-f]{3,8}\b|color:\s*white\b|var\(--danger\)|color-mix\([^\n]*white|rgba\((?!var\()|rgb\((?!var\()|hsla?\(/
const anonymousPartFilePattern = /(?:^|\/)_?[a-z0-9-]*part-\d+\.scss$/i

for (const relativePath of allStyleFiles) {
  if (anonymousPartFilePattern.test(relativePath)) {
    reportFailure(errors, relativePath, 'style partial file names must be semantic and must not use anonymous part numbering')
  }
  const content = read(relativePath)
  if (rawColorSourcePattern.test(content)) {
    reportFailure(errors, relativePath, 'style files outside the base token layer must not introduce raw color literals or raw rgb/rgba/hsl values')
  }
}

const inlineStyleRules = [
  {
    relativePath: 'src/components/ui/Loading.tsx',
    pattern: /style=\{\{[^}]*\b(?:color|opacity)\b[^}]*\}\}/,
    message: 'loading visuals must live in SCSS instead of static inline color/opacity styles',
  },
  {
    relativePath: 'src/components/practice/page/PracticePageStates.tsx',
    pattern: /style=\{\{[^}]*\b(?:color|marginBottom)\b[^}]*\}\}/,
    message: 'practice completion copy must use SCSS classes instead of inline spacing/color styles',
  },
  {
    relativePath: 'src/components/practice/quick-memory/QuickMemoryCountdownRing.tsx',
    pattern: /style=\{\{[^}]*\btransition\b[^}]*\}\}/,
    message: 'countdown ring transitions must live in SCSS instead of inline styles',
  },
  {
    relativePath: 'src/components/profile/avatar/AvatarUpload.tsx',
    pattern: /fillStyle\s*=\s*['"]#/,
    message: 'avatar upload canvas fill should read from theme tokens instead of hard-coded fallback colors',
  },
]

for (const rule of inlineStyleRules) {
  const content = read(rule.relativePath)
  if (rule.pattern.test(content)) {
    reportFailure(errors, rule.relativePath, rule.message)
  }
}

const stylesIndex = read('src/styles/index.scss')
if (stylesIndex.includes("./layout/global-word-search.scss") || stylesIndex.includes("./layout/global-word-search-detail.scss")) {
  reportFailure(errors, 'src/styles/index.scss', 'global word search styles must load from the components layer, not layout')
}

if (errors.length > 0) {
  console.error('Style discipline check failed:\n')
  for (const error of errors) {
    console.error(`- ${error}`)
  }
  process.exit(1)
}

console.log('Style discipline check passed.')
