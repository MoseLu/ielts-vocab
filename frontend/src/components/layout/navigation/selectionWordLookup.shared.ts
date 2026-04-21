import type { WordDetailResponse, WordSearchResult } from '../../../lib'

export const SELECTION_LOOKUP_PANEL_CLASS = 'selection-word-lookup'
export const SELECTION_LOOKUP_PANEL_SELECTOR = `.${SELECTION_LOOKUP_PANEL_CLASS}`
export const GLOBAL_WORD_SEARCH_OVERLAY_SELECTOR = '.global-word-search-overlay'
export const WORD_SELECTION_PATTERN = /^[A-Za-z]+(?:['-][A-Za-z]+)*$/
export const SELECTION_LOOKUP_OFFSET = 8
export const SELECTION_LOOKUP_VIEWPORT_PADDING = 12
export const SELECTION_LOOKUP_FALLBACK_WIDTH = 320
export const SELECTION_LOOKUP_FALLBACK_HEIGHT = 220
export const SELECTION_LOOKUP_RIGHT_BIAS_RATIO = 0.28
export const SELECTION_LOOKUP_RIGHT_BIAS_MAX = 88

export type SelectionLookupAnchorRect = {
  bottom: number
  height: number
  left: number
  right: number
  top: number
  width: number
  x: number
  y: number
}

type SelectionLookupPanelSize = {
  height: number
  width: number
}

type ViewportSize = {
  height: number
  width: number
}

export function cloneSelectionAnchorRect(
  rect: DOMRect | DOMRectReadOnly,
): SelectionLookupAnchorRect {
  return {
    x: rect.x,
    y: rect.y,
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  }
}

export function resolveElementFromNode(node: Node | null): Element | null {
  if (!node) return null
  return node instanceof Element ? node : node.parentElement
}

export function isSelectionWordCandidate(value: string): boolean {
  return WORD_SELECTION_PATTERN.test(value.trim())
}

export function isEditableElement(element: Element | null): boolean {
  if (!(element instanceof HTMLElement)) return false
  const tagName = element.tagName
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || element.isContentEditable
}

export function isInsideSelectionLookupPanel(element: Element | null): boolean {
  return Boolean(element?.closest(SELECTION_LOOKUP_PANEL_SELECTOR))
}

export function isInsideGlobalWordSearchOverlay(element: Element | null): boolean {
  return Boolean(element?.closest(GLOBAL_WORD_SEARCH_OVERLAY_SELECTOR))
}

export function isExactSelectionLookupMatch(
  selectedWord: string,
  result: WordSearchResult | null | undefined,
): boolean {
  return (result?.word ?? '').trim().toLowerCase() === selectedWord.trim().toLowerCase()
}

export function buildSelectionLookupMeta(result: WordSearchResult): string {
  return [result.book_title?.trim(), result.chapter_title?.trim()].filter(Boolean).join(' · ')
}

export function resolveSelectionLookupExample(
  detailData: WordDetailResponse | null,
  result: WordSearchResult,
) {
  return detailData?.examples?.[0] ?? result.examples?.[0] ?? null
}

export function resolveSelectionLookupPosition(
  anchorRect: SelectionLookupAnchorRect,
  panelSize: SelectionLookupPanelSize,
  viewport: ViewportSize,
) {
  const width = Math.max(panelSize.width || 0, SELECTION_LOOKUP_FALLBACK_WIDTH)
  const height = Math.max(panelSize.height || 0, SELECTION_LOOKUP_FALLBACK_HEIGHT)
  const maxLeft = Math.max(
    SELECTION_LOOKUP_VIEWPORT_PADDING,
    viewport.width - width - SELECTION_LOOKUP_VIEWPORT_PADDING,
  )
  const maxTop = Math.max(
    SELECTION_LOOKUP_VIEWPORT_PADDING,
    viewport.height - height - SELECTION_LOOKUP_VIEWPORT_PADDING,
  )
  const horizontalBias = Math.min(
    Math.round(width * SELECTION_LOOKUP_RIGHT_BIAS_RATIO),
    SELECTION_LOOKUP_RIGHT_BIAS_MAX,
  )

  let left = anchorRect.right - horizontalBias
  if (left + width + SELECTION_LOOKUP_VIEWPORT_PADDING > viewport.width) {
    left = viewport.width - width - SELECTION_LOOKUP_VIEWPORT_PADDING
  } else if (left < SELECTION_LOOKUP_VIEWPORT_PADDING) {
    left = SELECTION_LOOKUP_VIEWPORT_PADDING
  }

  let top = anchorRect.bottom + SELECTION_LOOKUP_OFFSET
  if (top + height + SELECTION_LOOKUP_VIEWPORT_PADDING > viewport.height) {
    top = anchorRect.top - height - SELECTION_LOOKUP_OFFSET
  }

  return {
    left: Math.min(Math.max(SELECTION_LOOKUP_VIEWPORT_PADDING, left), maxLeft),
    top: Math.min(Math.max(SELECTION_LOOKUP_VIEWPORT_PADDING, top), maxTop),
  }
}
