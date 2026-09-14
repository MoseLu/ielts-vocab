import { useRef, useState } from 'react'
import type { ErrorReviewRoundResults, MobileWord, PracticeQueueSource } from '@ielts-vocab/app-core'
import type { HydratedPracticeSession } from './practiceSessionLifecycle'

export function usePracticeSessionState() {
  const [queueSource, setQueueSource] = useState<PracticeQueueSource>('chapter')
  const [queue, setQueue] = useState<MobileWord[]>([])
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [errorRoundResults, setErrorRoundResults] = useState<ErrorReviewRoundResults>({})
  const [errorReviewRound, setErrorReviewRound] = useState(1)
  const [feedback, setFeedback] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const chapterBaselineRef = useRef({ correctCount: 0, wrongCount: 0 })
  const startedAtRef = useRef(Date.now())

  function applyHydratedSession(params: {
    queueSource: PracticeQueueSource
    savedErrorProgress?: {
      results: ErrorReviewRoundResults
      round: number
    } | null
    session: HydratedPracticeSession
  }) {
    setQueueSource(params.queueSource)
    setQueue(params.session.queue)
    setIndex(params.session.index)
    setCorrectCount(params.session.correctCount)
    setWrongCount(params.session.wrongCount)
    setErrorRoundResults(params.savedErrorProgress?.results ?? {})
    setErrorReviewRound(params.savedErrorProgress?.round ?? 1)
    chapterBaselineRef.current = params.session.chapterBaseline
    setAnswer('')
    startedAtRef.current = Date.now()
  }

  function startErrorReviewRound(params: {
    round: number
    words: MobileWord[]
  }) {
    setQueue(params.words)
    setIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    setErrorRoundResults({})
    setErrorReviewRound(params.round)
    setFeedback('已生成下一轮，仅包含本轮仍答错的词。')
    startedAtRef.current = Date.now()
  }

  return {
    answer,
    applyHydratedSession,
    chapterBaselineRef,
    correctCount,
    error,
    errorReviewRound,
    errorRoundResults,
    feedback,
    index,
    loading,
    queue,
    queueSource,
    setAnswer,
    setCorrectCount,
    setError,
    setErrorReviewRound,
    setErrorRoundResults,
    setFeedback,
    setIndex,
    setLoading,
    setQueue,
    setQueueSource,
    setWrongCount,
    startedAtRef,
    startErrorReviewRound,
    wrongCount,
  }
}
