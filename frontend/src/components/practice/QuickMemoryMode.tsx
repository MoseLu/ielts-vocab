import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import type { QuickMemoryModeProps, Word } from './types'
import { playWordAudio, prepareWordAudioPlayback, preloadWordAudioBatch, stopAudio } from './utils'
import { useToast } from '../../contexts/ToastContext'
import {
  readQuickMemoryRecordsFromStorage,
  updateQuickMemoryRecord,
  writeQuickMemoryRecordsToStorage,
  type QuickMemoryRecordState,
} from '../../lib/quickMemory'
import { buildLearningScope, type LearningScope } from '../../lib/learningScope'
import {
  reconcileQuickMemoryRecordsWithBackend,
  syncQuickMemoryRecordsToBackend,
} from '../../lib/quickMemorySync'
import { QuickMemoryCard } from './quick-memory/QuickMemoryCard'
import { QuickMemorySummary } from './quick-memory/QuickMemorySummary'
import type { QuickMemoryModeVariant, QuickMemorySessionResult as SessionResult } from '../../features/practice/quickMemorySession'
import { useQuickMemoryModeRuntime } from './quick-memory/useQuickMemoryModeRuntime'
import {
  PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT,
  PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT,
  PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT,
} from './page/practiceGlobalShortcutEvents'

const TIMER_SECONDS = 4
const TEST_HIDE_KNOWN_AFTER_MS = 2500
const TEST_AUTO_UNKNOWN_AFTER_MS = 4000
const QUICK_MEMORY_PLAYBACK_OPTIONS = { sourcePreference: 'generated' as const }
const QUICK_MEMORY_PRELOAD_OPTIONS = { includeBuffer: true, sourcePreference: 'buffer' as const }
type RevealOptions = { countAsActivity?: boolean; shouldPlayRevealAudio?: boolean; isFuzzy?: boolean }

function syncRecordToBackend(
  word: string,
  record: QuickMemoryRecordState,
  scope: LearningScope,
  modeVariant: QuickMemoryModeVariant,
): void {
  void syncQuickMemoryRecordsToBackend(
    [{ word, record }],
    { ...scope, sourceMode: modeVariant },
  ).catch(() => {})
}

