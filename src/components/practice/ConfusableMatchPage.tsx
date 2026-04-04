import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../../contexts'
import { STORAGE_KEYS } from '../../constants'
import { apiFetch, buildApiUrl, buildBookPracticePath } from '../../lib'
import Popover from '../ui/Popover'
import { Scrollbar } from '../ui/Scrollbar'
import { PageSkeleton } from '../ui'
import type { Chapter, ProgressData, Word } from './types'
import {
  buildMatchGroups,
  buildRoundCards,
  buildWordKeySet,
  getRoundGroups,
  resolveRoundGroupKeys,
  type MatchCard,
  type MatchProgressSnapshot,
} from './confusableMatch'
import ConfusableCustomGroupsModal, {
  type CustomConfusableChapter,
} from './ConfusableCustomGroupsModal'

const MATCH_GROUPS_MOBILE = 3
const MATCH_GROUPS_DESKTOP = 4
const MATCH_SUCCESS_DELAY = 900
const MATCH_FAILURE_DELAY = 900

type ChapterProgressResponse = {
  chapter_progress?: Record<string, ProgressData | MatchProgressSnapshot>
}

type ChapterWordsResponse = {
  chapter?: Chapter
  words?: Word[]
}

type ChaptersResponse = {
  chapters?: Chapter[]
}

type ActiveLine = {
  id: string
  groupKey: string
  path: string
}

function readStoredChapterSnapshot(bookId: string, chapterId: string): MatchProgressSnapshot | null {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEYS.CHAPTER_PROGRESS) || '{}') as Record<
      string,
      MatchProgressSnapshot
    >
    return raw[`${bookId}_${chapterId}`] ?? null
  } catch {
    return null
  }
}

function persistChapterSnapshot(
  bookId: string,
  chapterId: string,
  snapshot: MatchProgressSnapshot,
) {
  const key = `${bookId}_${chapterId}`
  const current = (() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.CHAPTER_PROGRESS) || '{}') as Record<
        string,
        MatchProgressSnapshot
      >
    } catch {
      return {}
    }
  })()

  current[key] = {
    ...snapshot,
    updatedAt: new Date().toISOString(),
  }

  localStorage.setItem(STORAGE_KEYS.CHAPTER_PROGRESS, JSON.stringify(current))
}

function resolveGroupsPerRound(): number {
  return window.innerWidth < 900 ? MATCH_GROUPS_MOBILE : MATCH_GROUPS_DESKTOP
}

function measureLine(
  boardElement: HTMLDivElement | null,
  fromElement: HTMLElement | null,
  toElement: HTMLElement | null,
  groupKey: string,
): ActiveLine | null {
  if (!boardElement || !fromElement || !toElement) return null

  const boardRect = boardElement.getBoundingClientRect()
  const fromRect = fromElement.getBoundingClientRect()
  const toRect = toElement.getBoundingClientRect()

  const x1 = fromRect.left + fromRect.width / 2 - boardRect.left
  const y1 = fromRect.top + fromRect.height / 2 - boardRect.top
  const x2 = toRect.left + toRect.width / 2 - boardRect.left
  const y2 = toRect.top + toRect.height / 2 - boardRect.top
  const railY = Math.max(14, Math.min(y1, y2) - 24)

  return {
    id: `${fromElement.dataset.cardId ?? 'from'}-${toElement.dataset.cardId ?? 'to'}`,
    groupKey,
    path: `M ${x1} ${y1} L ${x1} ${railY} L ${x2} ${railY} L ${x2} ${y2}`,
  }
}

