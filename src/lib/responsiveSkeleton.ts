interface AutoFitColumnsOptions {
  containerWidth: number
  minColumnWidth: number
  gap?: number
}

interface PageSkeletonCountOptions {
  viewportWidth: number
  minColumnWidth: number
  gap?: number
  containerWidth?: number
}

interface ChapterModalSkeletonCountOptions {
  viewportWidth: number
  bodyHeight: number
  rowMinHeight?: number
  gap?: number
  maxRows?: number
}

const DESKTOP_SIDEBAR_WIDTH = 160
const PAGE_GUTTER = 10
const MOBILE_BREAKPOINT = 768

export function estimateMainContentWidth(viewportWidth: number): number {
  const safeViewportWidth = Math.max(viewportWidth, 0)
  const sidebarOffset = safeViewportWidth > MOBILE_BREAKPOINT ? DESKTOP_SIDEBAR_WIDTH : 0
  const estimatedWidth = safeViewportWidth - sidebarOffset - PAGE_GUTTER * 2

  return Math.max(estimatedWidth, PAGE_GUTTER * 2)
}

export function calculateAutoFitColumns({
  containerWidth,
  minColumnWidth,
  gap = 10,
}: AutoFitColumnsOptions): number {
  if (containerWidth <= 0 || minColumnWidth <= 0) {
    return 1
  }

  return Math.max(1, Math.floor((containerWidth + gap) / (minColumnWidth + gap)))
}

export function calculatePageSkeletonCount({
  viewportWidth,
  minColumnWidth,
  gap = 10,
  containerWidth,
}: PageSkeletonCountOptions): number {
  const resolvedWidth = containerWidth && containerWidth > 0
    ? containerWidth
    : estimateMainContentWidth(viewportWidth)

  return calculateAutoFitColumns({
    containerWidth: resolvedWidth,
    minColumnWidth,
    gap,
  })
}

export function resolveChapterGridColumns(viewportWidth: number): number {
  if (viewportWidth <= 680) return 2
  if (viewportWidth <= 900) return 3
  return 4
}

export function estimateChapterModalBodyHeight(viewportHeight: number): number {
  const modalHeight = Math.min(Math.floor(viewportHeight * 0.86), 880)
  const headerHeight = 96
  const bodyPadding = 20

  return Math.max(modalHeight - headerHeight - bodyPadding, 166)
}

export function calculateChapterModalSkeletonCount({
  viewportWidth,
  bodyHeight,
  rowMinHeight = 156,
  gap = 10,
  maxRows = 3,
}: ChapterModalSkeletonCountOptions): number {
  const columns = resolveChapterGridColumns(viewportWidth)
  const visibleRows = Math.max(1, Math.floor((bodyHeight + gap) / (rowMinHeight + gap)))
  const rows = Math.min(visibleRows, maxRows)

  return columns * rows
}
