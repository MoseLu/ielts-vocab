// ── Vocabulary Test Page ───────────────────────────────────────────────────────

import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Word } from './practice/types'
import { shuffleArray } from './practice/utils'

const TEST_WORD_COUNT = 20
const LISTENING_BOOK_ID = 'ielts_listening_premium'

// ── Types ────────────────────────────────────────────────────────────────────

interface TestQuestion {
  word: Word
  options: { text: string; correct: boolean }[]
}

interface TestResult {
  correct: number
  total: number
  accuracy: number
  wrongWords: Word[]
}

// ── Utils ───────────────────────────────────────────────────────────────────

function playWord(word: string) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(word)
  utter.lang = 'en-US'
  utter.rate = 0.9
  window.speechSynthesis.speak(utter)
}

function generateTestOptions(correctWord: Word, allWords: Word[]): { text: string; correct: boolean }[] {
  // Shuffle all words and pick 3 wrong ones
  const others = allWords.filter(w => w.word !== correctWord.word)
  const shuffled = shuffleArray(others).slice(0, 3)
  const wrongOptions = shuffled.map(w => w.definition)

  // Build options array
  const options = [
    { text: correctWord.definition, correct: true },
    ...wrongOptions.map(text => ({ text, correct: false }))
  ]
  return shuffleArray(options)
}

// ── Result Screen ─────────────────────────────────────────────────────────────

