import { startTransition, useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  apiFetch,
  safeParse,
  WordDetailResponseSchema,
  WordSearchResponseSchema,
  type WordDetailResponse,
  type WordSearchResult,
} from '../../../lib'
import SelectionWordLookupCard from './SelectionWordLookupCard'
import { GLOBAL_WORD_SEARCH_OPEN_EVENT } from './globalWordSearchEvents'
import {
  cloneSelectionAnchorRect,
  isEditableElement,
  isExactSelectionLookupMatch,
  isInsideGlobalWordSearchOverlay,
  isInsideSelectionLookupPanel,
  isSelectionWordCandidate,
  resolveElementFromNode,
  type SelectionLookupAnchorRect,
} from './selectionWordLookup.shared'

const SEARCH_LIMIT = 1

export default function SelectionWordLookup() {
  const location = useLocation()
  const searchAbortRef = useRef<AbortController | null>(null)
  const detailAbortRef = useRef<AbortController | null>(null)
  const selectionTimerRef = useRef<number | null>(null)
  const requestVersionRef = useRef(0)
  const [selectedWord, setSelectedWord] = useState('')
  const [anchorRect, setAnchorRect] = useState<SelectionLookupAnchorRect | null>(null)
  const [searchResult, setSearchResult] = useState<WordSearchResult | null>(null)
  const [detailData, setDetailData] = useState<WordDetailResponse | null>(null)
  const [isGlobalSearchContext, setIsGlobalSearchContext] = useState(false)
  const [isResolving, setIsResolving] = useState(false)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearBrowserSelection = useCallback(() => {
    const selection = document.getSelection()
    selection?.removeAllRanges?.()
  }, [])

  const resetLookupState = useCallback(() => {
    startTransition(() => {
      setSelectedWord('')
      setAnchorRect(null)
      setSearchResult(null)
      setDetailData(null)
      setIsGlobalSearchContext(false)
    })
    setIsResolving(false)
    setIsLoadingDetails(false)
    setError(null)
  }, [])

  const abortInflightRequests = useCallback(() => {
    searchAbortRef.current?.abort()
    detailAbortRef.current?.abort()
    searchAbortRef.current = null
    detailAbortRef.current = null
  }, [])

  const closeLookup = useCallback(() => {
    if (selectionTimerRef.current != null) {
      window.clearTimeout(selectionTimerRef.current)
      selectionTimerRef.current = null
    }
    requestVersionRef.current += 1
    abortInflightRequests()
    resetLookupState()
  }, [abortInflightRequests, resetLookupState])

  const loadWordDetails = useCallback(async (word: string, requestVersion: number) => {
    detailAbortRef.current?.abort()
    const controller = new AbortController()
    detailAbortRef.current = controller
    setIsLoadingDetails(true)

    try {
      const raw = await apiFetch<unknown>(
        `/api/books/word-details?word=${encodeURIComponent(word)}`,
        { signal: controller.signal },
      )
      const parsed = safeParse(WordDetailResponseSchema, raw)
      if (!parsed.success) {
        throw new Error('单词详情格式错误')
      }

      if (requestVersionRef.current !== requestVersion) return
      startTransition(() => setDetailData(parsed.data))
    } catch (detailError) {
      if (controller.signal.aborted || requestVersionRef.current !== requestVersion) return
      setError(detailError instanceof Error ? detailError.message : '单词详情加载失败')
    } finally {
      if (detailAbortRef.current === controller) {
        detailAbortRef.current = null
      }
      if (!controller.signal.aborted && requestVersionRef.current === requestVersion) {
        setIsLoadingDetails(false)
      }
    }
  }, [])

  const resolveSelectedWord = useCallback(async (
    word: string,
    nextAnchorRect: SelectionLookupAnchorRect,
    nextIsGlobalSearchContext: boolean,
  ) => {
    const trimmedWord = word.trim()
    if (!trimmedWord) {
      closeLookup()
      return
    }

    const requestVersion = requestVersionRef.current + 1
    requestVersionRef.current = requestVersion
    abortInflightRequests()
    startTransition(() => {
      setSelectedWord(trimmedWord)
      setAnchorRect(nextAnchorRect)
      setSearchResult(null)
      setDetailData(null)
      setIsGlobalSearchContext(nextIsGlobalSearchContext)
    })
    setIsResolving(true)
    setIsLoadingDetails(false)
    setError(null)

    const controller = new AbortController()
    searchAbortRef.current = controller

    try {
      const raw = await apiFetch<unknown>(
        `/api/books/search?q=${encodeURIComponent(trimmedWord)}&limit=${SEARCH_LIMIT}`,
        { signal: controller.signal },
      )
      const parsed = safeParse(WordSearchResponseSchema, raw)
      if (!parsed.success) {
        throw new Error('搜索结果格式错误')
      }

      const exactResult = parsed.data.results[0] ?? null
      if (!isExactSelectionLookupMatch(trimmedWord, exactResult)) {
        if (requestVersionRef.current === requestVersion) {
          startTransition(() => {
            setAnchorRect(null)
            setSearchResult(null)
            setDetailData(null)
          })
          setIsLoadingDetails(false)
          setError(null)
        }
        return
      }

      if (requestVersionRef.current !== requestVersion) return
      startTransition(() => {
        setSearchResult(exactResult)
        setAnchorRect(nextAnchorRect)
        setIsGlobalSearchContext(nextIsGlobalSearchContext)
      })
      clearBrowserSelection()
      void loadWordDetails(exactResult.word, requestVersion)
    } catch (searchError) {
      if (controller.signal.aborted || requestVersionRef.current !== requestVersion) return
      startTransition(() => {
        setAnchorRect(null)
        setSearchResult(null)
        setDetailData(null)
      })
      setError(searchError instanceof Error ? searchError.message : '划词查询失败')
      setIsLoadingDetails(false)
    } finally {
      if (searchAbortRef.current === controller) {
        searchAbortRef.current = null
      }
      if (!controller.signal.aborted && requestVersionRef.current === requestVersion) {
        setIsResolving(false)
      }
    }
  }, [abortInflightRequests, clearBrowserSelection, closeLookup, loadWordDetails])

  const scheduleSelectionEvaluation = useCallback((eventTarget: EventTarget | null) => {
    if (typeof window === 'undefined') return
    if (selectionTimerRef.current != null) {
      window.clearTimeout(selectionTimerRef.current)
    }

    selectionTimerRef.current = window.setTimeout(() => {
      selectionTimerRef.current = null
      const selection = document.getSelection()
      if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
        closeLookup()
        return
      }

      const targetElement = eventTarget instanceof Node ? resolveElementFromNode(eventTarget) : null
      const anchorElement = resolveElementFromNode(selection.anchorNode)
      const focusElement = resolveElementFromNode(selection.focusNode)
      const inspectedElements = [targetElement, anchorElement, focusElement]
      const nextIsGlobalSearchContext = inspectedElements.some(isInsideGlobalWordSearchOverlay)

      if (inspectedElements.some(isInsideSelectionLookupPanel)) {
        return
      }

      if (inspectedElements.some(isEditableElement)) {
        closeLookup()
        return
      }

      const trimmedWord = selection.toString().trim()
      if (!isSelectionWordCandidate(trimmedWord)) {
        closeLookup()
        return
      }

      const rangeRect = selection.getRangeAt(0).getBoundingClientRect()
      if (!rangeRect.width && !rangeRect.height) {
        closeLookup()
        return
      }

      void resolveSelectedWord(
        trimmedWord,
        cloneSelectionAnchorRect(rangeRect),
        nextIsGlobalSearchContext,
      )
    }, 0)
  }, [closeLookup, resolveSelectedWord])

  useEffect(() => {
    const handlePointerUp = (event: PointerEvent) => {
      if (event.pointerType === 'touch') return
      scheduleSelectionEvaluation(event.target)
    }

    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.key === 'Escape') return
      scheduleSelectionEvaluation(event.target)
    }

    document.addEventListener('pointerup', handlePointerUp, true)
    document.addEventListener('keyup', handleKeyUp, true)

    return () => {
      document.removeEventListener('pointerup', handlePointerUp, true)
      document.removeEventListener('keyup', handleKeyUp, true)
    }
  }, [scheduleSelectionEvaluation])

  useEffect(() => {
    if (!searchResult) return undefined

    const handlePointerDown = (event: PointerEvent) => {
      const targetElement = event.target instanceof Node ? resolveElementFromNode(event.target) : null
      if (isInsideSelectionLookupPanel(targetElement)) return
      closeLookup()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeLookup()
      }
    }

    const handleViewportClose = () => closeLookup()

    document.addEventListener('pointerdown', handlePointerDown, true)
    document.addEventListener('scroll', handleViewportClose, true)
    window.addEventListener('resize', handleViewportClose)
    window.addEventListener('keydown', handleKeyDown, true)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown, true)
      document.removeEventListener('scroll', handleViewportClose, true)
      window.removeEventListener('resize', handleViewportClose)
      window.removeEventListener('keydown', handleKeyDown, true)
    }
  }, [closeLookup, searchResult])

  useEffect(() => {
    closeLookup()
  }, [closeLookup, location.hash, location.pathname, location.search])

  useEffect(() => {
    const handleGlobalSearchOpen = () => closeLookup()
    window.addEventListener(GLOBAL_WORD_SEARCH_OPEN_EVENT, handleGlobalSearchOpen)
    return () => window.removeEventListener(GLOBAL_WORD_SEARCH_OPEN_EVENT, handleGlobalSearchOpen)
  }, [closeLookup])

  useEffect(() => () => {
    if (selectionTimerRef.current != null) {
      window.clearTimeout(selectionTimerRef.current)
    }
    abortInflightRequests()
  }, [abortInflightRequests])

  if (!selectedWord || !anchorRect || !searchResult) return null

  return (
    <SelectionWordLookupCard
      anchorRect={anchorRect}
      detailData={detailData}
      error={error}
      isGlobalSearchContext={isGlobalSearchContext}
      isLoadingDetails={isLoadingDetails || isResolving}
      onDismiss={closeLookup}
      result={searchResult}
    />
  )
}
