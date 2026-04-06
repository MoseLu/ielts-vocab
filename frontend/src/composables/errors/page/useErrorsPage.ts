import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords } from '../../../features/vocabulary/hooks'
import {
  buildWrongWordsPracticeQuery,
  filterWrongWords,
} from '../../../features/vocabulary/wrongWordsFilters'
import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  WRONG_WORD_DIMENSIONS,
  getWrongWordActiveCount,
  getWrongWordDimensionHistoryWrong,
  hasWrongWordHistory,
  hasWrongWordPending,
  isWrongWordPendingInDimension,
  readWrongWordsReviewSelectionFromStorage,
  writeWrongWordsReviewSelectionToStorage,
} from '../../../features/vocabulary/wrongWordsStore'
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
  const [selectedWordKeys, setSelectedWordKeys] = useState<string[]>(
    () => readWrongWordsReviewSelectionFromStorage(),
  )
  const { words } = useWrongWords()
  const { minWrongCount, maxWrongCount } = getWrongCountBounds(wrongCountRange)

  const historyWords = useMemo(() => words.filter(word => hasWrongWordHistory(word)), [words])
  const pendingWords = useMemo(() => words.filter(word => hasWrongWordPending(word)), [words])
  const scopeWords = scope === 'pending' ? pendingWords : historyWords
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
    return [...filterWrongWords(words, {
      scope,
      dimFilter,
      startDate,
      endDate,
      minWrongCount,
      maxWrongCount,
    })].sort((a, b) => {
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
  }, [dimFilter, endDate, maxWrongCount, minWrongCount, scope, startDate, words])

  const selectedWordKeySet = useMemo(() => new Set(selectedWordKeys), [selectedWordKeys])
  const selectedFilteredWordCount = useMemo(() => {
    return filteredWords.filter(word => selectedWordKeySet.has(normalizeWrongWordKey(word.word))).length
  }, [filteredWords, selectedWordKeySet])
  const selectedWordCount = selectedWordKeys.length
  const selectedOutsideFilterCount = Math.max(0, selectedWordCount - selectedFilteredWordCount)
  const allFilteredSelected = filteredWords.length > 0
    && filteredWords.every(word => selectedWordKeySet.has(normalizeWrongWordKey(word.word)))

  const hasActiveFilters = dimFilter !== 'all' || Boolean(startDate) || Boolean(endDate) || wrongCountRange !== 'all'
  const practiceQuery = buildWrongWordsPracticeQuery({
    scope,
    dimFilter,
    startDate,
    endDate,
    minWrongCount,
    maxWrongCount,
  })
  const manualPracticeQuery = practiceQuery ? `${practiceQuery}&selection=manual` : 'selection=manual'

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

  const clearSelectedWords = useCallback(() => {
    updateSelectedWordKeys(() => [])
  }, [updateSelectedWordKeys])

  const resetFilters = useCallback(() => {
    setDimFilter('all')
    setStartDate('')
    setEndDate('')
    setWrongCountRange('all')
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
    words,
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
    hasActiveFilters,
    setActiveTab,
    setScope,
    setDimFilter,
    setStartDate,
    setEndDate,
    setWrongCountRange,
    toggleWordSelection,
    selectFilteredWords,
    clearSelectedWords,
    resetFilters,
    startSelectedPractice,
    goToPlan,
  }
}
