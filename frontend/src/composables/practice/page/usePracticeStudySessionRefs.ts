import { useEffect, useRef } from 'react'
import type { PracticeMode } from '../../../features/practice/types'

export interface PracticeStudySessionRefs {
  sessionStartRef: React.MutableRefObject<number>
  sessionLastActiveAtRef: React.MutableRefObject<number>
  sessionIdRef: React.MutableRefObject<number | null>
  sessionCorrectRef: React.MutableRefObject<number>
  sessionWrongRef: React.MutableRefObject<number>
  correctCountRef: React.MutableRefObject<number>
  wrongCountRef: React.MutableRefObject<number>
  completedSessionDurationSecondsRef: React.MutableRefObject<number | null>
  sessionLoggedRef: React.MutableRefObject<boolean>
  followInteractionRef: React.MutableRefObject<boolean>
  radioInteractionRef: React.MutableRefObject<boolean>
  radioWordsStudiedRef: React.MutableRefObject<number>
  wordsLearnedBaselineRef: React.MutableRefObject<number>
  uniqueAnsweredRef: React.MutableRefObject<Set<string>>
  sessionUniqueWordsRef: React.MutableRefObject<Set<string>>
  sessionBookIdRef: React.MutableRefObject<string | null>
  sessionChapterIdRef: React.MutableRefObject<string | null>
  currentModeRef: React.MutableRefObject<PracticeMode | undefined>
  effectiveSessionModeRef: React.MutableRefObject<string>
  activeSessionModeRef: React.MutableRefObject<string>
  previousEffectiveModeRef: React.MutableRefObject<string>
}

interface UsePracticeStudySessionRefsParams {
  mode?: PracticeMode
  errorMode: boolean
  practiceBookId: string | null
  practiceChapterId: string | null
  correctCount: number
  wrongCount: number
}

export function usePracticeStudySessionRefs({
  mode,
  errorMode,
  practiceBookId,
  practiceChapterId,
  correctCount,
  wrongCount,
}: UsePracticeStudySessionRefsParams): PracticeStudySessionRefs {
  const initialSessionMode = errorMode ? 'errors' : (mode ?? 'smart')
  const refs: PracticeStudySessionRefs = {
    sessionStartRef: useRef<number>(0),
    sessionLastActiveAtRef: useRef<number>(0),
    sessionIdRef: useRef<number | null>(null),
    sessionCorrectRef: useRef(0),
    sessionWrongRef: useRef(0),
    correctCountRef: useRef(0),
    wrongCountRef: useRef(0),
    completedSessionDurationSecondsRef: useRef<number | null>(null),
    sessionLoggedRef: useRef(false),
    followInteractionRef: useRef(false),
    radioInteractionRef: useRef(false),
    radioWordsStudiedRef: useRef(0),
    wordsLearnedBaselineRef: useRef(0),
    uniqueAnsweredRef: useRef<Set<string>>(new Set()),
    sessionUniqueWordsRef: useRef<Set<string>>(new Set()),
    sessionBookIdRef: useRef<string | null>(practiceBookId),
    sessionChapterIdRef: useRef<string | null>(practiceChapterId),
    currentModeRef: useRef(mode),
    effectiveSessionModeRef: useRef(initialSessionMode),
    activeSessionModeRef: useRef(initialSessionMode),
    previousEffectiveModeRef: useRef(initialSessionMode),
  }

  useEffect(() => { refs.correctCountRef.current = correctCount }, [correctCount, refs.correctCountRef])
  useEffect(() => { refs.wrongCountRef.current = wrongCount }, [wrongCount, refs.wrongCountRef])
  useEffect(() => { refs.sessionBookIdRef.current = practiceBookId }, [practiceBookId, refs.sessionBookIdRef])
  useEffect(() => { refs.sessionChapterIdRef.current = practiceChapterId }, [practiceChapterId, refs.sessionChapterIdRef])

  return refs
}