export default function QuickMemoryMode({
  vocabulary,
  queue,
  settings,
  bookId,
  chapterId,
  bookChapters,
  reviewMode,
  reviewHasMore,
  onContinueReview,
  chapterGroup,
  chapterQueueWords,
  onContinueChapterGroup,
  buildChapterPath,
  onModeChange,
  onNavigate,
  onWrongWord,
  onQuickMemoryRecordChange,
  initialIndex,
  onIndexChange,
  favoriteSlot,
  modeVariant = 'quickmemory',
}: QuickMemoryModeProps) {
  const isTestMode = modeVariant === 'test'
  const { showToast } = useToast()
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<'question' | 'reveal'>('question')
  const [countdown, setCountdown] = useState(TIMER_SECONDS)
  const [choice, setChoice] = useState<'known' | 'unknown' | null>(null)
  const [questionReady, setQuestionReady] = useState(!isTestMode)
  const [knownChoiceAvailable, setKnownChoiceAvailable] = useState(true)
  const [revealWasFuzzy, setRevealWasFuzzy] = useState(false)
  const [results, setResults] = useState<SessionResult[]>([])
  const [done, setDone] = useState(false)
  const [completedSessionDurationSeconds, setCompletedSessionDurationSeconds] = useState<number | null>(null)
  const [revisitedSet, setRevisitedSet] = useState<Set<number>>(new Set())
  const countdownRef = useRef(TIMER_SECONDS)
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)
  const hideKnownTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const autoUnknownTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const questionTokenRef = useRef(0)
  const chosenRef = useRef(false)
  const wordRef = useRef<Word | undefined>(undefined)
  const continueReviewInFlightRef = useRef(false)

  const currentWord: Word | undefined = vocabulary[queue[index]]
  const queueWords = useMemo(
    () => queue.map(queueIndex => vocabulary[queueIndex]?.word).filter((word): word is string => Boolean(word)),
    [queue, vocabulary],
  )
  const quickMemoryScope = useMemo(() => buildLearningScope({ bookId, chapterId }), [bookId, chapterId])
  const showProgressSaveError = useCallback(() => {
    showToast('进度保存失败，请检查网络连接', 'error')
  }, [showToast])
  wordRef.current = currentWord

  const {
    completedSessionDurationSecondsRef,
    flushPendingRecordSync,
    pendingRecordSyncRef,
    prepareLearningSession,
    resetCurrentSessionSegment,
    resultsRef,
    sessionLoggedRef,
    syncSessionSnapshot,
  } = useQuickMemoryModeRuntime({
    modeVariant,
    bookId,
    chapterId,
    done,
    index,
    queueWords,
    queueLength: queue.length,
    chapterGroup,
    chapterQueueWords,
    reviewMode,
    results,
    quickMemoryScope,
    showSaveError: showProgressSaveError,
    onCompletedSessionDurationChange: setCompletedSessionDurationSeconds,
  })

  const clearQuestionTimers = useCallback(() => {
    clearInterval(timerRef.current)
    clearTimeout(hideKnownTimerRef.current)
    clearTimeout(autoUnknownTimerRef.current)
    hideKnownTimerRef.current = undefined
    autoUnknownTimerRef.current = undefined
  }, [])

  useEffect(() => {
    if (queue.length === 0) return
    stopAudio()
    clearQuestionTimers()
    const startIndex =
      initialIndex != null && initialIndex > 0 && initialIndex < queue.length
        ? initialIndex
        : 0
    setIndex(startIndex)
    onIndexChange?.(startIndex)
    setPhase('question')
    setCountdown(TIMER_SECONDS)
    countdownRef.current = TIMER_SECONDS
    setChoice(null)
    setQuestionReady(!isTestMode)
    setKnownChoiceAvailable(true)
    setRevealWasFuzzy(false)
    setResults([])
    resultsRef.current = []
    setDone(false)
    setRevisitedSet(new Set())
    completedSessionDurationSecondsRef.current = null
    setCompletedSessionDurationSeconds(null)
    sessionLoggedRef.current = false
    resetCurrentSessionSegment()
  }, [bookId, chapterId, clearQuestionTimers, initialIndex, isTestMode, modeVariant, onIndexChange, queue.length, resetCurrentSessionSegment])

  const reveal = useCallback(async (picked: 'known' | 'unknown', options: RevealOptions = {}) => {
    if (chosenRef.current) return
    chosenRef.current = true
    clearQuestionTimers()
    stopAudio()
    const countAsActivity = options.countAsActivity ?? true
    const shouldPlayRevealAudio = options.shouldPlayRevealAudio ?? (countAsActivity && !isTestMode)
    const answeredWord = currentWord
    if (shouldPlayRevealAudio && answeredWord) {
      void playWordAudio(answeredWord.word, settings, () => {}, QUICK_MEMORY_PLAYBACK_OPTIONS)
    }

    const actionAt = Date.now()
    const isFuzzy = options.isFuzzy ?? revisitedSet.has(index)

    setChoice(picked)
    setRevealWasFuzzy(isFuzzy)
    setPhase('reveal')

    const { records, record } = updateQuickMemoryRecord(
      readQuickMemoryRecordsFromStorage(undefined, quickMemoryScope),
      answeredWord?.word ?? '',
      picked,
      isFuzzy,
      quickMemoryScope,
    )
    writeQuickMemoryRecordsToStorage(records, undefined, quickMemoryScope)
    const wordKey = (answeredWord?.word ?? '').toLowerCase()
    if (wordKey && record) {
      pendingRecordSyncRef.current[wordKey] = record
      syncRecordToBackend(wordKey, record, quickMemoryScope, modeVariant)
    }
    if (answeredWord && record) {
      onQuickMemoryRecordChange?.(answeredWord, record)
    }

    const prevResults = resultsRef.current
    const existing = prevResults.findIndex(result => result.wordIdx === index)
    const entry: SessionResult = { wordIdx: index, choice: picked, wasFuzzy: isFuzzy }
    const nextResults = existing >= 0
      ? prevResults.map((result, resultIndex) => (resultIndex === existing ? entry : result))
      : [...prevResults, entry]
    resultsRef.current = nextResults
    setResults(nextResults)

    if (picked === 'unknown' && answeredWord) {
      onWrongWord(answeredWord)
    }

    if (countAsActivity) {
      await prepareLearningSession(actionAt)
    }

    syncSessionSnapshot({
      ...(countAsActivity ? { activeAt: actionAt } : {}),
      wordsStudied: nextResults.length,
      correctCount: nextResults.filter(result => result.choice === 'known').length,
      wrongCount: nextResults.filter(result => result.choice === 'unknown').length,
    })
  }, [clearQuestionTimers, currentWord, index, isTestMode, modeVariant, onQuickMemoryRecordChange, onWrongWord, prepareLearningSession, quickMemoryScope, revisitedSet, settings, syncSessionSnapshot])

  const beginAutoUnknownReveal = useCallback(() => {
    if (chosenRef.current) return
    void reveal('unknown')
  }, [reveal])

  const startQuestionCountdown = useCallback(() => {
    clearQuestionTimers()
    setQuestionReady(true)
    setCountdown(TIMER_SECONDS)
    countdownRef.current = TIMER_SECONDS
    if (isTestMode) {
      const startedAt = Date.now()
      timerRef.current = setInterval(() => {
        const elapsedSeconds = (Date.now() - startedAt) / 1000
        const nextCountdown = Math.max(Math.ceil(TIMER_SECONDS - elapsedSeconds), 0)
        countdownRef.current = nextCountdown
        setCountdown(nextCountdown)
        if (nextCountdown === 0) clearInterval(timerRef.current)
      }, 250)
      hideKnownTimerRef.current = setTimeout(() => {
        if (!chosenRef.current) setKnownChoiceAvailable(false)
      }, TEST_HIDE_KNOWN_AFTER_MS)
      autoUnknownTimerRef.current = setTimeout(() => {
        if (!chosenRef.current) beginAutoUnknownReveal()
      }, TEST_AUTO_UNKNOWN_AFTER_MS)
      return
    }

    timerRef.current = setInterval(() => {
      const nextCountdown = Math.max(countdownRef.current - 1, 0)
      countdownRef.current = nextCountdown
      setCountdown(nextCountdown)
      if (nextCountdown === 0) {
        clearInterval(timerRef.current)
        beginAutoUnknownReveal()
      }
    }, 1000)
  }, [beginAutoUnknownReveal, clearQuestionTimers, isTestMode])

  useEffect(() => {
    if (phase !== 'question' || !currentWord) return

    const questionToken = questionTokenRef.current + 1
    questionTokenRef.current = questionToken
    const activeWord = currentWord.word
    chosenRef.current = false
    setCountdown(TIMER_SECONDS)
    countdownRef.current = TIMER_SECONDS
    setQuestionReady(!isTestMode)
    setKnownChoiceAvailable(true)
    setRevealWasFuzzy(false)
    clearQuestionTimers()
    void prepareWordAudioPlayback(currentWord.word, QUICK_MEMORY_PRELOAD_OPTIONS)

    const upcomingWords = queue
      .slice(index + 1, index + 4)
      .map(queueIndex => vocabulary[queueIndex]?.word?.trim())
      .filter((word): word is string => Boolean(word))
    if (upcomingWords.length) {
      void preloadWordAudioBatch(upcomingWords, upcomingWords.length, QUICK_MEMORY_PRELOAD_OPTIONS)
    }

    if (isTestMode) {
      const startAfterAudio = () => {
        if (
          !chosenRef.current
          && questionTokenRef.current === questionToken
          && wordRef.current?.word === activeWord
        ) {
          startQuestionCountdown()
        }
      }
      void playWordAudio(activeWord, settings, startAfterAudio, QUICK_MEMORY_PLAYBACK_OPTIONS).then(started => {
        if (!started) startAfterAudio()
      })
      return () => { questionTokenRef.current += 1; clearQuestionTimers() }
    }

    startQuestionCountdown()
    return () => {
      clearQuestionTimers()
    }
  }, [clearQuestionTimers, currentWord?.word, index, isTestMode, phase, queue, reviewMode, settings, startQuestionCountdown, vocabulary])

  useEffect(() => {
    void reconcileQuickMemoryRecordsWithBackend().catch(() => {})
  }, [])

  useEffect(() => () => {
    stopAudio()
    clearQuestionTimers()
  }, [clearQuestionTimers])

  const handleNext = useCallback(async () => {
    stopAudio()
    clearQuestionTimers()
    const next = index + 1
    if (next >= queue.length) {
      setDone(true)
      return
    }
    await prepareLearningSession()
    setIndex(next)
    onIndexChange?.(next)
    setPhase('question')
    setChoice(null)
    setQuestionReady(!isTestMode)
    setKnownChoiceAvailable(true)
    setRevealWasFuzzy(false)
  }, [clearQuestionTimers, index, isTestMode, onIndexChange, prepareLearningSession, queue.length])

  const handlePrev = useCallback(async () => {
    if (index === 0) return
    await prepareLearningSession()
    stopAudio()
    clearQuestionTimers()
    const prev = index - 1
    setRevisitedSet(current => {
      const nextSet = new Set(current)
      nextSet.add(prev)
      return nextSet
    })
    setIndex(prev)
    onIndexChange?.(prev)
    setPhase('question')
    setChoice(null)
    setQuestionReady(!isTestMode)
    setKnownChoiceAvailable(true)
    setRevealWasFuzzy(false)
  }, [clearQuestionTimers, index, isTestMode, onIndexChange, prepareLearningSession])

  const replayCurrentWord = useCallback(() => {
    if (!wordRef.current) return
    clearQuestionTimers()
    setCountdown(TIMER_SECONDS)
    countdownRef.current = TIMER_SECONDS
    if (phase === 'question') {
      stopAudio()
      const replayToken = questionTokenRef.current + 1
      questionTokenRef.current = replayToken
      const replayWord = wordRef.current.word
      setQuestionReady(!isTestMode)
      setKnownChoiceAvailable(true)
      void playWordAudio(replayWord, settings, () => {
        if (!chosenRef.current && questionTokenRef.current === replayToken && wordRef.current?.word === replayWord) {
          startQuestionCountdown()
        }
      }, QUICK_MEMORY_PLAYBACK_OPTIONS).then(started => {
        if (!started && !chosenRef.current && questionTokenRef.current === replayToken && wordRef.current?.word === replayWord) {
          startQuestionCountdown()
        }
      })
      return
    }
    void playWordAudio(wordRef.current.word, settings, () => {}, QUICK_MEMORY_PLAYBACK_OPTIONS)
  }, [clearQuestionTimers, isTestMode, phase, settings, startQuestionCountdown])

  useEffect(() => {
    const handlePreviousShortcut = () => { void handlePrev() }
    const handleNextShortcut = () => {
      if (phase === 'question') {
        if (isTestMode && (!questionReady || !knownChoiceAvailable)) return
        void reveal('known')
        return
      }
      void handleNext()
    }
    window.addEventListener(PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT, handlePreviousShortcut)
    window.addEventListener(PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT, handleNextShortcut)
    window.addEventListener(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT, replayCurrentWord)
    return () => {
      window.removeEventListener(PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT, handlePreviousShortcut)
      window.removeEventListener(PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT, handleNextShortcut)
      window.removeEventListener(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT, replayCurrentWord)
    }
  }, [handleNext, handlePrev, isTestMode, knownChoiceAvailable, phase, questionReady, replayCurrentWord, reveal])

  const handleRestart = useCallback(() => {
    stopAudio()
    clearQuestionTimers()
    setIndex(0)
    onIndexChange?.(0)
    setPhase('question')
    setChoice(null)
    setQuestionReady(!isTestMode)
    setKnownChoiceAvailable(true)
    setRevealWasFuzzy(false)
    setResults([])
    resultsRef.current = []
    setRevisitedSet(new Set())
    completedSessionDurationSecondsRef.current = null
    setCompletedSessionDurationSeconds(null)
    sessionLoggedRef.current = false
    resetCurrentSessionSegment()
    setDone(false)
  }, [clearQuestionTimers, isTestMode, onIndexChange, resetCurrentSessionSegment])

  const handleContinueReview = useCallback(async () => {
    if (!onContinueReview || continueReviewInFlightRef.current) return
    continueReviewInFlightRef.current = true
    try {
      await flushPendingRecordSync()
      await reconcileQuickMemoryRecordsWithBackend({ force: true })
      onContinueReview()
    } catch {
      showToast('复习记录同步失败，请稍后重试', 'error')
    } finally {
      continueReviewInFlightRef.current = false
    }
  }, [flushPendingRecordSync, onContinueReview, showToast])

  if (!currentWord && !done) {
    return <div className="qm-empty">暂无单词</div>
  }

  if (done) {
    return (
      <QuickMemorySummary
        results={results}
        vocabulary={vocabulary}
        queue={queue}
        bookId={bookId}
        chapterId={chapterId}
        bookChapters={bookChapters}
        reviewMode={reviewMode}
        reviewHasMore={reviewHasMore}
        onContinueReview={onContinueReview ? handleContinueReview : undefined}
        chapterGroup={chapterGroup}
        onContinueChapterGroup={onContinueChapterGroup}
        buildChapterPath={buildChapterPath}
        sessionDurationSeconds={completedSessionDurationSeconds}
        modeVariant={modeVariant}
        onRestart={handleRestart}
        onModeChange={onModeChange}
        onNavigate={onNavigate}
      />
    )
  }

  if (!currentWord) {
    return <div className="qm-empty">暂无单词</div>
  }

  const progress = (index / queue.length) * 100
  const replayWordHint = '点击右上角喇叭或按 Tab 重播发音'

  return (
    <QuickMemoryCard
      modeVariant={modeVariant}
      phase={phase}
      countdown={countdown}
      totalSeconds={TIMER_SECONDS}
      progressPercent={progress}
      currentPosition={index + 1}
      totalCount={queue.length}
      currentWord={currentWord}
      choice={choice}
      wasFuzzy={revealWasFuzzy}
      questionReady={questionReady}
      knownChoiceAvailable={knownChoiceAvailable}
      favoriteSlot={favoriteSlot}
      replayWordHint={replayWordHint}
      canGoPrev={index > 0}
      isLast={index + 1 >= queue.length}
      onReplay={replayCurrentWord}
      onKnown={() => { void reveal('known') }}
      onFamiliar={() => { void reveal('unknown', { isFuzzy: true }) }}
      onUnknown={() => { void reveal('unknown') }}
      onPrev={() => { void handlePrev() }}
      onNext={() => { void handleNext() }}
    />
  )
}
