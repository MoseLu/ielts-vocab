import { useCallback, useEffect, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'

interface UsePracticeSpellingFeedbackParams {
  spellingFeedbackLocked: boolean
  spellingFeedbackDismissing: boolean
  spellingResult: 'correct' | 'wrong' | null
  setSpellingInput: Dispatch<SetStateAction<string>>
  setSpellingResult: Dispatch<SetStateAction<'correct' | 'wrong' | null>>
  setSpellingFeedbackLocked: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackDismissing: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackSnapshot: Dispatch<SetStateAction<string | null>>
}

export function usePracticeSpellingFeedback({
  spellingFeedbackLocked,
  spellingFeedbackDismissing,
  spellingResult,
  setSpellingInput,
  setSpellingResult,
  setSpellingFeedbackLocked,
  setSpellingFeedbackDismissing,
  setSpellingFeedbackSnapshot,
}: UsePracticeSpellingFeedbackParams) {
  const spellingRetryTimerRef = useRef<number | null>(null)
  const spellingFeedbackDismissTimerRef = useRef<number | null>(null)

  const clearSpellingRetryTimer = useCallback(() => {
    if (spellingRetryTimerRef.current === null) return
    window.clearTimeout(spellingRetryTimerRef.current)
    spellingRetryTimerRef.current = null
  }, [])

  const clearSpellingFeedbackDismissTimer = useCallback(() => {
    if (spellingFeedbackDismissTimerRef.current === null) return
    window.clearTimeout(spellingFeedbackDismissTimerRef.current)
    spellingFeedbackDismissTimerRef.current = null
  }, [])

  const handleSpellingInputChange = useCallback((value: string) => {
    if (spellingFeedbackLocked && spellingResult === 'wrong' && !spellingFeedbackDismissing) {
      clearSpellingRetryTimer()
      clearSpellingFeedbackDismissTimer()
      setSpellingFeedbackLocked(false)
      setSpellingFeedbackDismissing(true)
      spellingFeedbackDismissTimerRef.current = window.setTimeout(() => {
        setSpellingResult(current => (current === 'wrong' ? null : current))
        setSpellingFeedbackDismissing(false)
        setSpellingFeedbackSnapshot(null)
        spellingFeedbackDismissTimerRef.current = null
      }, 120)
    }

    setSpellingInput(value)
  }, [
    clearSpellingFeedbackDismissTimer,
    clearSpellingRetryTimer,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    spellingFeedbackDismissing,
    spellingFeedbackLocked,
    spellingResult,
  ])

  useEffect(() => () => {
    clearSpellingRetryTimer()
    clearSpellingFeedbackDismissTimer()
  }, [clearSpellingFeedbackDismissTimer, clearSpellingRetryTimer])

  return {
    clearSpellingRetryTimer,
    clearSpellingFeedbackDismissTimer,
    handleSpellingInputChange,
    spellingRetryTimerRef,
  }
}
