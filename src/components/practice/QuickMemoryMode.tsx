// ── Quick Memory Mode ─────────────────────────────────────────────────────────
// DHP (Dynamic Hierarchical Progress) + SSP (Spaced-repetition + Ebbinghaus)
//
// Flow per word:
//   1. Show word only — 4-second countdown
//   2. User taps "认识" or "不认识" (or timer expires → "不认识")
//   3. Reveal: phonetic + definition + auto-play pronunciation
//   4. "下一个" → advance
//
// Records are persisted to localStorage (STORAGE_KEYS.QUICK_MEMORY_RECORDS).
// Each word carries: firstSeen, lastSeen, knownCount, unknownCount, nextReview.
// nextReview uses Ebbinghaus intervals: 1 / 1 / 4 / 7 / 14 / 30 days.
// After the full streak completes, nextReview becomes 0 and the word leaves the due queue.

import { useState, useEffect, useRef, useCallback } from 'react'
import type { QuickMemoryModeProps, Word } from './types'
import { playWordAudio, stopAudio } from './utils'
import {
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  cancelSession,
  flushStudySessionOnPageHide,
  logSession,
  startSession,
  touchStudySessionActivity,
  updateStudySessionSnapshot,
} from '../../hooks/useAIChat'
import { apiFetch } from '../../lib'
import { useToast } from '../../contexts/ToastContext'
import {
  mergeQuickMemoryRecordsByLastSeen,
  readQuickMemoryRecordsFromStorage,
  updateQuickMemoryRecord,
  writeQuickMemoryRecordsToStorage,
  type QuickMemoryRecordInput,
  type QuickMemoryRecordState,
} from '../../lib/quickMemory'

/** Fetch records from backend and merge into localStorage (backend wins for newer lastSeen). */
async function loadRecordsFromBackend(): Promise<void> {
  try {
    const data = await apiFetch<{ records: QuickMemoryRecordInput[] }>('/api/ai/quick-memory')
    const serverRecords = Array.isArray(data.records) ? data.records : []
    if (!serverRecords.length) return
    const merged = mergeQuickMemoryRecordsByLastSeen(
      readQuickMemoryRecordsFromStorage(),
      serverRecords,
    )
    writeQuickMemoryRecordsToStorage(merged)
  } catch {
    // Non-critical
  }
}

/** Fire-and-forget: sync a single updated record to the backend. */
function syncRecordToBackend(word: string, record: QuickMemoryRecordState): void {
  apiFetch('/api/ai/quick-memory/sync', {
    method: 'POST',
    body: JSON.stringify({
      source: 'quickmemory',
      records: [{
        word: word.toLowerCase(),
        bookId: record.bookId,
        chapterId: record.chapterId,
        status: record.status,
        firstSeen: record.firstSeen,
        lastSeen: record.lastSeen,
        knownCount: record.knownCount,
        unknownCount: record.unknownCount,
        nextReview: record.nextReview,
        fuzzyCount: record.fuzzyCount,
      }],
    }),
  }).catch(() => {})
}

// ── Circular countdown SVG ────────────────────────────────────────────────────
const TIMER_SECONDS = 4
const RADIUS = 20
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function CountdownRing({ seconds, total }: { seconds: number; total: number }) {
  const progress = seconds / total
  const dash = progress * CIRCUMFERENCE
  return (
    <svg className="qm-timer-svg" viewBox="0 0 48 48" width="48" height="48">
      {/* Track */}
      <circle cx="24" cy="24" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth="3" />
      {/* Progress arc */}
      <circle
        cx="24" cy="24" r={RADIUS}
        fill="none"
        stroke={seconds <= 1 ? 'var(--error)' : 'var(--accent)'}
        strokeWidth="3"
        strokeDasharray={`${dash} ${CIRCUMFERENCE}`}
        strokeLinecap="round"
        transform="rotate(-90 24 24)"
        style={{ transition: 'stroke-dasharray 0.9s linear, stroke 0.2s' }}
      />
      {/* Digit */}
      <text
        x="24" y="24"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize="14"
        fontWeight="700"
        fill={seconds <= 1 ? 'var(--error)' : 'var(--text-primary)'}
      >
        {seconds}
      </text>
    </svg>
  )
}

// ── Session summary ───────────────────────────────────────────────────────────
interface SessionResult {
  wordIdx: number
  choice: 'known' | 'unknown'
  wasFuzzy: boolean   // user went back and re-answered this word
}

