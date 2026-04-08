
import { useState, useEffect, useRef, useCallback } from 'react'
import type { QuickMemoryModeProps, Word } from './types'
import { playWordAudio, prepareWordAudioPlayback, preloadWordAudioBatch, stopAudio } from './utils'
import { updateStudySessionSnapshot } from '../../hooks/useAIChat'
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

// ── Main component ────────────────────────────────────────────────────────────
export default function QuickMemoryMode({
  vocabulary,
  queue,
  settings,
  bookId,
  chapterId,
  bookChapters,
  reviewMode,
  errorMode = false,
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
  const [index, setIndex]         = useState(0)
  const hasRestoredIndexRef = useRef(false)
  const [phase, setPhase]         = useState<'question' | 'reveal'>('question')
  const [countdown, setCountdown] = useState(TIMER_SECONDS)
  const [choice, setChoice]       = useState<'known' | 'unknown' | null>(null)
  const [results, setResults]     = useState<SessionResult[]>([])
  const [done, setDone]           = useState(false)
  const [questionReplayNonce, setQuestionReplayNonce] = useState(0)
  const [revisitedSet, setRevisitedSet] = useState<Set<number>>(new Set())
  const resultsRef = useRef<SessionResult[]>([])
  const timerRef        = useRef<ReturnType<typeof setInterval> | undefined>(undefined)
  const revealTimerRef  = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const chosenRef       = useRef(false)
  const wordRef         = useRef<Word | undefined>(undefined)
  const sessionStartRef = useRef(Date.now())
  const completedSessionDurationSecondsRef = useRef<number | null>(null)
  const bookIdRef       = useRef<string | null>(bookId)
  const chapterIdRef    = useRef<string | null>(chapterId)
  const sessionIdRef    = useRef<number | null>(null)
  const sessionLoggedRef = useRef(false)
  const pendingSessionCancelRef = useRef(false)
  const pendingRecordSyncRef = useRef<Record<string, QuickMemoryRecordState>>({})
  const recordSyncInFlightRef = useRef(false)

  const currentWord: Word | undefined = vocabulary[queue[index]]
  const nextWord: Word | undefined = vocabulary[queue[index + 1]]
  wordRef.current = currentWord

  useEffect(() => {
    bookIdRef.current = bookId
  }, [bookId])

  useEffect(() => {
    chapterIdRef.current = chapterId
  }, [chapterId])

  const syncSessionSnapshot = useCallback((patch: {
    activeAt?: number
    wordsStudied?: number
    correctCount?: number
    wrongCount?: number
  } = {}) => {
    updateStudySessionSnapshot({
      sessionId: sessionIdRef.current,
      mode: 'quickmemory',
      bookId: bookIdRef.current,
      chapterId: chapterIdRef.current,
      startedAt: sessionStartRef.current,
      activeAt: patch.activeAt ?? Date.now(),
      wordsStudied: patch.wordsStudied,
      correctCount: patch.correctCount,
      wrongCount: patch.wrongCount,
    })
  }, [])

  const flushPendingRecordSync = useCallback((keepalive = false) => {
    if (recordSyncInFlightRef.current) return

    const pendingEntries = Object.entries(pendingRecordSyncRef.current)
    if (!pendingEntries.length) return

    pendingRecordSyncRef.current = {}
    recordSyncInFlightRef.current = true

    void syncQuickMemoryRecordsToBackend(
      pendingEntries.map(([word, record]) => ({ word, record })),
      { keepalive },
    ).catch(() => {
      pendingRecordSyncRef.current = {
        ...Object.fromEntries(pendingEntries),
        ...pendingRecordSyncRef.current,
      }
    }).finally(() => {
      recordSyncInFlightRef.current = false
    })
  }, [])

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
    bookIdRef,
    chapterIdRef,
    sessionIdRef,
    sessionLoggedRef,
    pendingSessionCancelRef,
    flushPendingRecordSync,
    syncSessionSnapshot,
    showSaveError: () => showToast('进度保存失败，请检查网络连接', 'error'),
  })

  useEffect(() => {
    if (queue.length === 0) return  // vocabulary not loaded yet; nothing to reset
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
    pendingSessionCancelRef.current = false
  }, [bookId, chapterId, onIndexChange, queue.length])  // eslint-disable-line react-hooks/exhaustive-deps

  const reveal = useCallback((picked: 'known' | 'unknown') => {
    if (chosenRef.current) return
    chosenRef.current = true
    clearInterval(timerRef.current)
    stopAudio()

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
    const existing = prevResults.findIndex(r => r.wordIdx === index)
    const entry: SessionResult = { wordIdx: index, choice: picked, wasFuzzy: isFuzzy }
    const nextResults = existing >= 0
      ? prevResults.map((result, resultIndex) => (resultIndex === existing ? entry : result))
      : [...prevResults, entry]
    resultsRef.current = nextResults
    setResults(nextResults)
    syncSessionSnapshot({
      activeAt: Date.now(),
      wordsStudied: nextResults.length,
      correctCount: nextResults.filter(result => result.choice === 'known').length,
      wrongCount: nextResults.filter(result => result.choice === 'unknown').length,
    })

    if (picked === 'unknown' && currentWord) {
      onWrongWord(currentWord)
    }

    revealTimerRef.current = setTimeout(() => {
      if (wordRef.current) void playWordAudio(wordRef.current.word, settings, () => {})
    }, 350)
  }, [currentWord, index, onQuickMemoryRecordChange, onWrongWord, revisitedSet, settings])

  useEffect(() => {
    if (phase !== 'question' || !currentWord) return
    const activeWord = currentWord.word
    let cancelled = false

    chosenRef.current = false
    setCountdown(TIMER_SECONDS)
    clearInterval(timerRef.current)

    const upcomingWords = queue
      .slice(index + 1, index + 4)
      .map(queueIndex => vocabulary[queueIndex]?.word?.trim())
      .filter((word): word is string => Boolean(word))
    if (upcomingWords.length) {
      void preloadWordAudioBatch(upcomingWords)
    }

    const startCountdown = () => {
      if (cancelled) return
      clearInterval(timerRef.current)
      timerRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(timerRef.current)
            reveal('unknown')
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }

    void (async () => {
      const audioReady = await prepareWordAudioPlayback(activeWord)
      if (cancelled || wordRef.current?.word !== activeWord) return
      if (audioReady) {
        const started = await playWordAudio(activeWord, settings, () => {
          if (!cancelled && wordRef.current?.word === activeWord) startCountdown()
        })
        if (cancelled || wordRef.current?.word !== activeWord) return
        if (started) return
      }
      startCountdown()
    })()

    return () => {
      cancelled = true
      clearInterval(timerRef.current)
    }
  }, [currentWord?.word, nextWord?.word, phase, index, questionReplayNonce, reveal, settings])   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void reconcileQuickMemoryRecordsWithBackend().catch(() => {})
  }, [])

  useEffect(() => () => {
    stopAudio()
    clearInterval(timerRef.current)
    clearTimeout(revealTimerRef.current)
  }, [])

  const handleNext = useCallback(() => {
    clearTimeout(revealTimerRef.current)
    stopAudio()
    const next = index + 1
    if (next >= queue.length) {
      completedSessionDurationSecondsRef.current = Math.max(0, Math.round((Date.now() - sessionStartRef.current) / 1000))
      setDone(true)
      return
    }
    setIndex(next)
    onIndexChange?.(next)
    setPhase('question')
    setChoice(null)
  }, [index, queue.length, onIndexChange])

  const handlePrev = useCallback(() => {
    if (index === 0) return
    clearTimeout(revealTimerRef.current)
    stopAudio()
    const prev = index - 1
    // Mark the previous word as revisited — re-answering it counts as fuzzy
    setRevisitedSet(s => { const n = new Set(s); n.add(prev); return n })
    setIndex(prev)
    onIndexChange?.(prev)
    setPhase('question')
    setChoice(null)
  }, [index, onIndexChange])

  const replayCurrentWord = useCallback(() => {
    if (!wordRef.current) return
    clearTimeout(revealTimerRef.current)
    clearInterval(timerRef.current)
    setCountdown(TIMER_SECONDS)
    if (phase === 'question') {
      stopAudio()
      setQuestionReplayNonce(value => value + 1)
      return
    }
    void playWordAudio(wordRef.current.word, settings, () => {})
  }, [phase, settings])

  useEffect(() => {
    const handlePreviousShortcut = () => { handlePrev() }
    const handleNextShortcut = () => {
      if (phase === 'question') {
        reveal('known')
        return
      }
      handleNext()
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
    setDone(false)
  }, [onIndexChange])

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

  const progress = ((index) / queue.length) * 100

  return (
    <div className="qm-root">
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
                onClick={() => reveal('unknown')}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                不认识
              </button>
              <button
                className="qm-btn qm-btn--known"
                onClick={() => reveal('known')}
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
                <button className="qm-btn-prev" onClick={handlePrev}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M15 18l-6-6 6-6"/>
                  </svg>
                  上一个
                </button>
              )}
              <button className="qm-btn-next" onClick={handleNext}>
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
  )
}
