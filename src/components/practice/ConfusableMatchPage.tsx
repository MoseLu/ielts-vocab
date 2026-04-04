import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../../contexts'
import { apiFetch, buildApiUrl, buildBookPracticePath } from '../../lib'
import type { Chapter, ProgressData, Word } from './types'
import { buildMatchGroups, buildRoundCards, buildWordKeySet, getRoundGroups, resolveRoundGroupKeys, type MatchCard, type MatchProgressSnapshot } from './confusableMatch'
import { ConfusableMatchBoard } from './confusable/ConfusableMatchBoard'
import { ConfusableMatchHeader } from './confusable/ConfusableMatchHeader'
import { measureLine, persistChapterSnapshot, readStoredChapterSnapshot, type ActiveLine } from './confusable/confusableMatchPageHelpers'
import { ConfusableMatchCompletedState, ConfusableMatchErrorState, ConfusableMatchLoadingState, ConfusableMatchWarningOverlay } from './confusable/ConfusableMatchStatus'
import ConfusableCustomGroupsModal, { type CustomConfusableChapter } from './ConfusableCustomGroupsModal'
const MATCH_GROUPS_MOBILE = 3
const MATCH_GROUPS_DESKTOP = 4
const MATCH_SUCCESS_DELAY = 900
const MATCH_FAILURE_DELAY = 900
type ChapterProgressResponse = { chapter_progress?: Record<string, ProgressData | MatchProgressSnapshot> }
type ChapterWordsResponse = { chapter?: Chapter; words?: Word[] }
type ChaptersResponse = { chapters?: Chapter[] }
function resolveGroupsPerRound(): number {
  return window.innerWidth < 900 ? MATCH_GROUPS_MOBILE : MATCH_GROUPS_DESKTOP
}
export default function ConfusableMatchPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { showToast } = useToast()
  const bookId = searchParams.get('book')
  const chapterId = searchParams.get('chapter')
  const supportsCustomGroups = bookId === 'ielts_confusable_match'
  const [bookChapters, setBookChapters] = useState<Chapter[]>([])
  const [currentChapterTitle, setCurrentChapterTitle] = useState('')
  const [vocabulary, setVocabulary] = useState<Word[]>([])
  const [roundGroupKeys, setRoundGroupKeys] = useState<string[]>([])
  const [boardCards, setBoardCards] = useState<MatchCard[]>([])
  const [answeredWordKeys, setAnsweredWordKeys] = useState<Set<string>>(new Set())
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [groupsPerRound, setGroupsPerRound] = useState(resolveGroupsPerRound)
  const [selectedCard, setSelectedCard] = useState<MatchCard | null>(null)
  const [successCardIds, setSuccessCardIds] = useState<string[]>([])
  const [errorCardIds, setErrorCardIds] = useState<string[]>([])
  const [activeLine, setActiveLine] = useState<ActiveLine | null>(null)
  const [warningText, setWarningText] = useState('')
  const [warningVisible, setWarningVisible] = useState(false)
  const [interactionLocked, setInteractionLocked] = useState(false)
  const [showCustomModal, setShowCustomModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const groupBoardRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const persistRef = useRef('')
  const allGroups = useMemo(() => buildMatchGroups(vocabulary), [vocabulary])
  const currentRoundGroups = useMemo(
    () => getRoundGroups(allGroups, roundGroupKeys),
    [allGroups, roundGroupKeys],
  )
  const boardGroups = useMemo(() => {
    const groups = new Map<string, MatchCard[]>()
    const orderedKeys: string[] = []
    for (const card of boardCards) {
      const existing = groups.get(card.groupKey)
      if (existing) {
        existing.push(card)
        continue
      }
      groups.set(card.groupKey, [card])
      orderedKeys.push(card.groupKey)
    }
    return orderedKeys.map(key => ({
      key,
      cards: groups.get(key) ?? [],
    }))
  }, [boardCards])
  const totalWords = vocabulary.length
  const answeredCount = answeredWordKeys.size
  const isCompleted = totalWords > 0 && answeredCount >= totalWords
  const applyRound = useCallback(
    (nextRoundGroupKeys: string[], nextAnsweredWordKeys: Set<string>) => {
      const nextGroups = getRoundGroups(allGroups, nextRoundGroupKeys)
      const nextCards = buildRoundCards(nextGroups, nextAnsweredWordKeys)
      startTransition(() => {
        setRoundGroupKeys(nextRoundGroupKeys)
        setBoardCards(nextCards)
        setSelectedCard(null)
        setSuccessCardIds([])
        setErrorCardIds([])
        setActiveLine(null)
      })
    },
    [allGroups],
  )
  useEffect(() => {
    const handleResize = () => {
      setGroupsPerRound(resolveGroupsPerRound())
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      if (!bookId) {
        setError('缺少词书参数')
        setLoading(false)
        return
      }
      try {
        setLoading(true)
        setError(null)
        persistRef.current = ''
        const chaptersResponse = await fetch(buildApiUrl(`/api/books/${bookId}/chapters`))
        if (!chaptersResponse.ok) {
          throw new Error('加载章节失败')
        }
        const chaptersData = await chaptersResponse.json() as ChaptersResponse
        if (cancelled) return
        const nextChapters = chaptersData.chapters ?? []
        setBookChapters(nextChapters)
        if (!chapterId) {
          const firstChapter = nextChapters[0]
          if (!firstChapter) {
            throw new Error('未找到可练习章节')
          }
          navigate(buildBookPracticePath({ id: bookId, practice_mode: 'match' }, firstChapter.id), {
            replace: true,
          })
          return
        }
        const [chapterWordsData, progressData] = await Promise.all([
          fetch(buildApiUrl(`/api/books/${bookId}/chapters/${chapterId}`)).then(async response => {
            if (!response.ok) throw new Error('加载辨析词汇失败')
            return response.json() as Promise<ChapterWordsResponse>
          }),
          apiFetch<ChapterProgressResponse>(`/api/books/${bookId}/chapters/progress`).catch(() => ({})),
        ])
        if (cancelled) return
        const words = chapterWordsData.words ?? []
        if (words.length < 2) {
          throw new Error('当前章节词量不足，无法生成配对')
        }
        setVocabulary(words)
        setCurrentChapterTitle(chapterWordsData.chapter?.title ?? '')
        const storedSnapshot = readStoredChapterSnapshot(bookId, chapterId)
        const serverSnapshot = progressData.chapter_progress?.[String(chapterId)] as MatchProgressSnapshot | undefined
        const rawSnapshot = storedSnapshot ?? (
          Array.isArray(serverSnapshot?.answered_words) && serverSnapshot.answered_words.length > 0
            ? serverSnapshot
            : null
        )
        const baseSnapshot =
          rawSnapshot && rawSnapshot.is_completed
            ? null
            : rawSnapshot
        const groups = buildMatchGroups(words)
        const nextAnsweredWordKeys = buildWordKeySet(baseSnapshot?.answered_words)
        const nextRoundGroupKeys = resolveRoundGroupKeys(
          groups,
          nextAnsweredWordKeys,
          groupsPerRound,
          baseSnapshot?.round_group_keys,
        )
        const nextCards = buildRoundCards(
          getRoundGroups(groups, nextRoundGroupKeys),
          nextAnsweredWordKeys,
        )
        startTransition(() => {
          setAnsweredWordKeys(nextAnsweredWordKeys)
          setCorrectCount(baseSnapshot?.correct_count ?? nextAnsweredWordKeys.size)
          setWrongCount(baseSnapshot?.wrong_count ?? 0)
          setRoundGroupKeys(nextRoundGroupKeys)
          setBoardCards(nextCards)
          setSelectedCard(null)
          setSuccessCardIds([])
          setErrorCardIds([])
          setActiveLine(null)
          setWarningVisible(false)
          setWarningText('')
        })
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : '加载辨析词汇失败')
        }
      } finally {
        if (!cancelled) {
          setHydrated(true)
          setLoading(false)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [bookId, chapterId, navigate])
  useEffect(() => {
    if (!bookId || !chapterId || !hydrated || !vocabulary.length) return
    const snapshot: MatchProgressSnapshot = {
      current_index: answeredCount,
      correct_count: correctCount,
      wrong_count: wrongCount,
      is_completed: isCompleted,
      words_learned: answeredCount,
      answered_words: Array.from(answeredWordKeys).sort(),
      round_group_keys: roundGroupKeys,
      updatedAt: new Date().toISOString(),
    }
    const serialized = JSON.stringify(snapshot)
    if (serialized === persistRef.current) return
    persistRef.current = serialized
    persistChapterSnapshot(bookId, chapterId, snapshot)
    void apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
      method: 'POST',
      body: JSON.stringify({
        current_index: snapshot.current_index,
        correct_count: snapshot.correct_count,
        wrong_count: snapshot.wrong_count,
        is_completed: snapshot.is_completed,
        words_learned: snapshot.words_learned,
      }),
    }).catch(() => {})
    void apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
      method: 'POST',
      body: JSON.stringify({
        mode: 'match',
        correct_count: snapshot.correct_count,
        wrong_count: snapshot.wrong_count,
        is_completed: snapshot.is_completed,
      }),
    }).catch(() => {})
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
  const advanceIfRoundCleared = useCallback(
    (nextAnsweredWordKeys: Set<string>) => {
      const remainingInCurrentRound = currentRoundGroups.some(group =>
        group.words.some(word => !nextAnsweredWordKeys.has(word.key)),
      )
      if (remainingInCurrentRound) {
        return
      }
      const nextRoundGroupKeys = resolveRoundGroupKeys(
        allGroups,
        nextAnsweredWordKeys,
        groupsPerRound,
      )
      applyRound(nextRoundGroupKeys, nextAnsweredWordKeys)
    },
    [allGroups, applyRound, currentRoundGroups, groupsPerRound],
  )
  const handleCorrectMatch = useCallback((wordCard: MatchCard, definitionCard: MatchCard) => {
    const nextCorrectCount = correctCount + 1
    const nextAnsweredWordKeys = new Set(answeredWordKeys)
    nextAnsweredWordKeys.add(wordCard.wordKey)
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
      setInteractionLocked(false)
    }, MATCH_SUCCESS_DELAY)
  }, [advanceIfRoundCleared, answeredWordKeys, correctCount])
  const handleWrongMatch = useCallback((wordCard: MatchCard, definitionCard: MatchCard) => {
    setInteractionLocked(true)
    setSelectedCard(null)
    setWrongCount(count => count + 1)
    setErrorCardIds([wordCard.id, definitionCard.id])
    setWarningText(`“${wordCard.word}” 和当前中文不是一组`)
    setWarningVisible(true)
    window.setTimeout(() => {
      setErrorCardIds([])
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
    navigate(
      buildBookPracticePath({ id: bookId, practice_mode: 'match' }, firstCreated.id),
      { replace: false },
    )
    showToast(`已切换到 ${firstCreated.title}`, 'success')
  }, [bookId, navigate, showToast])
  if (loading) {
    return <ConfusableMatchLoadingState />
  }
  if (error || !bookId) {
    return <ConfusableMatchErrorState error={error ?? '缺少词书参数'} onBack={() => navigate('/books')} />
  }
  if (isCompleted) {
    return (
      <ConfusableMatchCompletedState
        chapterTitle={currentChapterTitle}
        correctCount={correctCount}
        wrongCount={wrongCount}
        onReplay={handleReplay}
        onBack={() => navigate('/books')}
      />
    )
  }
  return (
    <div className="practice-session-layout confusable-shell">
      <div className="confusable-stage">
        <ConfusableMatchHeader
          bookId={bookId}
          chapterId={chapterId}
          currentChapterTitle={currentChapterTitle}
          bookChapters={bookChapters}
          supportsCustomGroups={supportsCustomGroups}
          selectedCard={selectedCard}
          answeredCount={answeredCount}
          totalWords={totalWords}
          correctCount={correctCount}
          wrongCount={wrongCount}
          onOpenCustomModal={() => setShowCustomModal(true)}
          onNavigate={navigate}
          buildChapterPath={(nextChapterId) => buildBookPracticePath({ id: bookId, practice_mode: 'match' }, nextChapterId)}
        />
        <ConfusableMatchBoard
          boardGroups={boardGroups}
          selectedCard={selectedCard}
          activeLine={activeLine}
          errorCardIds={errorCardIds}
          successCardIds={successCardIds}
          groupBoardRefs={groupBoardRefs}
          cardRefs={cardRefs}
          onCardClick={handleCardClick}
        />
      </div>
      {warningVisible && <ConfusableMatchWarningOverlay warningText={warningText} />}
      {supportsCustomGroups && (
        <ConfusableCustomGroupsModal
          isOpen={showCustomModal}
          onClose={() => setShowCustomModal(false)}
          onCreated={handleCustomCreated}
        />
      )}
    </div>
  )
}
