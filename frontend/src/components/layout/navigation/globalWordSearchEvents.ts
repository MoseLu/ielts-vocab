export const GLOBAL_WORD_SEARCH_OPEN_EVENT = 'global-word-search:open'

interface OpenGlobalWordSearchDetail {
  query?: string
}

export function openGlobalWordSearch(detail: OpenGlobalWordSearchDetail = {}): void {
  window.dispatchEvent(new CustomEvent<OpenGlobalWordSearchDetail>(GLOBAL_WORD_SEARCH_OPEN_EVENT, {
    detail,
  }))
}
