import { useState, useEffect, useRef, useCallback } from 'react'
import type { QuickMemoryModeProps, Word } from './types'
import { playWordAudio, preloadWordAudioBatch, stopAudio } from './utils'
import { useToast } from '../../contexts/ToastContext'
import {
  readQuickMemoryRecordsFromStorage,
  updateQuickMemoryRecord,
  writeQuickMemoryRecordsToStorage,
  type QuickMemoryRecordState,
} from '../../lib/quickMemory'
import {
  reconcileQuickMemoryRecordsWithBackend,
  syncQuickMemoryRecordsToBackend,
} from '../../lib/quickMemorySync'
import { QuickMemoryCountdownRing } from './quick-memory/QuickMemoryCountdownRing'
import {
  QuickMemorySummary,
  type QuickMemorySessionResult as SessionResult,
} from './quick-memory/QuickMemorySummary'
import { useQuickMemoryModeSession } from './quick-memory/useQuickMemoryModeSession'
import { useQuickMemorySession } from '../../composables/practice/quick-memory/useQuickMemorySession'
import {
  PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT,
  PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT,
  PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT,
} from './page/practiceGlobalShortcutEvents'

const TIMER_SECONDS = 4

function syncRecordToBackend(word: string, record: QuickMemoryRecordState): void {
  void syncQuickMemoryRecordsToBackend([{ word, record }]).catch(() => {})
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
  buildChapterPath,
  onModeChange,
  onNavigate,
  onWrongWord,
  onQuickMemoryRecordChange,
  initialIndex,
  onIndexChange,
  favoriteSlot,
}: QuickMemoryModeProps) {
  const { showToast } = useToast()
  const [index, setIndex] = useState(0)
  const hasRestoredIndexRef = useRef(false)
  const [phase, setPhase] = useState<'question' | 'reveal'>('question')
  const [countdown, setCountdown] = useState(TIMER_SECONDS)
  const [choice, setChoice] = useState<'known' | 'unknown' | null>(null)
  const [results, setResults] = useState<SessionResult[]>([])
  const [done, setDone] = useState(false)
  const [revisitedSet, setRevisitedSet] = useState<Set<number>>(new Set())
  const resultsRef = useRef<SessionResult[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const chosenRef = useRef(false)
  const wordRef = useRef<Word | undefined>(undefined)
  const sessionStartRef = useRef(0)
  const sessionLastActiveAtRef = useRef(0)
  const completedSessionDurationSecondsRef = useRef<number | null>(null)
  const bookIdRef = useRef<string | null>(bookId)
  const chapterIdRef = useRef<string | null>(chapterId)
  const sessionIdRef = useRef<number | null>(null)
  const sessionLoggedRef = useRef(false)
  const pendingRecordSyncRef = useRef<Record<string, QuickMemoryRecordState>>({})
  const recordSyncInFlightRef = useRef(false)

  const currentWord: Word | undefined = vocabulary[queue[index]]
  wordRef.current = currentWord

  const {
    completeCurrentSession,
    flushPendingRecordSync,
    isCurrentSessionActive,
    prepareLearningSession,
    resetCurrentSessionSegment,
    syncSessionSnapshot,
  } = useQuickMemoryModeSession({
    bookId,
    chapterId,
    bookIdRef,
    chapterIdRef,
    resultsRef,
    sessionStartRef,
    sessionLastActiveAtRef,
    completedSessionDurationSecondsRef,
    sessionIdRef,
    sessionLoggedRef,
    pendingRecordSyncRef,
    recordSyncInFlightRef,
  })

  useQuickMemorySession({
    bookId,
    chapterId,
    done,
    index,
    queueLength: queue.length,
    reviewMode,
    results,
    resultsRef,
    sessionStartRef,
    sessionLastActiveAtRef,
    completedSessionDurationSecondsRef,
    bookIdRef,
    chapterIdRef,
    sessionIdRef,
    sessionLoggedRef,
    flushPendingRecordSync,
    completeCurrentSession,
    syncSessionSnapshot,
    showSaveError: () => showToast('进度保存失败，请检查网络连接', 'error'),
  })

  useEffect(() => {
    if (queue.length === 0) return
    stopAudio()
    clearInterval(timerRef.current)
    clearTimeout(revealTimerRef.current)
    const startIndex =
      !hasRestoredIndexRef.current && initialIndex != null && initialIndex > 0 && initialIndex < queue.length
        ? initialIndex
        : 0
    hasRestoredIndexRef.current = true
    setIndex(startIndex)
    onIndexChange?.(startIndex)
    setPhase('question')
    setCountdown(TIMER_SECONDS)
    setChoice(null)
    setResults([])
    resultsRef.current = []
    setDone(false)
    setRevisitedSet(new Set())
    completedSessionDurationSecondsRef.current = null
    sessionLoggedRef.current = false
    resetCurrentSessionSegment()
  }, [bookId, chapterId, onIndexChange, queue.length, resetCurrentSessionSegment])

  const reveal = useCallback(async (
    picked: 'known' | 'unknown',
    countAsActivity = true,
    shouldPlayRevealAudio = true,
  ) => {
    if (chosenRef.current) return
    chosenRef.current = true
    clearInterval(timerRef.current)
    clearTimeout(revealTimerRef.current)
    stopAudio()

    const actionAt = Date.now()
    if (countAsActivity) {
      await prepareLearningSession(actionAt)
    }

    const isFuzzy = revisitedSet.has(index)

    setChoice(picked)
    setPhase('reveal')

    const { records, record } = updateQuickMemoryRecord(
      readQuickMemoryRecordsFromStorage(),
      currentWord?.word ?? '',
      picked,
      isFuzzy,
      {
        bookId: bookId ?? undefined,
        chapterId: chapterId ?? (currentWord?.chapter_id != null ? String(currentWord.chapter_id) : undefined),
      },
    )
    writeQuickMemoryRecordsToStorage(records)
    const wordKey = (currentWord?.word ?? '').toLowerCase()
    if (wordKey && record) {
      pendingRecordSyncRef.current[wordKey] = record
      syncRecordToBackend(wordKey, record)
    }
    if (currentWord && record) {
      onQuickMemoryRecordChange?.(currentWord, record)
    }

    const prevResults = resultsRef.current
    const existing = prevResults.findIndex(result => result.wordIdx === index)
    const entry: SessionResult = { wordIdx: index, choice: picked, wasFuzzy: isFuzzy }
    const nextResults = existing >= 0
      ? prevResults.map((result, resultIndex) => (resultIndex === existing ? entry : result))
      : [...prevResults, entry]
    resultsRef.current = nextResults
    setResults(nextResults)
    syncSessionSnapshot({
      ...(countAsActivity ? { activeAt: actionAt } : {}),
      wordsStudied: nextResults.length,
      correctCount: nextResults.filter(result => result.choice === 'known').length,
      wrongCount: nextResults.filter(result => result.choice === 'unknown').length,
    })

    if (picked === 'unknown' && currentWord) {
      onWrongWord(currentWord)
    }

    if (shouldPlayRevealAudio) {
      revealTimerRef.current = setTimeout(() => {
        if (wordRef.current) void playWordAudio(wordRef.current.word, settings, () => {})
      }, 350)
    }
  }, [
    bookId,
    chapterId,
    currentWord,
    index,
    onQuickMemoryRecordChange,
    onWrongWord,
    prepareLearningSession,
    revisitedSet,
    settings,
    syncSessionSnapshot,
  ])

  const startQuestionCountdown = useCallback(() => {
    clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current)
          if (isCurrentSessionActive()) {
            void reveal('unknown', false)
          }
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [isCurrentSessionActive, reveal])

  useEffect(() => {
    if (phase !== 'question' || !currentWord) return

    chosenRef.current = false
    setCountdown(TIMER_SECONDS)
    clearInterval(timerRef.current)

    const upcomingWords = queue
      .slice(index + 1, index + 4)
      .map(queueIndex => vocabulary[queueIndex]?.word?.trim())
      .filter((word): word is string => Boolean(word))
    if (upcomingWords.length && (!reviewMode || index > 0)) {
      void preloadWordAudioBatch(upcomingWords)
    }

    startQuestionCountdown()

    return () => {
      clearInterval(timerRef.current)
    }
  }, [currentWord?.word, index, phase, queue, reviewMode, startQuestionCountdown, vocabulary])

  useEffect(() => {
    void reconcileQuickMemoryRecordsWithBackend().catch(() => {})
  }, [])

  useEffect(() => () => {
    stopAudio()
    clearInterval(timerRef.current)
    clearTimeout(revealTimerRef.current)
  }, [])

  const handleNext = useCallback(async () => {
    await prepareLearningSession()
    clearTimeout(revealTimerRef.current)
    stopAudio()
    const next = index + 1
    if (next >= queue.length) {
      completedSessionDurationSecondsRef.current = await completeCurrentSession()
      setDone(true)
      return
    }
    setIndex(next)
    onIndexChange?.(next)
    setPhase('question')
    setChoice(null)
  }, [completeCurrentSession, index, onIndexChange, prepareLearningSession, queue.length])

  const handlePrev = useCallback(async () => {
    if (index === 0) return
    await prepareLearningSession()
    clearTimeout(revealTimerRef.current)
    stopAudio()
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
  }, [index, onIndexChange, prepareLearningSession])

  const replayCurrentWord = useCallback(() => {
    if (!wordRef.current) return
    clearTimeout(revealTimerRef.current)
    clearInterval(timerRef.current)
    setCountdown(TIMER_SECONDS)
    if (phase === 'question') {
      stopAudio()
      const replayWord = wordRef.current.word
      void playWordAudio(replayWord, settings, () => {
        if (!chosenRef.current && wordRef.current?.word === replayWord) {
          startQuestionCountdown()
        }
      }).then(started => {
        if (!started && !chosenRef.current && wordRef.current?.word === replayWord) {
          startQuestionCountdown()
        }
      })
      return
    }
    void playWordAudio(wordRef.current.word, settings, () => {})
  }, [phase, settings, startQuestionCountdown])

  useEffect(() => {
    const handlePreviousShortcut = () => { void handlePrev() }
    const handleNextShortcut = () => {
      if (phase === 'question') {
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
  }, [phase, reveal, handlePrev, handleNext, replayCurrentWord])

  const handleRestart = useCallback(() => {
    stopAudio()
    setIndex(0)
    onIndexChange?.(0)
    setPhase('question')
    setChoice(null)
    setResults([])
    resultsRef.current = []
    setRevisitedSet(new Set())
    completedSessionDurationSecondsRef.current = null
    sessionLoggedRef.current = false
    resetCurrentSessionSegment()
    setDone(false)
  }, [onIndexChange, resetCurrentSessionSegment])

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
        onContinueReview={onContinueReview}
        buildChapterPath={buildChapterPath}
        sessionDurationSeconds={completedSessionDurationSecondsRef.current}
        onRestart={handleRestart}
        onModeChange={onModeChange}
        onNavigate={onNavigate}
      />
    )
  }

  const progress = (index / queue.length) * 100

  return (
    <div className="qm-root">
      <div className="qm-stage">
        <div className="qm-progress-track">
          <div className="qm-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="qm-progress-label">{index + 1} / {queue.length}</div>

        <div className={`qm-card ${phase === 'reveal' ? 'qm-card--reveal' : ''}`}>
          {favoriteSlot ? (
            <div className={`qm-card-toolbar${phase === 'question' ? ' qm-card-toolbar--question' : ''}`}>
              {phase === 'question' ? <div className="qm-card-toolbar__spacer" /> : null}
              <div className="qm-card-toolbar__action">{favoriteSlot}</div>
            </div>
          ) : null}
          {phase === 'question' && (
            <>
              <div className="qm-countdown-ring">
                <QuickMemoryCountdownRing seconds={countdown} total={TIMER_SECONDS} />
              </div>

              <div className="qm-word">{currentWord.word}</div>

              <p className="qm-hint">你认识这个单词吗？</p>

              <div className="qm-choice-row">
                <button
                  className="qm-btn qm-btn--unknown"
                  onClick={() => { void reveal('unknown') }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  不认识
                </button>
                <button
                  className="qm-btn qm-btn--known"
                  onClick={() => { void reveal('known') }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  认识
                </button>
              </div>
              <div className="qm-key-hints">
                {index > 0 && <span className="qm-key-hint"><kbd>←</kbd> 上一个</span>}
                <span className="qm-key-hint"><kbd>→</kbd> 认识</span>
                <span className="qm-key-hint"><kbd>Tab</kbd> 重播发音</span>
              </div>
            </>
          )}

          {phase === 'reveal' && currentWord && (
            <>
              <div className={`qm-result-badge ${choice === 'known' ? 'qm-badge--known' : 'qm-badge--unknown'}${revisitedSet.has(index) ? ' qm-badge--fuzzy' : ''}`}>
                {choice === 'known' ? '✓ 认识' : '✗ 不认识'}
                {revisitedSet.has(index) && <span className="qm-badge-fuzzy-tag">模糊</span>}
              </div>

              <div className="qm-word">{currentWord.word}</div>

              {currentWord.phonetic && (
                <div className="qm-phonetic">{currentWord.phonetic}</div>
              )}

              {currentWord.pos && (
                <span className="qm-pos">{currentWord.pos}</span>
              )}

              <div className="qm-definition">{currentWord.definition}</div>

              <div className="qm-nav-row">
                {index > 0 && (
                  <button className="qm-btn-prev" onClick={() => { void handlePrev() }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M15 18l-6-6 6-6"/>
                    </svg>
                    上一个
                  </button>
                )}
                <button className="qm-btn-next" onClick={() => { void handleNext() }}>
                  {index + 1 < queue.length ? (
                    <span className="qm-btn-next-inner">
                      下一个
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M9 18l6-6-6-6"/>
                      </svg>
                    </span>
                  ) : '查看结果'}
                </button>
              </div>
              <div className="qm-key-hints">
                {index > 0 && <span className="qm-key-hint"><kbd>←</kbd> 上一个</span>}
                <span className="qm-key-hint"><kbd>→</kbd> 下一个</span>
                <span className="qm-key-hint"><kbd>Tab</kbd> 重播发音</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
