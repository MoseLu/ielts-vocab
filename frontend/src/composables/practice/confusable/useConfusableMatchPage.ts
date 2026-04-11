import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../../../contexts'
import { buildBookPracticePath } from '../../../lib'
import type { Chapter, Word, WordStatuses } from '../../../components/practice/types'
import {
  buildMatchGroups,
  buildRoundCards,
  getRoundGroups,
  getUnresolvedGroups,
  resolveRoundGroupKeys,
  type MatchCard,
  type MatchGroup,
} from '../../../components/practice/confusableMatch'
import {
  clearStoredChapterSnapshot,
  measureLine,
  type ActiveLine,
} from '../../../components/practice/confusable/confusableMatchPageHelpers'
import {
  buildConfusableMatchSnapshot,
  loadConfusableMatchPageData,
  persistConfusableMatchProgress,
} from '../../../components/practice/confusable/confusableMatchPageData'
import type { CustomConfusableChapter } from '../../../components/practice/ConfusableCustomGroupsModal'

const MATCH_GROUPS_PER_ROUND = 1
const MATCH_SUCCESS_DELAY = 900
const MATCH_FAILURE_DELAY = 900
const MATCH_GROUP_INSIGHT_DELAY = 1800

export function useConfusableMatchPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { showToast } = useToast()
  const bookId = searchParams.get('book')
  const chapterId = searchParams.get('chapter')
  const supportsCustomGroups = bookId === 'ielts_confusable_match'
  const groupsPerRound = MATCH_GROUPS_PER_ROUND

  const [bookChapters, setBookChapters] = useState<Chapter[]>([])
  const [currentChapterTitle, setCurrentChapterTitle] = useState('')
  const [vocabulary, setVocabulary] = useState<Word[]>([])
  const [roundGroupKeys, setRoundGroupKeys] = useState<string[]>([])
  const [boardCards, setBoardCards] = useState<MatchCard[]>([])
  const [answeredWordKeys, setAnsweredWordKeys] = useState<Set<string>>(new Set())
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [selectedCard, setSelectedCard] = useState<MatchCard | null>(null)
  const [successCardIds, setSuccessCardIds] = useState<string[]>([])
  const [errorCardIds, setErrorCardIds] = useState<string[]>([])
  const [activeLine, setActiveLine] = useState<ActiveLine | null>(null)
  const [completedGroup, setCompletedGroup] = useState<MatchGroup | null>(null)
  const [errorComparison, setErrorComparison] = useState<{ fromWord: string; toWord: string } | null>(null)
  const [warningText, setWarningText] = useState('')
  const [warningVisible, setWarningVisible] = useState(false)
  const [interactionLocked, setInteractionLocked] = useState(false)
  const [showWordList, setShowWordList] = useState(false)
  const [showCustomModal, setShowCustomModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hydrated, setHydrated] = useState(false)

  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const groupBoardRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const persistRef = useRef('')

  const allGroups = useMemo(() => buildMatchGroups(vocabulary), [vocabulary])
  const groupOrderMap = useMemo(() => new Map(allGroups.map((group, index) => [group.key, index + 1])), [allGroups])
  const currentRoundGroups = useMemo(() => getRoundGroups(allGroups, roundGroupKeys), [allGroups, roundGroupKeys])
  const unresolvedGroups = useMemo(() => getUnresolvedGroups(allGroups, answeredWordKeys), [allGroups, answeredWordKeys])

  const boardGroups = useMemo(() => {
    const cardsByGroup = new Map<string, MatchCard[]>()
    for (const card of boardCards) {
      const existing = cardsByGroup.get(card.groupKey)
      if (existing) {
        existing.push(card)
      } else {
        cardsByGroup.set(card.groupKey, [card])
      }
    }

    return currentRoundGroups.map(group => ({
      key: group.key,
      groupNumber: groupOrderMap.get(group.key) ?? 0,
      words: group.words,
      cards: cardsByGroup.get(group.key) ?? [],
    }))
  }, [boardCards, currentRoundGroups, groupOrderMap])

  const queuedGroups = useMemo(() => unresolvedGroups.slice(1, 4).map(group => ({
    key: group.key,
    groupNumber: groupOrderMap.get(group.key) ?? 0,
    words: group.words,
    cards: [],
  })), [groupOrderMap, unresolvedGroups])

  const completedBoardGroup = useMemo(() => (
    completedGroup
      ? {
          key: completedGroup.key,
          groupNumber: groupOrderMap.get(completedGroup.key) ?? 0,
          words: completedGroup.words,
          cards: [],
        }
      : null
  ), [completedGroup, groupOrderMap])

  const totalWords = vocabulary.length
  const answeredCount = answeredWordKeys.size
  const totalGroups = allGroups.length
  const answeredGroupCount = useMemo(
    () => allGroups.filter(group => group.words.every(word => answeredWordKeys.has(word.key))).length,
    [allGroups, answeredWordKeys],
  )
  const isCompleted = totalWords > 0 && answeredCount >= totalWords
  const currentChapter = useMemo(
    () => bookChapters.find(chapter => String(chapter.id) === String(chapterId)) ?? null,
    [bookChapters, chapterId],
  )
  const wordListQueue = useMemo(() => vocabulary.map((_, index) => index), [vocabulary])
  const wordListStatuses = useMemo<WordStatuses>(() => {
    const statuses: WordStatuses = {}
    vocabulary.forEach((word, index) => {
      if (answeredWordKeys.has(word.word.toLowerCase())) {
        statuses[index] = 'correct'
      }
    })
    return statuses
  }, [answeredWordKeys, vocabulary])
  const wordListCurrentIndex = useMemo(() => {
    const nextPendingIndex = vocabulary.findIndex(word => !answeredWordKeys.has(word.word.toLowerCase()))
    return nextPendingIndex >= 0 ? nextPendingIndex : Math.max(vocabulary.length - 1, 0)
  }, [answeredWordKeys, vocabulary])

  const applyRound = useCallback((nextRoundGroupKeys: string[], nextAnsweredWordKeys: Set<string>) => {
    const nextGroups = getRoundGroups(allGroups, nextRoundGroupKeys)
    const nextCards = buildRoundCards(nextGroups, nextAnsweredWordKeys)
    startTransition(() => {
      setRoundGroupKeys(nextRoundGroupKeys)
      setBoardCards(nextCards)
      setSelectedCard(null)
      setSuccessCardIds([])
      setErrorCardIds([])
      setActiveLine(null)
      setCompletedGroup(null)
      setErrorComparison(null)
    })
  }, [allGroups])

  const resetBoardForWords = useCallback((nextChapter: Chapter, nextWords: Word[]) => {
    const nextGroups = buildMatchGroups(nextWords)
    const nextAnsweredWordKeys = new Set<string>()
    const nextRoundGroupKeys = resolveRoundGroupKeys(nextGroups, nextAnsweredWordKeys, groupsPerRound)
    const nextCards = buildRoundCards(getRoundGroups(nextGroups, nextRoundGroupKeys), nextAnsweredWordKeys)
    startTransition(() => {
      setVocabulary(nextWords)
      setCurrentChapterTitle(nextChapter.title)
      setAnsweredWordKeys(nextAnsweredWordKeys)
      setCorrectCount(0)
      setWrongCount(0)
      setRoundGroupKeys(nextRoundGroupKeys)
      setBoardCards(nextCards)
      setSelectedCard(null)
      setSuccessCardIds([])
      setErrorCardIds([])
      setActiveLine(null)
      setCompletedGroup(null)
      setErrorComparison(null)
      setWarningVisible(false)
      setWarningText('')
      setInteractionLocked(false)
    })
  }, [groupsPerRound])

  useEffect(() => {
    let cancelled = false
    if (!bookId) {
      setError('缺少词书参数')
      setLoading(false)
      return () => { cancelled = true }
    }

    setLoading(true)
    setError(null)
    persistRef.current = ''

    void loadConfusableMatchPageData({ bookId, chapterId, groupsPerRound, navigate })
      .then(data => {
        if (cancelled || data.redirectPath) return
        setBookChapters(data.chapters)
        startTransition(() => {
          setVocabulary(data.words)
          setCurrentChapterTitle(data.title)
          setAnsweredWordKeys(data.answeredWordKeys)
          setCorrectCount(data.correctCount)
          setWrongCount(data.wrongCount)
          setRoundGroupKeys(data.roundGroupKeys)
          setBoardCards(data.cards)
          setSelectedCard(null)
          setSuccessCardIds([])
          setErrorCardIds([])
          setActiveLine(null)
          setCompletedGroup(null)
          setErrorComparison(null)
          setWarningVisible(false)
          setWarningText('')
        })
      })
      .catch(loadError => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : '加载辨析词汇失败')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setHydrated(true)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [bookId, chapterId, groupsPerRound, navigate])

  useEffect(() => {
    if (!bookId || !chapterId || !hydrated || !vocabulary.length) return
    const snapshot = buildConfusableMatchSnapshot({
      answeredCount,
      correctCount,
      wrongCount,
      isCompleted,
      answeredWordKeys,
      roundGroupKeys,
    })
    const serialized = JSON.stringify(snapshot)
    if (serialized === persistRef.current) return
    persistRef.current = serialized
    persistConfusableMatchProgress({ bookId, chapterId, snapshot })
  }, [
    answeredCount,
    answeredWordKeys,
    bookId,
    chapterId,
    correctCount,
    hydrated,
    isCompleted,
    roundGroupKeys,
    vocabulary.length,
    wrongCount,
  ])

  const advanceIfRoundCleared = useCallback((nextAnsweredWordKeys: Set<string>) => {
    const activeGroup = currentRoundGroups[0]
    if (!activeGroup) return

    const remainingInCurrentRound = activeGroup.words.some(word => !nextAnsweredWordKeys.has(word.key))
    if (remainingInCurrentRound) return

    const nextRoundGroupKeys = resolveRoundGroupKeys(allGroups, nextAnsweredWordKeys, groupsPerRound)
    setCompletedGroup(activeGroup)
    setInteractionLocked(true)
    window.setTimeout(() => {
      startTransition(() => {
        applyRound(nextRoundGroupKeys, nextAnsweredWordKeys)
        setCompletedGroup(null)
        setInteractionLocked(false)
      })
    }, MATCH_GROUP_INSIGHT_DELAY)
  }, [allGroups, applyRound, currentRoundGroups, groupsPerRound])

  const handleCorrectMatch = useCallback((wordCard: MatchCard, definitionCard: MatchCard) => {
    const nextCorrectCount = correctCount + 1
    const nextAnsweredWordKeys = new Set(answeredWordKeys)
    nextAnsweredWordKeys.add(wordCard.wordKey)
    const activeGroup = currentRoundGroups[0]
    const willClearGroup = activeGroup
      ? activeGroup.words.every(word => nextAnsweredWordKeys.has(word.key))
      : false

    setInteractionLocked(true)
    setSelectedCard(null)
    setSuccessCardIds([wordCard.id, definitionCard.id])
    setActiveLine(
      measureLine(
        groupBoardRefs.current[wordCard.groupKey],
        cardRefs.current[wordCard.id],
        cardRefs.current[definitionCard.id],
        wordCard.groupKey,
      ),
    )

    window.setTimeout(() => {
      startTransition(() => {
        setBoardCards(previousCards => previousCards.filter(card => card.wordKey !== wordCard.wordKey))
        setAnsweredWordKeys(nextAnsweredWordKeys)
        setCorrectCount(nextCorrectCount)
        setSuccessCardIds([])
        setActiveLine(null)
      })
      advanceIfRoundCleared(nextAnsweredWordKeys)
      if (!willClearGroup) {
        setInteractionLocked(false)
      }
    }, MATCH_SUCCESS_DELAY)
  }, [advanceIfRoundCleared, answeredWordKeys, correctCount, currentRoundGroups])

  const handleWrongMatch = useCallback((wordCard: MatchCard, definitionCard: MatchCard) => {
    setInteractionLocked(true)
    setSelectedCard(null)
    setWrongCount(count => count + 1)
    setErrorCardIds([wordCard.id, definitionCard.id])
    setErrorComparison({
      fromWord: wordCard.word,
      toWord: definitionCard.word,
    })
    setWarningText(`“${wordCard.word}” 和当前中文不是一组`)
    setWarningVisible(true)

    window.setTimeout(() => {
      setErrorCardIds([])
      setErrorComparison(null)
      setWarningVisible(false)
      setWarningText('')
      setInteractionLocked(false)
    }, MATCH_FAILURE_DELAY)
  }, [])

  const handleCardClick = useCallback((card: MatchCard) => {
    if (interactionLocked) return
    if (answeredWordKeys.has(card.wordKey)) return

    if (!selectedCard) {
      setSelectedCard(card)
      return
    }
    if (selectedCard.id === card.id) {
      setSelectedCard(null)
      return
    }
    if (selectedCard.side === card.side) {
      setSelectedCard(card)
      return
    }

    const wordCard = selectedCard.side === 'word' ? selectedCard : card
    const definitionCard = selectedCard.side === 'definition' ? selectedCard : card
    if (wordCard.wordKey === definitionCard.wordKey) {
      handleCorrectMatch(wordCard, definitionCard)
      return
    }
    handleWrongMatch(wordCard, definitionCard)
  }, [answeredWordKeys, handleCorrectMatch, handleWrongMatch, interactionLocked, selectedCard])

  const handleReplay = useCallback(() => {
    if (!bookId || !chapterId || !allGroups.length) return
    const nextAnsweredWordKeys = new Set<string>()
    const nextRoundGroupKeys = resolveRoundGroupKeys(allGroups, nextAnsweredWordKeys, groupsPerRound)
    const nextCards = buildRoundCards(getRoundGroups(allGroups, nextRoundGroupKeys), nextAnsweredWordKeys)
    startTransition(() => {
      setAnsweredWordKeys(nextAnsweredWordKeys)
      setCorrectCount(0)
      setWrongCount(0)
      setRoundGroupKeys(nextRoundGroupKeys)
      setBoardCards(nextCards)
      setSelectedCard(null)
      setSuccessCardIds([])
      setErrorCardIds([])
      setActiveLine(null)
      setCompletedGroup(null)
      setErrorComparison(null)
      setWarningVisible(false)
      setWarningText('')
      setInteractionLocked(false)
    })
  }, [allGroups, bookId, chapterId, groupsPerRound])

  const handleCustomCreated = useCallback((createdChapters: CustomConfusableChapter[]) => {
    if (!bookId || !createdChapters.length) return
    setBookChapters(previous => {
      const existingIds = new Set(previous.map(chapter => String(chapter.id)))
      const appended = createdChapters.filter(chapter => !existingIds.has(String(chapter.id)))
      return [...previous, ...appended]
    })
    const firstCreated = createdChapters[0]
    navigate(buildBookPracticePath({ id: bookId, practice_mode: 'match' }, firstCreated.id), {
      replace: false,
    })
    showToast(`已切换到 ${firstCreated.title}`, 'success')
  }, [bookId, navigate, showToast])

  const handleCustomUpdated = useCallback((updatedChapter: CustomConfusableChapter, words: Word[]) => {
    if (!bookId || !chapterId) return
    clearStoredChapterSnapshot(bookId, String(chapterId))
    setBookChapters(previous => previous.map(chapter => (
      String(chapter.id) === String(updatedChapter.id)
        ? { ...chapter, ...updatedChapter }
        : chapter
    )))
    resetBoardForWords(
      {
        id: updatedChapter.id,
        title: updatedChapter.title,
        word_count: updatedChapter.word_count,
        group_count: updatedChapter.group_count,
        is_custom: updatedChapter.is_custom,
      },
      words,
    )
    showToast(`已更新 ${updatedChapter.title}`, 'success')
  }, [bookId, chapterId, resetBoardForWords, showToast])

  const buildChapterPath = useCallback((nextChapterId: string | number) => {
    if (!bookId) return '/practice?mode=match'
    return buildBookPracticePath({ id: bookId, practice_mode: 'match' }, nextChapterId)
  }, [bookId])

  return {
    bookId,
    chapterId,
    supportsCustomGroups,
    loading,
    error,
    isCompleted,
    completedGroup,
    currentChapterTitle,
    correctCount,
    wrongCount,
    currentChapter,
    bookChapters,
    showWordList,
    showCustomModal,
    boardGroups,
    queuedGroups,
    selectedCard,
    activeLine,
    errorCardIds,
    successCardIds,
    answeredGroupCount,
    totalGroups,
    completedBoardGroup,
    errorComparison,
    groupBoardRefs,
    cardRefs,
    warningVisible,
    warningText,
    vocabulary,
    wordListQueue,
    wordListCurrentIndex,
    wordListStatuses,
    setShowWordList,
    setShowCustomModal,
    handleReplay,
    handleCardClick,
    handleCustomCreated,
    handleCustomUpdated,
    buildChapterPath,
    navigatePath: (path: string) => navigate(path),
    navigateToBooks: () => navigate('/books'),
    navigateToPlan: () => navigate('/plan'),
  }
}
