import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Word } from './practice/types'
import { shuffleArray, playWordAudio } from './practice/utils'
import { PageSkeleton } from './ui'

const TEST_WORD_COUNT = 20
const LISTENING_BOOK_ID = 'ielts_listening_premium'

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

function playWord(word: string) {
  playWordAudio(word, {})
}

function generateTestOptions(correctWord: Word, allWords: Word[]): { text: string; correct: boolean }[] {
  const others = allWords.filter(w => w.word !== correctWord.word)
  const shuffled = shuffleArray(others).slice(0, 3)
  const wrongOptions = shuffled.map(w => w.definition)

  const options = [
    { text: correctWord.definition, correct: true },
    ...wrongOptions.map(text => ({ text, correct: false })),
  ]

  return shuffleArray(options)
}

function ResultScreen({ result, onRestart, onBack }: { result: TestResult; onRestart: () => void; onBack: () => void }) {
  const pct = result.accuracy
  const ringToneClass = pct >= 80 ? 'result-ring-progress--success' : pct >= 50 ? 'result-ring-progress--accent' : 'result-ring-progress--error'
  const circumference = 2 * Math.PI * 52
  const dashOffset = circumference * (1 - pct / 100)

  return (
    <div className="vocab-test-result">
      <div className="result-ring-wrap">
        <svg width="130" height="130" viewBox="0 0 130 130">
          <circle cx="65" cy="65" r="52" fill="none" stroke="var(--border)" strokeWidth="10" />
          <circle
            cx="65"
            cy="65"
            r="52"
            fill="none"
            className={ringToneClass}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            transform="rotate(-90 65 65)"
          />
        </svg>
        <div className="result-ring-label">
          <div className="result-pct">{pct}%</div>
          <div className="result-score">{result.correct}/{result.total}</div>
        </div>
      </div>

      <div className="result-msg">
        {pct >= 90 ? '太棒了，词汇量很稳。' :
         pct >= 70 ? '表现不错，继续保持。' :
         pct >= 50 ? '还需要加强，继续练习。' :
         '建议多听多读，继续积累词汇。'}
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

  useEffect(() => {
    fetch(`/api/books/${LISTENING_BOOK_ID}/words?per_page=200`)
      .then(r => r.json())
      .then((data: { words?: Word[] }) => {
        const words: Word[] = data.words || []
        if (words.length < 4) {
          setError('词汇量不足，无法生成测试')
          setLoading(false)
          return
        }
        const picked = shuffleArray(words).slice(0, TEST_WORD_COUNT)
        const testQs: TestQuestion[] = picked.map(w => ({
          word: w,
          options: generateTestOptions(w, words),
        }))
        setQuestions(testQs)
        setLoading(false)
        setTimeout(() => playWord(testQs[0].word.word), 600)
      })
      .catch(() => {
        setError('加载词汇失败')
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    if (currentQ && !showResult) {
      setTimeout(() => playWord(currentQ.word.word), 300)
    }
  }, [qIndex, showResult, currentQ])

  const handleOptionSelect = useCallback((optIdx: number) => {
    if (selected !== null) return
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

    fetch(`/api/books/${LISTENING_BOOK_ID}/words?per_page=200`)
      .then(r => r.json())
      .then((data: { words?: Word[] }) => {
        const words: Word[] = data.words || []
        const picked = shuffleArray(words).slice(0, TEST_WORD_COUNT)
        const testQs: TestQuestion[] = picked.map(w => ({
          word: w,
          options: generateTestOptions(w, words),
        }))
        setQuestions(testQs)
        setLoading(false)
        setTimeout(() => playWord(testQs[0].word.word), 600)
      })
  }, [])

  if (loading) {
    return (
      <div className="vocab-test">
        <PageSkeleton variant="quiz" />
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
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>
        <ResultScreen
          result={{
            correct: correctCount,
            total: questions.length,
            accuracy,
            wrongWords,
          }}
          onRestart={handleRestart}
          onBack={() => navigate(-1)}
        />
      </div>
    )
  }

  return (
    <div className="vocab-test">
      <div className="vocab-test-header">
        <button className="vocab-test-back" onClick={() => navigate(-1)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="vocab-test-progress">
          {qIndex + 1} / {questions.length}
        </div>
      </div>

      <div className="vocab-test-card">
        <button className="vocab-test-audio" onClick={() => playWord(currentQ.word.word)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
        </button>

        <div className="vocab-test-options">
          {currentQ.options.map((option, index) => {
            const isSelected = selected === index
            const isCorrect = option.correct
            const statusClass = selected === null
              ? ''
              : isCorrect
                ? ' correct'
                : isSelected
                  ? ' wrong'
                  : ''

            return (
              <button
                key={`${currentQ.word.word}-${option.text}`}
                className={`vocab-test-option${statusClass}`}
                onClick={() => handleOptionSelect(index)}
                disabled={selected !== null}
              >
                <span className="vocab-test-option-index">{index + 1}</span>
                <span>{option.text}</span>
              </button>
            )
          })}
        </div>

        <div className="vocab-test-actions">
          <button className="vocab-test-secondary" onClick={() => playWord(currentQ.word.word)}>
            再听一遍
          </button>
          <button
            className="vocab-test-primary"
            onClick={handleNext}
            disabled={selected === null}
          >
            {qIndex + 1 >= questions.length ? '查看结果' : '下一题'}
          </button>
        </div>
      </div>
    </div>
  )
}
