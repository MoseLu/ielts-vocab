import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords } from '../../../features/vocabulary/hooks'
import {
  buildWrongWordsPracticeQuery,
  compareWrongWordSearchResults,
  filterWrongWords,
  matchesWrongWordSearchTerm,
  normalizeWrongWordSearchTerm,
  type WrongWordSearchMode,
} from '../../../features/vocabulary/wrongWordsFilters'
import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  WRONG_WORD_DIMENSIONS,
  getWrongWordActiveCount,
  getWrongWordDimensionHistoryWrong,
  hasWrongWordHistory,
  hasWrongWordPending,
  isWrongWordPendingInDimension,
  mergeWrongWordLists,
  readWrongWordsReviewSelectionFromStorage,
  writeWrongWordsReviewSelectionToStorage,
} from '../../../features/vocabulary/wrongWordsStore'
import { apiFetch } from '../../../lib'
import { requestPracticeMode } from '../../practice/page/practiceModeEvents'
import {
  dedupeWrongWordKeys,
  getScopedWrongWordDimensions,
  isSameWrongWordKeyList,
  normalizeWrongWordKey,
} from '../../../components/errors/page/errorsPageHelpers'

export type ActiveTab = 'words' | 'real'
export type DimFilter = 'all' | WrongWordDimension
export type WrongCountRange = 'all' | '0-5' | '6-10' | '11-20' | '20+'

const ERRORS_PAGE_SIZE = 10

