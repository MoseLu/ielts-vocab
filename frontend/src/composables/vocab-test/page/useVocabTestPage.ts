import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Word } from '../../../components/practice/types'
import { playWordAudio, shuffleArray } from '../../../components/practice/utils'

const TEST_WORD_COUNT = 20
const LISTENING_BOOK_ID = 'ielts_listening_premium'

export interface TestQuestion {
  word: Word
  options: Array<{ text: string; correct: boolean }>
}

export interface TestResult {
  correct: number
  total: number
  accuracy: number
  wrongWords: Word[]
}

function playWord(word: string) {
  void playWordAudio(word, {})
}

function generateTestOptions(correctWord: Word, allWords: Word[]): Array<{ text: string; correct: boolean }> {
  const others = allWords.filter(word => word.word !== correctWord.word)
  const shuffled = shuffleArray(others).slice(0, 3)
  const wrongOptions = shuffled.map(word => word.definition)

  return shuffleArray([
    { text: correctWord.definition, correct: true },
    ...wrongOptions.map(text => ({ text, correct: false })),
  ])
}

function buildQuestions(words: Word[]): TestQuestion[] {
  return shuffleArray(words).slice(0, TEST_WORD_COUNT).map(word => ({
    word,
    options: generateTestOptions(word, words),
  }))
}

export function useVocabTestPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [questions, setQuestions] = useState<TestQuestion[]>([])
  const [qIndex, setQIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongWords, setWrongWords] = useState<Word[]>([])
  const autoPlayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const currentQuestion = questions[qIndex] ?? null

  const clearPendingAutoPlay = useCallback(() => {
    if (autoPlayTimerRef.current == null) return
    clearTimeout(autoPlayTimerRef.current)
    autoPlayTimerRef.current = null
  }, [])

  const loadQuestions = useCallback(async () => {
    clearPendingAutoPlay()
    setLoading(true)
    setError('')
    setQuestions([])
    setQIndex(0)
    setSelected(null)
    setShowResult(false)
    setCorrectCount(0)
    setWrongWords([])

    try {
      const response = await fetch(`/api/books/${LISTENING_BOOK_ID}/words?per_page=200`)
      const data = await response.json() as { words?: Word[] }
      const words = data.words || []
      if (words.length < 4) {
        setError('词汇量不足，无法生成测试')
        return
      }

      setQuestions(buildQuestions(words))
    } catch {
      setError('加载词汇失败')
    } finally {
      setLoading(false)
    }
  }, [clearPendingAutoPlay])

  useEffect(() => {
    void loadQuestions()
  }, [loadQuestions])

  useEffect(() => {
    clearPendingAutoPlay()
    if (!currentQuestion || showResult) return

    autoPlayTimerRef.current = setTimeout(() => {
      autoPlayTimerRef.current = null
      playWord(currentQuestion.word.word)
    }, 300)

    return clearPendingAutoPlay
  }, [clearPendingAutoPlay, currentQuestion, qIndex, showResult])

  useEffect(() => clearPendingAutoPlay, [clearPendingAutoPlay])

  const handlePlayWord = useCallback((word: string) => {
    clearPendingAutoPlay()
    playWord(word)
  }, [clearPendingAutoPlay])

  const replayCurrentQuestion = useCallback(() => {
    if (!currentQuestion) return
    handlePlayWord(currentQuestion.word.word)
  }, [currentQuestion, handlePlayWord])

  const handleOptionSelect = useCallback((optionIndex: number) => {
    if (!currentQuestion || selected !== null) return

    setSelected(optionIndex)
    if (currentQuestion.options[optionIndex].correct) {
      setCorrectCount(count => count + 1)
      return
    }

    setWrongWords(words => [...words, currentQuestion.word])
  }, [currentQuestion, selected])

  const handleNext = useCallback(() => {
    if (questions.length === 0) return

    if (qIndex + 1 >= questions.length) {
      setShowResult(true)
      return
    }

    setQIndex(index => index + 1)
    setSelected(null)
  }, [qIndex, questions.length])

  const handleRestart = useCallback(() => {
    void loadQuestions()
  }, [loadQuestions])

  const handleBack = useCallback(() => {
    navigate(-1)
  }, [navigate])

  const result = useMemo<TestResult | null>(() => {
    if (!showResult || questions.length === 0) return null
    return {
      correct: correctCount,
      total: questions.length,
      accuracy: Math.round((correctCount / questions.length) * 100),
      wrongWords,
    }
  }, [correctCount, questions.length, showResult, wrongWords])

  return {
    loading,
    error,
    questions,
    currentQuestion,
    qIndex,
    selected,
    showResult,
    result,
    handleBack,
    handleRestart,
    handleNext,
    handleOptionSelect,
    replayCurrentQuestion,
  }
}