function ResultScreen({ result, onRestart, onBack }: { result: TestResult; onRestart: () => void; onBack: () => void }) {
  const pct = result.accuracy
  const ringColor = pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--accent)' : 'var(--error)'
  const circumference = 2 * Math.PI * 52
  const dashOffset = circumference * (1 - pct / 100)

  return (
    <div className="vocab-test-result">
      <div className="result-ring-wrap">
        <svg width="130" height="130" viewBox="0 0 130 130">
          <circle cx="65" cy="65" r="52" fill="none" stroke="var(--border)" strokeWidth="10"/>
          <circle
            cx="65" cy="65" r="52" fill="none"
            stroke={ringColor} strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            transform="rotate(-90 65 65)"
            style={{ transition: 'stroke-dashoffset 1s ease' }}
          />
        </svg>
        <div className="result-ring-label">
          <div className="result-pct">{pct}%</div>
          <div className="result-score">{result.correct}/{result.total}</div>
        </div>
      </div>

      <div className="result-msg">
        {pct >= 90 ? '🎉 太棒了！词汇量惊人！' :
         pct >= 70 ? '👍 很不错，继续保持！' :
         pct >= 50 ? '💪 还需努力，加油！' :
         '📚 建议多听多读，积累词汇'}
      </div>

      {result.wrongWords.length > 0 && (
        <div className="result-wrong-section">
          <div className="result-wrong-title">需要加强的词汇：</div>
          {result.wrongWords.map(w => (
            <div key={w.word} className="result-wrong-item">
              <span className="result-wrong-word">{w.word}</span>
              <span className="result-wrong-def">{w.definition}</span>
            </div>
          ))}
        </div>
      )}

      <div className="result-actions">
        <button className="result-btn primary" onClick={onRestart}>再测一次</button>
        <button className="result-btn" onClick={onBack}>返回</button>
      </div>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function VocabTestPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [questions, setQuestions] = useState<TestQuestion[]>([])
  const [qIndex, setQIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongWords, setWrongWords] = useState<Word[]>([])

  const currentQ = questions[qIndex]

  // Load words and generate test
  useEffect(() => {
    fetch(`/api/books/${LISTENING_BOOK_ID}/words?per_page=200`)
      .then(r => r.json())
      .then((data: { words?: Word[] }) => {
        const words: Word[] = data.words || []
        if (words.length < 4) {
          setError('词汇量不足，无法生成测试')
          return
        }
        const picked = shuffleArray(words).slice(0, TEST_WORD_COUNT)
        const testQs: TestQuestion[] = picked.map(w => ({
          word: w,
          options: generateTestOptions(w, words)
        }))
        setQuestions(testQs)
        setLoading(false)
        // Auto-play first word after short delay
        setTimeout(() => playWord(testQs[0].word.word), 600)
      })
      .catch(() => {
        setError('加载词汇失败')
        setLoading(false)
      })
  }, [])

  // Auto-play word when question changes
  useEffect(() => {
    if (currentQ && !showResult) {
      setTimeout(() => playWord(currentQ.word.word), 300)
    }
  }, [qIndex, showResult])

  const handleOptionSelect = useCallback((optIdx: number) => {
    if (selected !== null) return // already answered
    setSelected(optIdx)
    const correct = currentQ.options[optIdx].correct
    if (correct) {
      setCorrectCount(c => c + 1)
    } else {
      setWrongWords(w => [...w, currentQ.word])
    }
  }, [selected, currentQ])

  const handleNext = useCallback(() => {
    if (qIndex + 1 >= questions.length) {
      setShowResult(true)
    } else {
      setQIndex(i => i + 1)
      setSelected(null)
    }
  }, [qIndex, questions.length])

  const handleRestart = useCallback(() => {
    setQIndex(0)
    setSelected(null)
    setCorrectCount(0)
    setWrongWords([])
    setShowResult(false)
    setLoading(true)
    // Re-generate
    fetch(`/api/books/${LISTENING_BOOK_ID}/words?per_page=200`)
      .then(r => r.json())
      .then((data: { words?: Word[] }) => {
        const words: Word[] = data.words || []
        const picked = shuffleArray(words).slice(0, TEST_WORD_COUNT)
        const testQs: TestQuestion[] = picked.map(w => ({
          word: w,
          options: generateTestOptions(w, words)
        }))
        setQuestions(testQs)
        setLoading(false)
        setTimeout(() => playWord(testQs[0].word.word), 600)
      })
  }, [])

  if (loading) {
    return (
      <div className="vocab-test">
        <div className="vocab-test-loading">
          <div className="loading-spinner" />
          <p>正在加载词汇...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="vocab-test">
        <div className="vocab-test-error">
          <p>{error}</p>
          <button onClick={() => navigate(-1)}>返回</button>
        </div>
      </div>
    )
  }

  if (showResult) {
    const accuracy = Math.round((correctCount / questions.length) * 100)
    return (
      <div className="vocab-test">
        <div className="vocab-test-header">
          <button className="vocab-test-back" onClick={() => navigate(-1)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <span className="vocab-test-title">词汇量测试</span>
        </div>
        <ResultScreen
          result={{ correct: correctCount, total: questions.length, accuracy, wrongWords }}
          onRestart={handleRestart}
          onBack={() => navigate(-1)}
        />
      </div>
    )
  }

  const progress = (qIndex + 1) / questions.length
  const isCorrect = selected !== null ? currentQ.options[selected].correct : null

  return (
    <div className="vocab-test">
      {/* Header */}
      <div className="vocab-test-header">
        <button className="vocab-test-back" onClick={() => navigate(-1)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <span className="vocab-test-title">词汇量测试</span>
        <div className="vocab-test-score">
          <span className="score-correct">{correctCount}</span>
          <span className="score-sep">/</span>
          <span className="score-total">{qIndex}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="vocab-test-progress">
        <div className="vocab-test-progress-fill" style={{ width: `${progress * 100}%` }} />
      </div>

      {/* Score badge */}
      <div className="vocab-test-badge">
        <div className="vocab-test-badge-num" style={{ color: 'var(--accent)' }}>{qIndex + 1}</div>
        <div className="vocab-test-badge-label">/{questions.length} 题</div>
      </div>

      {/* Play button */}
      <div className="vocab-test-play-area">
        <button className="vocab-test-play-btn" onClick={() => playWord(currentQ.word.word)}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
        </button>
        <div className="vocab-test-hint">点击播放发音</div>
      </div>

      {/* Options */}
      <div className="vocab-test-options">
        {currentQ.options.map((opt, idx) => {
          let cls = 'vocab-test-opt'
          if (selected !== null) {
            if (idx === currentQ.options.findIndex(o => o.correct)) cls += ' correct'
            else if (idx === selected) cls += ' wrong'
          }
          return (
            <button
              key={idx}
              className={cls}
              onClick={() => handleOptionSelect(idx)}
              disabled={selected !== null}
            >
              <span className="opt-indicator">{String.fromCharCode(65 + idx)}</span>
              <span className="opt-text">{opt.text}</span>
            </button>
          )
        })}
      </div>

      {/* Feedback + Next */}
      {selected !== null && (
        <div className="vocab-test-feedback">
          <div className={`feedback-text ${isCorrect ? 'correct' : 'wrong'}`}>
            {isCorrect ? '✓ 正确！' : `✗ 正确答案是：${currentQ.options.find(o => o.correct)?.text}`}
          </div>
          <button className="vocab-test-next-btn" onClick={handleNext}>
            {qIndex + 1 >= questions.length ? '查看结果' : '下一题'}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}