function getSelectionHint(selectedCard: MatchCard | null): string {
  if (!selectedCard) {
    return '每个小棋盘只包含一组易混词，优先在同组内完成消除。'
  }

  if (selectedCard.side === 'word') {
    return `继续点击对应中文：${selectedCard.word}`
  }

  return `继续点击对应英文：${selectedCard.label}`
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
    return (
      <div className="practice-session-layout">
        <PageSkeleton variant="practice" />
      </div>
    )
  }

  if (error || !bookId) {
    return (
      <div className="practice-session-layout confusable-shell">
        <div className="practice-complete confusable-empty">
          <div className="complete-emoji" aria-hidden="true">!</div>
          <h2>无法进入辨析模式</h2>
          <p>{error ?? '缺少词书参数'}</p>
          <button className="complete-btn" onClick={() => navigate('/books')}>返回词书</button>
        </div>
      </div>
    )
  }

  if (isCompleted) {
    return (
      <div className="practice-session-layout confusable-shell">
        <div className="practice-complete confusable-empty">
          <div className="complete-emoji" aria-hidden="true">✓</div>
          <h2>{currentChapterTitle || '本章'}已完成</h2>
          <div className="complete-stats-row">
            <span className="stat-correct">配对成功 {correctCount}</span>
            <span className="stat-wrong">误连 {wrongCount}</span>
          </div>
          <button className="complete-btn" onClick={handleReplay}>再来一轮</button>
          <button className="complete-btn" onClick={() => navigate('/books')}>返回词书</button>
        </div>
      </div>
    )
  }

  return (
    <div className="practice-session-layout confusable-shell">
      <div className="practice-ctrl-bar confusable-ctrl-bar">
        <button
          type="button"
          className="practice-ctrl-brand"
          onClick={() => navigate('/books')}
          title="返回词书"
        >
          <img
            src="/images/logo.png"
            alt="Logo"
            className="practice-ctrl-brand-logo"
            onError={(event) => { event.currentTarget.style.display = 'none' }}
          />
          <span className="practice-ctrl-brand-text">易混辨析</span>
        </button>

        <div className="practice-ctrl-right">
          {supportsCustomGroups && (
            <button
              type="button"
              className="confusable-toolbar-btn"
              onClick={() => setShowCustomModal(true)}
            >
              自定义组
            </button>
          )}

          <Popover
            placement="bottom"
            offset={10}
            panelClassName="popover-ctx-panel"
            trigger={
              <button className="practice-ctrl-icon-btn practice-mode-btn" title="切换章节">
                <span className="practice-mode-label">{currentChapterTitle || '选择章节'}</span>
                <svg className="practice-ctx-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
            }
          >
            <Scrollbar className="popover-ctx-scroll" maxHeight={320}>
              {bookChapters.map(chapter => (
                <button
                  key={chapter.id}
                  className={`popover-option ${String(chapter.id) === String(chapterId) ? 'active' : ''}`}
                  onClick={() => navigate(buildBookPracticePath({ id: bookId, practice_mode: 'match' }, chapter.id))}
                >
                  <span className={`ctx-radio ${String(chapter.id) === String(chapterId) ? 'checked' : ''}`} />
                  {chapter.title}
                </button>
              ))}
            </Scrollbar>
          </Popover>

          <div className="confusable-progress-chip">
            <strong>{answeredCount}</strong>
            <span>/ {totalWords} 已消除</span>
          </div>
        </div>
      </div>

      <div className="confusable-stage">
        <div className="confusable-stage-header">
          <div>
            <h1 className="confusable-title">{currentChapterTitle || '易混词辨析'}</h1>
            <p className="confusable-subtitle">
              每个小棋盘就是一组易混词。先点英文，再点中文，组内连线成功后就会像消消乐一样消失。
            </p>
          </div>
          <div className="confusable-stats">
            <span className="confusable-stat confusable-stat--ok">成功 {correctCount}</span>
            <span className="confusable-stat confusable-stat--bad">误连 {wrongCount}</span>
          </div>
        </div>

        <div className={`confusable-selection-tray ${selectedCard ? 'is-active' : ''}`}>
          <div>
            <span className="confusable-selection-label">当前连线</span>
            <strong>{selectedCard ? '已选中一张卡片' : '从任意小棋盘开始'}</strong>
            <span>{getSelectionHint(selectedCard)}</span>
          </div>
          {selectedCard && (
            <span className={`confusable-selection-token confusable-selection-token--${selectedCard.side}`}>
              {selectedCard.side === 'word' ? `EN · ${selectedCard.label}` : `中 · ${selectedCard.label}`}
            </span>
          )}
        </div>

        <div className="confusable-board">
          <div className="confusable-group-grid">
            {boardGroups.map((group, index) => {
              const isSelectedGroup = selectedCard?.groupKey === group.key
              const isSuccessGroup = activeLine?.groupKey === group.key
              const isErrorGroup = group.cards.some(card => errorCardIds.includes(card.id))

              return (
                <section
                  key={group.key}
                  className={[
                    'confusable-group-panel',
                    isSelectedGroup ? 'is-selected' : '',
                    isSuccessGroup ? 'is-success' : '',
                    isErrorGroup ? 'is-error' : '',
                  ].filter(Boolean).join(' ')}
                  aria-label={`易混组 ${index + 1}`}
                >
                  <div className="confusable-group-head">
                    <span className="confusable-group-label">易混组 {index + 1}</span>
                    <span className="confusable-group-meta">{Math.max(1, group.cards.length / 2)} 对待消除</span>
                  </div>

                  <div
                    className="confusable-group-board"
                    ref={element => { groupBoardRefs.current[group.key] = element }}
                  >
                    <svg className="confusable-lines" aria-hidden="true">
                      {activeLine?.groupKey === group.key && (
                        <path
                          d={activeLine.path}
                          className="confusable-line confusable-line--success"
                        />
                      )}
                    </svg>

                    <div className="confusable-card-grid">
                      {group.cards.map(card => {
                        const isSelected = selectedCard?.id === card.id
                        const isSuccess = successCardIds.includes(card.id)
                        const isError = errorCardIds.includes(card.id)

                        return (
                          <button
                            key={card.id}
                            ref={element => { cardRefs.current[card.id] = element }}
                            type="button"
                            data-card-id={card.id}
                            className={[
                              'confusable-card',
                              `confusable-card--${card.side}`,
                              isSelected ? 'is-selected' : '',
                              isSuccess ? 'is-success' : '',
                              isError ? 'is-error' : '',
                            ].filter(Boolean).join(' ')}
                            onClick={() => handleCardClick(card)}
                          >
                            <span className={`confusable-card-badge confusable-card-badge--${card.side}`}>
                              {card.side === 'word' ? 'EN' : '中'}
                            </span>
                            {card.side === 'word' ? (
                              <>
                                <span className="confusable-card-word">{card.label}</span>
                                {card.phonetic && (
                                  <span className="confusable-card-phonetic">{card.phonetic}</span>
                                )}
                              </>
                            ) : (
                              <span className="confusable-card-definition">{card.label}</span>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </section>
              )
            })}
          </div>
        </div>
      </div>

      {warningVisible && (
        <div className="confusable-warning-overlay" role="alert" aria-live="assertive">
          <div className="confusable-warning-card">
            <span className="confusable-warning-label">配对错误</span>
            <strong>{warningText}</strong>
            <span>当前小棋盘里的两组词很接近，再看一眼再连。</span>
          </div>
        </div>
      )}

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
