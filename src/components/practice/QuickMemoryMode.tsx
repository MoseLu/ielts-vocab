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

import React, { useState, useEffect, useRef, useCallback } from 'react'
import type { QuickMemoryModeProps, QuickMemoryRecords, Word } from './types'
import { STORAGE_KEYS } from '../../constants'
import { playWordAudio, stopAudio } from './utils'
import { logSession } from '../../hooks/useAIChat'

// ── Ebbinghaus review intervals (days per consecutive knownCount) ──────────
const REVIEW_INTERVALS_DAYS = [1, 1, 4, 7, 14, 30]

function nextReviewTimestamp(knownCount: number): number {
  const days = REVIEW_INTERVALS_DAYS[Math.min(knownCount, REVIEW_INTERVALS_DAYS.length - 1)]
  return Date.now() + days * 86_400_000
}

function loadRecords(): QuickMemoryRecords {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS) || '{}') }
  catch { return {} }
}

function saveRecords(records: QuickMemoryRecords) {
  localStorage.setItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS, JSON.stringify(records))
}

/** Fetch records from backend and merge into localStorage (backend wins for newer lastSeen). */
async function loadRecordsFromBackend(): Promise<void> {
  const token = localStorage.getItem('auth_token')
  if (!token) return
  try {
    const res = await fetch('/api/ai/quick-memory', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return
    const data = await res.json()
    const serverRecords: Array<{
      word: string; status: string; firstSeen: number; lastSeen: number;
      knownCount: number; unknownCount: number; nextReview: number; fuzzyCount: number
    }> = data.records || []
    if (!serverRecords.length) return
    const local = loadRecords()
    let changed = false
    for (const r of serverRecords) {
      const key = r.word.toLowerCase()
      const existing = local[key]
      if (!existing || (r.lastSeen ?? 0) > (existing.lastSeen ?? 0)) {
        local[key] = {
          status: r.status as 'known' | 'unknown',
          firstSeen: r.firstSeen,
          lastSeen: r.lastSeen,
          knownCount: r.knownCount,
          unknownCount: r.unknownCount,
          nextReview: r.nextReview,
          fuzzyCount: r.fuzzyCount ?? 0,
        }
        changed = true
      }
    }
    if (changed) saveRecords(local)
  } catch {
    // Non-critical
  }
}

/** Fire-and-forget: sync a single updated record to the backend. */
function syncRecordToBackend(word: string, record: QuickMemoryRecords[string]): void {
  const token = localStorage.getItem('auth_token')
  if (!token) return
  fetch('/api/ai/quick-memory/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      records: [{
        word: word.toLowerCase(),
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

function updateRecord(
  records: QuickMemoryRecords,
  word: string,
  choice: 'known' | 'unknown',
  isFuzzy: boolean,
): QuickMemoryRecords {
  const key = word.toLowerCase()
  const existing = records[key]
  const now = Date.now()
  const knownCount   = (existing?.knownCount   ?? 0) + (choice === 'known'   ? 1 : 0)
  const unknownCount = (existing?.unknownCount  ?? 0) + (choice === 'unknown' ? 1 : 0)
  const fuzzyCount   = (existing?.fuzzyCount    ?? 0) + (isFuzzy ? 1 : 0)
  return {
    ...records,
    [key]: {
      status:     choice,
      firstSeen:  existing?.firstSeen ?? now,
      lastSeen:   now,
      knownCount,
      unknownCount,
      fuzzyCount,
      nextReview: nextReviewTimestamp(knownCount),
    },
  }
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
        {nextChapter && bookId ? (
          <button
            className="qm-btn-next-chapter"
            onClick={() => onNavigate(`/practice?book=${bookId}&chapter=${nextChapter.id}&mode=quickmemory`)}
          >
            下一章节
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
  onModeChange,
  onNavigate,
  onWrongWord,
}: QuickMemoryModeProps) {
  const [index, setIndex]         = useState(0)
  const [phase, setPhase]         = useState<'question' | 'reveal'>('question')
  const [countdown, setCountdown] = useState(TIMER_SECONDS)
  const [choice, setChoice]       = useState<'known' | 'unknown' | null>(null)
  const [results, setResults]     = useState<SessionResult[]>([])
  const [done, setDone]           = useState(false)
  // Set of queue indices the user navigated back to (= uncertain/fuzzy about)
  const [revisitedSet, setRevisitedSet] = useState<Set<number>>(new Set())

  const timerRef        = useRef<ReturnType<typeof setInterval>>()
  const revealTimerRef  = useRef<ReturnType<typeof setTimeout>>()
  const chosenRef       = useRef(false)   // guard against double-fire
  const wordRef         = useRef<Word>()  // always holds current word for setTimeout
  const sessionStartRef = useRef(Date.now())

  const currentWord: Word | undefined = vocabulary[queue[index]]
  // Keep ref in sync so setTimeout always uses the latest word
  wordRef.current = currentWord

  // ── Reveal helper ──────────────────────────────────────────────────────────
  const reveal = useCallback((picked: 'known' | 'unknown') => {
    if (chosenRef.current) return
    chosenRef.current = true
    clearInterval(timerRef.current)

    const isFuzzy = revisitedSet.has(index)

    setChoice(picked)
    setPhase('reveal')

    // Update persistent records
    const records = updateRecord(loadRecords(), currentWord?.word ?? '', picked, isFuzzy)
    saveRecords(records)
    const wordKey = (currentWord?.word ?? '').toLowerCase()
    if (wordKey && records[wordKey]) syncRecordToBackend(wordKey, records[wordKey])

    // Replace existing result if user went back and re-answered; else append
    setResults(prev => {
      const existing = prev.findIndex(r => r.wordIdx === index)
      const entry: SessionResult = { wordIdx: index, choice: picked, wasFuzzy: isFuzzy }
      if (existing >= 0) {
        const next = [...prev]; next[existing] = entry; return next
      }
      return [...prev, entry]
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
  }, [index, settings, revisitedSet])

  // ── Play audio when question phase starts ──────────────────────────────────
  useEffect(() => {
    if (phase !== 'question' || !currentWord) return
    const t = setTimeout(() => playWordAudio(currentWord.word, settings, () => {}), 200)
    return () => clearTimeout(t)
  }, [phase, index]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Countdown tick ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'question') return
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
  }, [phase, index])   // re-run when word changes

  // ── Save chapter progress when a round is done ────────────────────────────
  useEffect(() => {
    if (!done || !bookId || !chapterId) return
    const correct = results.filter(r => r.choice === 'known').length
    const wrong   = results.filter(r => r.choice === 'unknown').length
    const token   = localStorage.getItem('auth_token')

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

    if (token) {
      // Save book-level progress
      fetch('/api/books/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ book_id: bookId, ...progressData }),
      }).catch(() => {})

      // Save chapter-level progress
      fetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(progressData),
      }).catch(() => {})

      // Save per-mode accuracy so it shows as an independent badge in ChapterModal
      fetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          mode: 'quickmemory',
          correct_count: correct,
          wrong_count: wrong,
          is_completed: true,
        }),
      }).catch(() => {})
    }

    // Log session for admin analytics
    logSession({
      mode: 'quickmemory',
      bookId,
      chapterId,
      wordsStudied: queue.length,
      correctCount: correct,
      wrongCount: wrong,
      durationSeconds: Math.round((Date.now() - sessionStartRef.current) / 1000),
      startedAt: sessionStartRef.current,
    })
  }, [done]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Save partial chapter progress on unmount (if session not completed) ──────
  useEffect(() => {
    return () => {
      if (done || !bookId || !chapterId || index === 0) return
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
  }, [done, bookId, chapterId, index, results])

  // ── Load records from backend on mount (merge into localStorage) ──────────
  useEffect(() => { loadRecordsFromBackend() }, [])

  // ── Cleanup audio on unmount ───────────────────────────────────────────────
  useEffect(() => () => {
    stopAudio()
    clearInterval(timerRef.current)
    clearTimeout(revealTimerRef.current)
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
    setPhase('question')
    setChoice(null)
  }, [index, queue.length])

  // ── Go back to previous word ───────────────────────────────────────────────
  const handlePrev = useCallback(() => {
    if (index === 0) return
    clearTimeout(revealTimerRef.current)
    stopAudio()
    const prev = index - 1
    // Mark the previous word as revisited — re-answering it counts as fuzzy
    setRevisitedSet(s => { const n = new Set(s); n.add(prev); return n })
    setIndex(prev)
    setPhase('question')
    setChoice(null)
  }, [index])

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
