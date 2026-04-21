export const GLOBAL_WORD_SEARCH_OPEN_EVENT = 'global-word-search:open'

export interface OpenGlobalWordSearchDetail {
  query?: string
  autoSubmit?: boolean
}

export function openGlobalWordSearch(detail: OpenGlobalWordSearchDetail = {}): void {
  window.dispatchEvent(new CustomEvent<OpenGlobalWordSearchDetail>(GLOBAL_WORD_SEARCH_OPEN_EVENT, {
    detail,
  }))
}