function formatDateInput(date: Date): string {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getWrongCountBounds(range: WrongCountRange): { minWrongCount?: number; maxWrongCount?: number } {
  switch (range) {
    case '0-5':
      return { maxWrongCount: 5 }
    case '6-10':
      return { minWrongCount: 6, maxWrongCount: 10 }
    case '11-20':
      return { minWrongCount: 11, maxWrongCount: 20 }
    case '20+':
      return { minWrongCount: 21 }
    default:
      return {}
  }
}

function resolvePracticeMode(dimFilter: DimFilter): string | null {
  if (dimFilter === 'recognition') return 'quickmemory'
  if (dimFilter === 'listening') return 'listening'
  if (dimFilter === 'dictation') return 'dictation'
  if (dimFilter === 'meaning') return 'meaning'
  return null
}

export function useErrorsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('words')
  const [scope, setScope] = useState<WrongWordCollectionScope>('pending')
  const [dimFilter, setDimFilter] = useState<DimFilter>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [wrongCountRange, setWrongCountRange] = useState<WrongCountRange>('all')
  const [searchText, setSearchText] = useState('')
  const [searchMode, setSearchMode] = useState<WrongWordSearchMode | null>(null)
  const [appliedSearch, setAppliedSearch] = useState('')
  const [remoteSearchWords, setRemoteSearchWords] = useState<WrongWordRecord[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [selectedWordKeys, setSelectedWordKeys] = useState<string[]>(
    () => readWrongWordsReviewSelectionFromStorage(),
  )
  const searchRequestIdRef = useRef(0)
  const { words, loading } = useWrongWords({ includeDetails: false })
  const { minWrongCount, maxWrongCount } = getWrongCountBounds(wrongCountRange)

  const knownWordKeySet = useMemo(
    () => new Set(words.map(word => normalizeWrongWordKey(word.word)).filter(Boolean)),
    [words],
  )

  useEffect(() => {
    const nextSelectedWordKeys = selectedWordKeys.filter(key => knownWordKeySet.has(key))
    if (isSameWrongWordKeyList(nextSelectedWordKeys, selectedWordKeys)) return

    setSelectedWordKeys(nextSelectedWordKeys)
    writeWrongWordsReviewSelectionToStorage(nextSelectedWordKeys)
  }, [knownWordKeySet, selectedWordKeys])

  const visibleWords = useMemo(() => {
    if (!appliedSearch) return words

    const localMatchedWords = words.filter(word => matchesWrongWordSearchTerm(word, appliedSearch, searchMode))
    const remoteMatchedWords = remoteSearchWords.filter(word => matchesWrongWordSearchTerm(word, appliedSearch, searchMode))
    return mergeWrongWordLists(localMatchedWords, remoteMatchedWords)
  }, [appliedSearch, remoteSearchWords, searchMode, words])

  const historyWords = useMemo(() => visibleWords.filter(word => hasWrongWordHistory(word)), [visibleWords])
  const pendingWords = useMemo(() => visibleWords.filter(word => hasWrongWordPending(word)), [visibleWords])
  const scopeWords = scope === 'pending' ? pendingWords : historyWords

  const dimStats = useMemo(() => {
    const counts = WRONG_WORD_DIMENSIONS.reduce((result, dimension) => {
      result[dimension] = 0
      return result
    }, {} as Record<WrongWordDimension, number>)
    let hitCount = 0
    let overlappingWordCount = 0

    scopeWords.forEach(word => {
      const matchedDimensions = getScopedWrongWordDimensions(word, scope)
      hitCount += matchedDimensions.length
      if (matchedDimensions.length > 1) {
        overlappingWordCount += 1
      }
      matchedDimensions.forEach(dimension => {
        counts[dimension] += 1
      })
    })

    return {
      counts,
      hitCount,
      overlappingWordCount,
    }
  }, [scope, scopeWords])

  const filteredWords = useMemo(() => {
    return [...filterWrongWords(visibleWords, {
      scope,
      dimFilter,
      startDate,
      endDate,
      minWrongCount,
      maxWrongCount,
    })].sort((a, b) => {
      if (appliedSearch) {
        return compareWrongWordSearchResults(a, b, appliedSearch, searchMode)
      }

      if (dimFilter !== 'all') {
        const aDimCount = scope === 'history'
          ? getWrongWordDimensionHistoryWrong(a, dimFilter)
          : (isWrongWordPendingInDimension(a, dimFilter) ? getWrongWordDimensionHistoryWrong(a, dimFilter) : 0)
        const bDimCount = scope === 'history'
          ? getWrongWordDimensionHistoryWrong(b, dimFilter)
          : (isWrongWordPendingInDimension(b, dimFilter) ? getWrongWordDimensionHistoryWrong(b, dimFilter) : 0)
        if (bDimCount !== aDimCount) return bDimCount - aDimCount
      }

      return getWrongWordActiveCount(b, scope) - getWrongWordActiveCount(a, scope)
    })
  }, [appliedSearch, dimFilter, endDate, maxWrongCount, minWrongCount, scope, searchMode, startDate, visibleWords])

  const selectedWordKeySet = useMemo(() => new Set(selectedWordKeys), [selectedWordKeys])
  const selectedFilteredWordCount = useMemo(() => {
    return filteredWords.filter(word => selectedWordKeySet.has(normalizeWrongWordKey(word.word))).length
  }, [filteredWords, selectedWordKeySet])
  const selectedWordCount = selectedWordKeys.length
  const selectedOutsideFilterCount = Math.max(0, selectedWordCount - selectedFilteredWordCount)
  const allFilteredSelected = filteredWords.length > 0
    && filteredWords.every(word => selectedWordKeySet.has(normalizeWrongWordKey(word.word)))
  const totalPages = Math.max(1, Math.ceil(filteredWords.length / ERRORS_PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const paginatedWords = useMemo(() => {
    const offset = (currentPage - 1) * ERRORS_PAGE_SIZE
    return filteredWords.slice(offset, offset + ERRORS_PAGE_SIZE)
  }, [currentPage, filteredWords])
  const allPaginatedSelected = paginatedWords.length > 0
    && paginatedWords.every(word => selectedWordKeySet.has(normalizeWrongWordKey(word.word)))
  const pageStartIndex = filteredWords.length === 0 ? 0 : ((currentPage - 1) * ERRORS_PAGE_SIZE) + 1
  const pageEndIndex = Math.min(currentPage * ERRORS_PAGE_SIZE, filteredWords.length)

  const hasActiveFilters = dimFilter !== 'all'
    || Boolean(startDate)
    || Boolean(endDate)
    || wrongCountRange !== 'all'
    || Boolean(appliedSearch)
  const canResetFilters = hasActiveFilters || Boolean(searchText) || searchMode != null
  const practiceQuery = buildWrongWordsPracticeQuery({
    scope,
    dimFilter,
    startDate,
    endDate,
    minWrongCount,
    maxWrongCount,
  })
  const manualPracticeQuery = practiceQuery ? `${practiceQuery}&selection=manual` : 'selection=manual'

  useEffect(() => {
    setPage(1)
  }, [activeTab, appliedSearch, dimFilter, endDate, scope, searchMode, startDate, wrongCountRange])

  useEffect(() => {
    if (page <= totalPages) return
    setPage(totalPages)
  }, [page, totalPages])

  const updateSelectedWordKeys = useCallback((updater: (previous: string[]) => string[]) => {
    setSelectedWordKeys(previous => {
      const next = dedupeWrongWordKeys(updater(previous))
      writeWrongWordsReviewSelectionToStorage(next)
      return next
    })
  }, [])

  const toggleWordSelection = useCallback((word: string) => {
    const key = normalizeWrongWordKey(word)
    updateSelectedWordKeys(previous => (
      previous.includes(key)
        ? previous.filter(item => item !== key)
        : [...previous, key]
    ))
  }, [updateSelectedWordKeys])

  const selectFilteredWords = useCallback(() => {
    updateSelectedWordKeys(previous => [
      ...previous,
      ...filteredWords.map(word => word.word),
    ])
  }, [filteredWords, updateSelectedWordKeys])

  const selectPaginatedWords = useCallback(() => {
    updateSelectedWordKeys(previous => [
      ...previous,
      ...paginatedWords.map(word => word.word),
    ])
  }, [paginatedWords, updateSelectedWordKeys])

  const clearSelectedWords = useCallback(() => {
    updateSelectedWordKeys(() => [])
  }, [updateSelectedWordKeys])

  const applySearch = useCallback(async () => {
    const nextSearch = normalizeWrongWordSearchTerm(searchText)
    const requestId = searchRequestIdRef.current + 1

    searchRequestIdRef.current = requestId
    setAppliedSearch(nextSearch)
    setRemoteSearchWords([])

    if (!nextSearch) {
      setSearchMode(null)
      setSearchLoading(false)
      return
    }

    setSearchLoading(true)

    try {
      const params = new URLSearchParams({
        details: 'compact',
        search: nextSearch,
      })
      const response = await apiFetch<{ words?: WrongWordRecord[] }>(`/api/ai/wrong-words?${params.toString()}`)
      if (searchRequestIdRef.current !== requestId) return

      const nextRemoteWords = Array.isArray(response.words) ? response.words : []
      setRemoteSearchWords(nextRemoteWords)
    } catch {
      if (searchRequestIdRef.current !== requestId) return
      setRemoteSearchWords([])
    } finally {
      if (searchRequestIdRef.current === requestId) {
        setSearchLoading(false)
      }
    }
  }, [searchText])

  const resetFilters = useCallback(() => {
    searchRequestIdRef.current += 1
    setDimFilter('all')
    setStartDate('')
    setEndDate('')
    setWrongCountRange('all')
    setSearchText('')
    setSearchMode(null)
    setAppliedSearch('')
    setRemoteSearchWords([])
    setSearchLoading(false)
  }, [])

  const applyTodayDateRange = useCallback(() => {
    const today = formatDateInput(new Date())
    setStartDate(today)
    setEndDate(today)
  }, [])

  const applyRecentDaysDateRange = useCallback((days: number) => {
    const rangeDays = Math.max(1, Math.floor(days))
    const end = new Date()
    const start = new Date(end)
    start.setDate(end.getDate() - (rangeDays - 1))

    setStartDate(formatDateInput(start))
    setEndDate(formatDateInput(end))
  }, [])

  const startSelectedPractice = useCallback(() => {
    requestPracticeMode(resolvePracticeMode(dimFilter))
    navigate(`/practice?mode=errors&${manualPracticeQuery}`)
  }, [dimFilter, manualPracticeQuery, navigate])

  const goToPlan = useCallback(() => {
    navigate('/plan')
  }, [navigate])

  return {
    activeTab,
    scope,
    dimFilter,
    startDate,
    endDate,
    wrongCountRange,
    searchText,
    searchMode,
    appliedSearch,
    words,
    visibleWords,
    historyWords,
    pendingWords,
    scopeWords,
    dimStats,
    dimCounts: dimStats.counts,
    filteredWords,
    selectedWordKeySet,
    selectedWordCount,
    selectedFilteredWordCount,
    selectedOutsideFilterCount,
    allFilteredSelected,
    allPaginatedSelected,
    hasActiveFilters,
    canResetFilters,
    loading,
    searchLoading,
    page: currentPage,
    totalPages,
    pageStartIndex,
    pageEndIndex,
    paginatedWords,
    setActiveTab,
    setScope,
    setDimFilter,
    setStartDate,
    setEndDate,
    setWrongCountRange,
    setSearchText,
    setSearchMode,
    setPage,
    applySearch,
    applyTodayDateRange,
    applyRecentDaysDateRange,
    toggleWordSelection,
    selectFilteredWords,
    selectPaginatedWords,
    clearSelectedWords,
    resetFilters,
    startSelectedPractice,
    goToPlan,
  }
}
