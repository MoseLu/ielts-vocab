import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  apiFetch,
  safeParse,
  WordSearchResponseSchema,
  type WordSearchResult,
} from '../../../lib'
import { GLOBAL_WORD_SEARCH_OPEN_EVENT } from '../../../components/layout/navigation/globalWordSearchEvents'

const SEARCH_LIMIT = 12

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tagName = target.tagName
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || target.isContentEditable
}

function getResultKey(result: WordSearchResult): string {
  return `${result.book_id}:${String(result.chapter_id ?? '')}:${result.word.toLowerCase()}`
}

export function useGlobalWordSearch() {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [results, setResults] = useState<WordSearchResult[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const selectedResult = useMemo(() => {
    if (!results.length) return null
    return results.find(result => getResultKey(result) === selectedKey) ?? results[0]
  }, [results, selectedKey])

  const clearSearchState = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setSubmittedQuery('')
    setResults([])
    setSelectedKey(null)
    setError(null)
    setIsLoading(false)
  }, [])

  const closeSearch = useCallback(() => {
    clearSearchState()
    setIsOpen(false)
    setQuery('')
  }, [clearSearchState])

  const openSearch = useCallback((nextQuery = '') => {
    setIsOpen(true)
    if (nextQuery) {
      setQuery(nextQuery)
    }
    requestAnimationFrame(() => {
      inputRef.current?.focus()
      inputRef.current?.select()
    })
  }, [])

  const runSearch = useCallback(async (rawQuery: string) => {
    const trimmedQuery = rawQuery.trim()
    if (!trimmedQuery) {
      clearSearchState()
      return
    }

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setIsLoading(true)
    setSubmittedQuery(trimmedQuery)
    setError(null)

    try {
      const raw = await apiFetch<unknown>(
        `/api/books/search?q=${encodeURIComponent(trimmedQuery)}&limit=${SEARCH_LIMIT}`,
        { signal: controller.signal },
      )
      const parsed = safeParse(WordSearchResponseSchema, raw)
      if (!parsed.success) {
        throw new Error('搜索结果格式错误')
      }

      startTransition(() => {
        setResults(parsed.data.results)
        setSelectedKey(parsed.data.results[0] ? getResultKey(parsed.data.results[0]) : null)
      })
    } catch (searchError) {
      if (controller.signal.aborted) return
      setResults([])
      setSelectedKey(null)
      setError(searchError instanceof Error ? searchError.message : '搜索失败，请稍后重试')
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      if (!controller.signal.aborted) {
        setIsLoading(false)
      }
    }
  }, [clearSearchState])

  const handleQueryChange = useCallback((nextQuery: string) => {
    setQuery(nextQuery)

    const trimmedQuery = nextQuery.trim()
    if (!trimmedQuery || (submittedQuery && trimmedQuery !== submittedQuery)) {
      clearSearchState()
    }
  }, [clearSearchState, submittedQuery])

  const handleQuickPickWord = useCallback((nextWord: string) => {
    setQuery(nextWord)
    void runSearch(nextWord)
  }, [runSearch])

  useEffect(() => {
    const handleGlobalKey = (event: KeyboardEvent) => {
      if (isOpen && event.key === 'Escape') {
        event.preventDefault()
        event.stopImmediatePropagation()
        closeSearch()
        return
      }

      if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return
      if (!event.shiftKey || event.key.toLowerCase() !== 'q') return
      if (isEditableTarget(event.target) && event.target !== inputRef.current) return

      event.preventDefault()
      event.stopImmediatePropagation()
      openSearch()
    }

    const handleOpenEvent = (event: Event) => {
      const customEvent = event as CustomEvent<{ query?: string }>
      openSearch(customEvent.detail?.query ?? '')
    }

    window.addEventListener('keydown', handleGlobalKey, true)
    window.addEventListener(GLOBAL_WORD_SEARCH_OPEN_EVENT, handleOpenEvent as EventListener)

    return () => {
      window.removeEventListener('keydown', handleGlobalKey, true)
      window.removeEventListener(GLOBAL_WORD_SEARCH_OPEN_EVENT, handleOpenEvent as EventListener)
    }
  }, [closeSearch, isOpen, openSearch])

  useEffect(() => {
    if (!isOpen) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [isOpen])

  return {
    isOpen,
    query,
    submittedQuery,
    results,
    selectedResult,
    error,
    isLoading,
    inputRef,
    showSearchEntry: !selectedResult,
    closeSearch,
    runSearch,
    handleQueryChange,
    handleQuickPickWord,
  }
}