function SummaryScreen({
  results,
  vocabulary,
  queue,
  bookId,
  chapterId,
  bookChapters,
  reviewMode,
  reviewHasMore,
  onContinueReview,
  buildChapterPath,
  onRestart,
  onModeChange,
  onNavigate,
}: {
  results: SessionResult[]
  vocabulary: Word[]
  queue: number[]
  bookId: string | null
  chapterId: string | null
  bookChapters: { id: number | string; title: string }[]
  reviewMode?: boolean
  reviewHasMore?: boolean
  onContinueReview?: () => void
  buildChapterPath?: (chapterId: string | number) => string
  onRestart: () => void
  onModeChange: (mode: string) => void
  onNavigate: (path: string) => void
}) {
  const known   = results.filter(r => r.choice === 'known')
  const unknown = results.filter(r => r.choice === 'unknown')
  const fuzzy   = results.filter(r => r.wasFuzzy)

  const currentIdx = bookChapters.findIndex(c => String(c.id) === String(chapterId))
  const nextChapter = currentIdx >= 0 && currentIdx < bookChapters.length - 1
    ? bookChapters[currentIdx + 1]
    : null

  const accuracy = results.length > 0 ? Math.round(known.length / results.length * 100) : 0

  return (
    <div className="qm-summary">
      <div className="qm-summary-title">本轮完成</div>
      <div className="qm-summary-stats">
        <div className="qm-stat qm-stat-known">
          <span className="qm-stat-num">{known.length}</span>
          <span className="qm-stat-label">认识</span>
        </div>
        <div className="qm-stat qm-stat-unknown">
          <span className="qm-stat-num">{unknown.length}</span>
          <span className="qm-stat-label">不认识</span>
        </div>
        {fuzzy.length > 0 && (
          <div className="qm-stat qm-stat-fuzzy">
            <span className="qm-stat-num">{fuzzy.length}</span>
            <span className="qm-stat-label">模糊</span>
          </div>
        )}
        <div className="qm-stat">
          <span className="qm-stat-num">{accuracy}%</span>
          <span className="qm-stat-label">正确率</span>
        </div>
      </div>

      {fuzzy.length > 0 && (
        <div className="qm-summary-section">
          <div className="qm-summary-section-title">模糊单词（回退重答）</div>
          <div className="qm-summary-word-list">
            {fuzzy.map(r => {
              const w = vocabulary[queue[r.wordIdx]]
              return w ? (
                <span key={r.wordIdx} className={`qm-summary-word-tag qm-summary-word-fuzzy`}>{w.word}</span>
              ) : null
            })}
          </div>
        </div>
      )}

      {unknown.length > 0 && (
        <div className="qm-summary-section">
          <div className="qm-summary-section-title">需要复习</div>
          <div className="qm-summary-word-list">
            {unknown.map(r => {
              const w = vocabulary[queue[r.wordIdx]]
              return w ? (
                <span key={r.wordIdx} className={`qm-summary-word-tag${r.wasFuzzy ? ' qm-summary-word-fuzzy' : ''}`}>{w.word}</span>
              ) : null
            })}
          </div>
        </div>
      )}

      <div className="qm-summary-actions">
        <button className="qm-btn-restart" onClick={onRestart}>再来一轮</button>
        {reviewHasMore && onContinueReview ? (
          <button
            className="qm-btn-next-chapter"
            onClick={onContinueReview}
          >
            下一组复习
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </button>
        ) : nextChapter && bookId ? (
          <button
            className="qm-btn-next-chapter"
            onClick={() => onNavigate(
              buildChapterPath?.(nextChapter.id) ?? `/practice?book=${bookId}&chapter=${nextChapter.id}&mode=quickmemory`,
            )}
          >
            {reviewMode ? '下一章节复习' : '下一章节'}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </button>
        ) : (
          <button className="qm-btn-mode" onClick={() => onModeChange('smart')}>换个模式</button>
        )}
      </div>
    </div>
  )
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
  reviewHasMore,
  onContinueReview,
  buildChapterPath,
  onModeChange,
  onNavigate,
  onWrongWord,
  onQuickMemoryRecordChange,
  initialIndex,
  onIndexChange,
}: QuickMemoryModeProps) {
  const { showToast } = useToast()
  const [index, setIndex]         = useState(0)
  // Tracks whether we've applied initialIndex once (only on first vocabulary load)
  const hasRestoredIndexRef = useRef(false)
  const [phase, setPhase]         = useState<'question' | 'reveal'>('question')
  const [countdown, setCountdown] = useState(TIMER_SECONDS)
  const [choice, setChoice]       = useState<'known' | 'unknown' | null>(null)
  const [results, setResults]     = useState<SessionResult[]>([])
  const [done, setDone]           = useState(false)
  // Set of queue indices the user navigated back to (= uncertain/fuzzy about)
  const [revisitedSet, setRevisitedSet] = useState<Set<number>>(new Set())
  const resultsRef = useRef<SessionResult[]>([])

  const timerRef        = useRef<ReturnType<typeof setInterval> | undefined>(undefined)
  const revealTimerRef  = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const chosenRef       = useRef(false)   // guard against double-fire
  const wordRef         = useRef<Word | undefined>(undefined)  // always holds current word for setTimeout
  const sessionStartRef = useRef(Date.now())
  const bookIdRef       = useRef<string | null>(bookId)
  const chapterIdRef    = useRef<string | null>(chapterId)
  const sessionIdRef    = useRef<number | null>(null)
  const sessionLoggedRef = useRef(false)
  const pendingSessionCancelRef = useRef(false)

  const currentWord: Word | undefined = vocabulary[queue[index]]
  // Keep ref in sync so setTimeout always uses the latest word
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

  useEffect(() => {
    const touch = () => {
      if (sessionStartRef.current <= 0) return
      touchStudySessionActivity(sessionIdRef.current)
    }
    const onVisible = () => {
      if (document.visibilityState === 'visible') touch()
    }
    window.addEventListener('pointerdown', touch, true)
    window.addEventListener('keydown', touch, true)
    window.addEventListener('focus', touch)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('pointerdown', touch, true)
      window.removeEventListener('keydown', touch, true)
      window.removeEventListener('focus', touch)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  useEffect(() => {
    const handlePageHide = () => {
      if (sessionLoggedRef.current || sessionStartRef.current <= 0) return
      const finalResults = resultsRef.current
      flushStudySessionOnPageHide({
        mode: 'quickmemory',
        bookId: bookIdRef.current,
        chapterId: chapterIdRef.current,
        wordsStudied: finalResults.length,
        correctCount: finalResults.filter(r => r.choice === 'known').length,
        wrongCount: finalResults.filter(r => r.choice === 'unknown').length,
        startedAt: sessionStartRef.current,
        sessionId: sessionIdRef.current,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [])

  // Reset session-scoped state when practice context changes.
  // On the very first load (queue going from empty to populated), restore
  // the saved position from initialIndex instead of resetting to 0.
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
    setPhase('question')
    setCountdown(TIMER_SECONDS)
    setChoice(null)
    setResults([])
    resultsRef.current = []
    setDone(false)
    setRevisitedSet(new Set())
    sessionLoggedRef.current = false
    pendingSessionCancelRef.current = false
  }, [bookId, chapterId, queue.length])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Reveal helper ──────────────────────────────────────────────────────────
  const reveal = useCallback((picked: 'known' | 'unknown') => {
    if (chosenRef.current) return
    chosenRef.current = true
    clearInterval(timerRef.current)

    const isFuzzy = revisitedSet.has(index)

    setChoice(picked)
    setPhase('reveal')

    // Update persistent records
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
      syncRecordToBackend(wordKey, record)
    }
    if (currentWord && record) {
      onQuickMemoryRecordChange?.(currentWord, record)
    }

    // Replace existing result if user went back and re-answered; else append.
    // Keep the ref in sync immediately so a fast "查看结果" click does not miss
    // the last answered word while React state is still committing.
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

    // Report wrong words to the error book
    if (picked === 'unknown' && currentWord) {
      onWrongWord(currentWord)
    }

    // Auto-play pronunciation after brief delay.
    // Use wordRef so this always plays the CURRENT word (not the closure-captured one).
    revealTimerRef.current = setTimeout(() => {
      if (wordRef.current) playWordAudio(wordRef.current.word, settings, () => {})
    }, 350)
  }, [currentWord, index, onQuickMemoryRecordChange, onWrongWord, revisitedSet, settings])

  // ── Play audio when question phase starts ──────────────────────────────────
  useEffect(() => {
    if (phase !== 'question' || !currentWord) return
    const t = setTimeout(() => playWordAudio(currentWord.word, settings, () => {}), 200)
    return () => clearTimeout(t)
  }, [currentWord?.word, phase, index]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Countdown tick ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'question' || !currentWord) return
    chosenRef.current = false
    setCountdown(TIMER_SECONDS)

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

    return () => clearInterval(timerRef.current)
  }, [currentWord?.word, phase, index, reveal])   // re-run when word changes

  // ── Save chapter progress when a round is done ────────────────────────────
  useEffect(() => {
    if (reviewMode || !done || !bookId || !chapterId) return
    const correct = results.filter(r => r.choice === 'known').length
    const wrong   = results.filter(r => r.choice === 'unknown').length

    const progressData = {
      current_index: queue.length,
      correct_count: correct,
      wrong_count:   wrong,
      words_learned: queue.length,
      is_completed:  true,
    }

    // Persist locally
    const chapterProgress: Record<string, typeof progressData & { updatedAt: string }> =
      JSON.parse(localStorage.getItem('chapter_progress') || '{}')
    chapterProgress[`${bookId}_${chapterId}`] = { ...progressData, updatedAt: new Date().toISOString() }
    localStorage.setItem('chapter_progress', JSON.stringify(chapterProgress))

    // Save chapter-level progress — toast on failure so user knows
    apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
      method: 'POST',
      body: JSON.stringify(progressData),
    }).catch(() => showToast('进度保存失败，请检查网络连接', 'error'))

    // Save per-mode accuracy so it shows as an independent badge in ChapterModal
    apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
      method: 'POST',
      body: JSON.stringify({
        mode: 'quickmemory',
        correct_count: correct,
        wrong_count: wrong,
        is_completed: true,
      }),
    }).catch(() => {})
  }, [bookId, chapterId, done, queue, results, reviewMode, showToast, vocabulary])

  // ── Log completed sessions immediately, including review/global sessions ──
  useEffect(() => {
    if (!done || sessionLoggedRef.current || results.length < queue.length) return
    const finalResults = resultsRef.current
    if (finalResults.length < queue.length) return
    const correct = finalResults.filter(r => r.choice === 'known').length
    const wrong   = finalResults.filter(r => r.choice === 'unknown').length

    sessionLoggedRef.current = true
    syncSessionSnapshot({
      activeAt: Date.now(),
      wordsStudied: queue.length,
      correctCount: correct,
      wrongCount: wrong,
    })
    logSession({
      mode: 'quickmemory',
      bookId,
      chapterId,
      wordsStudied: queue.length,
      correctCount: correct,
      wrongCount: wrong,
      durationSeconds: Math.round((Date.now() - sessionStartRef.current) / 1000),
      startedAt: sessionStartRef.current,
      sessionId: sessionIdRef.current,
    })
  }, [bookId, chapterId, done, queue.length, results])

  // ── Save partial chapter progress on unmount (if session not completed) ──────
  useEffect(() => {
    return () => {
      if (reviewMode || done || !bookId || !chapterId || index === 0) return
      const correct = results.filter(r => r.choice === 'known').length
      const wrong   = results.filter(r => r.choice === 'unknown').length
      const partialProgress = {
        current_index: index,
        correct_count: correct,
        wrong_count:   wrong,
        words_learned: index,
        is_completed:  false,
        updatedAt:     new Date().toISOString(),
      }
      const chapterProgress: Record<string, typeof partialProgress> =
        JSON.parse(localStorage.getItem('chapter_progress') || '{}')
      // Only overwrite if no completed record already exists
      const existing = chapterProgress[`${bookId}_${chapterId}`]
      if (!existing?.is_completed) {
        chapterProgress[`${bookId}_${chapterId}`] = partialProgress
        localStorage.setItem('chapter_progress', JSON.stringify(chapterProgress))
      }
    }
  }, [done, reviewMode, bookId, chapterId, index, results])

  // ── Load records from backend on mount (merge into localStorage) ──────────
  useEffect(() => { loadRecordsFromBackend() }, [])

  // ── Start server-side session timer on mount ───────────────────────────────
  useEffect(() => {
    sessionStartRef.current = Date.now()
    sessionLoggedRef.current = false
    pendingSessionCancelRef.current = false
    startSession({
      mode: 'quickmemory',
      bookId,
      chapterId,
    }).then(id => {
      sessionIdRef.current = id
      if (pendingSessionCancelRef.current && id) {
        cancelSession(id)
      }
    }).catch(() => {})
  }, [bookId, chapterId])

  // ── Cleanup audio + session lifecycle on unmount ──────────────────────────
  useEffect(() => () => {
    stopAudio()
    clearInterval(timerRef.current)
    clearTimeout(revealTimerRef.current)

    if (sessionLoggedRef.current) return

    const finalResults = resultsRef.current
    const durationSeconds = Math.round((Date.now() - sessionStartRef.current) / 1000)
    if (finalResults.length <= 0 && durationSeconds < PASSIVE_STUDY_SESSION_MIN_SECONDS) {
      pendingSessionCancelRef.current = true
      cancelSession(sessionIdRef.current)
      return
    }

    sessionLoggedRef.current = true
    syncSessionSnapshot({
      activeAt: Date.now(),
      wordsStudied: finalResults.length,
      correctCount: finalResults.filter(r => r.choice === 'known').length,
      wrongCount: finalResults.filter(r => r.choice === 'unknown').length,
    })
    logSession({
      mode: 'quickmemory',
      bookId: bookIdRef.current,
      chapterId: chapterIdRef.current,
      wordsStudied: finalResults.length,
      correctCount: finalResults.filter(r => r.choice === 'known').length,
      wrongCount: finalResults.filter(r => r.choice === 'unknown').length,
      durationSeconds,
      startedAt: sessionStartRef.current,
      sessionId: sessionIdRef.current,
    })
  }, [])

  // ── Advance to next word ───────────────────────────────────────────────────
  const handleNext = useCallback(() => {
    clearTimeout(revealTimerRef.current)
    stopAudio()
    const next = index + 1
    if (next >= queue.length) {
      setDone(true)
      return
    }
    setIndex(next)
    onIndexChange?.(next)
    setPhase('question')
    setChoice(null)
  }, [index, queue.length, onIndexChange])

  // ── Go back to previous word ───────────────────────────────────────────────
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

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (phase === 'question') {
        if (e.key === 'ArrowLeft')  { e.preventDefault(); reveal('unknown') }
        if (e.key === 'ArrowRight') { e.preventDefault(); reveal('known') }
      } else if (phase === 'reveal') {
        if (e.key === 'ArrowLeft') { e.preventDefault(); handlePrev() }
        if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {
          e.preventDefault(); handleNext()
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [phase, reveal, handlePrev, handleNext])

  // ── Restart ────────────────────────────────────────────────────────────────
  const handleRestart = useCallback(() => {
    stopAudio()
    setIndex(0)
    setPhase('question')
    setChoice(null)
    setResults([])
    resultsRef.current = []
    setRevisitedSet(new Set())
    setDone(false)
  }, [])

  // ── Guard: no words ────────────────────────────────────────────────────────
  if (!currentWord && !done) {
    return <div className="qm-empty">暂无单词</div>
  }

  // ── Summary screen ─────────────────────────────────────────────────────────
  if (done) {
    return (
      <SummaryScreen
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
        onRestart={handleRestart}
        onModeChange={onModeChange}
        onNavigate={onNavigate}
      />
    )
  }

  const progress = ((index) / queue.length) * 100

  return (
    <div className="qm-root">
      {/* Progress bar */}
      <div className="qm-progress-track">
        <div className="qm-progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="qm-progress-label">{index + 1} / {queue.length}</div>

      {/* Card */}
      <div className={`qm-card ${phase === 'reveal' ? 'qm-card--reveal' : ''}`}>

        {/* ── Question phase ── */}
        {phase === 'question' && (
          <>
            <div className="qm-countdown-ring">
              <CountdownRing seconds={countdown} total={TIMER_SECONDS} />
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
              <span className="qm-key-hint"><kbd>←</kbd> 不认识</span>
              <span className="qm-key-hint"><kbd>→</kbd> 认识</span>
            </div>
          </>
        )}

        {/* ── Reveal phase ── */}
        {phase === 'reveal' && currentWord && (
          <>
            {/* Result badge — show fuzzy indicator if this was a revisit */}
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
            </div>
          </>
        )}
      </div>
    </div>
  )
}
