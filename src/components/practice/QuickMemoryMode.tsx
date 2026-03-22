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

function updateRecord(
  records: QuickMemoryRecords,
  word: string,
  choice: 'known' | 'unknown',
): QuickMemoryRecords {
  const key = word.toLowerCase()
  const existing = records[key]
  const now = Date.now()
  const knownCount  = (existing?.knownCount  ?? 0) + (choice === 'known'   ? 1 : 0)
  const unknownCount = (existing?.unknownCount ?? 0) + (choice === 'unknown' ? 1 : 0)
  return {
    ...records,
    [key]: {
      status:      choice,
      firstSeen:   existing?.firstSeen ?? now,
      lastSeen:    now,
      knownCount,
      unknownCount,
      nextReview:  nextReviewTimestamp(knownCount),
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
}

function SummaryScreen({
  results,
  vocabulary,
  queue,
  onRestart,
  onModeChange,
}: {
  results: SessionResult[]
  vocabulary: Word[]
  queue: number[]
  onRestart: () => void
  onModeChange: (mode: string) => void
}) {
  const known   = results.filter(r => r.choice === 'known')
  const unknown = results.filter(r => r.choice === 'unknown')

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
      </div>

      {unknown.length > 0 && (
        <div className="qm-summary-section">
          <div className="qm-summary-section-title">需要复习</div>
          <div className="qm-summary-word-list">
            {unknown.map(r => {
              const w = vocabulary[queue[r.wordIdx]]
              return w ? (
                <span key={r.wordIdx} className="qm-summary-word-tag">{w.word}</span>
              ) : null
            })}
          </div>
        </div>
      )}

      <div className="qm-summary-actions">
        <button className="qm-btn-restart" onClick={onRestart}>再来一轮</button>
        <button className="qm-btn-mode" onClick={() => onModeChange('smart')}>换个模式</button>
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
  onModeChange,
}: QuickMemoryModeProps) {
  const [index, setIndex]         = useState(0)
  const [phase, setPhase]         = useState<'question' | 'reveal'>('question')
  const [countdown, setCountdown] = useState(TIMER_SECONDS)
  const [choice, setChoice]       = useState<'known' | 'unknown' | null>(null)
  const [results, setResults]     = useState<SessionResult[]>([])
  const [done, setDone]           = useState(false)

  const timerRef       = useRef<ReturnType<typeof setInterval>>()
  const revealTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const chosenRef      = useRef(false)   // guard against double-fire
  const wordRef        = useRef<Word>()  // always holds current word for setTimeout

  const currentWord: Word | undefined = vocabulary[queue[index]]
  // Keep ref in sync so setTimeout always uses the latest word
  wordRef.current = currentWord

  // ── Reveal helper ──────────────────────────────────────────────────────────
  const reveal = useCallback((picked: 'known' | 'unknown') => {
    if (chosenRef.current) return
    chosenRef.current = true
    clearInterval(timerRef.current)

    setChoice(picked)
    setPhase('reveal')

    // Update persistent records
    const records = updateRecord(loadRecords(), currentWord?.word ?? '', picked)
    saveRecords(records)
    setResults(prev => [...prev, { wordIdx: index, choice: picked }])

    // Auto-play pronunciation after brief delay.
    // Use wordRef so this always plays the CURRENT word (not the closure-captured one).
    revealTimerRef.current = setTimeout(() => {
      if (wordRef.current) playWordAudio(wordRef.current.word, settings, () => {})
    }, 350)
  }, [index, settings])

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

  // ── Restart ────────────────────────────────────────────────────────────────
  const handleRestart = useCallback(() => {
    stopAudio()
    setIndex(0)
    setPhase('question')
    setChoice(null)
    setResults([])
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
        onRestart={handleRestart}
        onModeChange={onModeChange}
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

            {/* Word is hidden — user identifies by listening only */}
            <div className="qm-audio-prompt">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="48" height="48">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
              </svg>
            </div>

            <p className="qm-hint">听音频，你认识这个单词吗？</p>

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
          </>
        )}

        {/* ── Reveal phase ── */}
        {phase === 'reveal' && currentWord && (
          <>
            {/* Result badge */}
            <div className={`qm-result-badge ${choice === 'known' ? 'qm-badge--known' : 'qm-badge--unknown'}`}>
              {choice === 'known' ? '✓ 认识' : '✗ 不认识'}
            </div>

            <div className="qm-word">{currentWord.word}</div>

            {currentWord.phonetic && (
              <div className="qm-phonetic">{currentWord.phonetic}</div>
            )}

            {currentWord.pos && (
              <span className="qm-pos">{currentWord.pos}</span>
            )}

            <div className="qm-definition">{currentWord.definition}</div>

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
          </>
        )}
      </div>
    </div>
  )
}
