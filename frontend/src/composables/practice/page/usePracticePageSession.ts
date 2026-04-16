import { useCallback, useEffect, useRef, useState } from 'react'
import type { MutableRefObject } from 'react'
import type { AppSettings, PracticeMode, RadioQuickSettings } from '../../../components/practice/types'
import * as AIChat from '../../../hooks/useAIChat'
import { readAppSettingsFromStorage, writeAppSettingsToStorage } from '../../../lib/appSettings'
import { syncSmartStatsToBackend } from '../../../lib/smartMode'

interface UsePracticePageSessionParams {
  mode?: PracticeMode
  errorMode: boolean
  chapterId: string | null
  practiceBookId: string | null
  practiceChapterId: string | null
  correctCount: number
  wrongCount: number
}

interface UsePracticePageSessionResult {
  settings: AppSettings
  radioQuickSettings: RadioQuickSettings
  handleRadioSettingChange: (key: keyof RadioQuickSettings, value: string | boolean) => void
  sessionStartRef: MutableRefObject<number>
  sessionIdRef: MutableRefObject<number | null>
  sessionCorrectRef: MutableRefObject<number>
  sessionWrongRef: MutableRefObject<number>
  correctCountRef: MutableRefObject<number>
  wrongCountRef: MutableRefObject<number>
  completedSessionDurationSecondsRef: MutableRefObject<number | null>
  sessionLoggedRef: MutableRefObject<boolean>
  currentModeRef: MutableRefObject<PracticeMode | undefined>
  effectiveSessionModeRef: MutableRefObject<string>
  sessionBookIdRef: MutableRefObject<string | null>
  sessionChapterIdRef: MutableRefObject<string | null>
  radioWordsStudiedRef: MutableRefObject<number>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  sessionUniqueWordsRef: MutableRefObject<Set<string>>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  prepareSessionForLearningAction: (activityAt?: number) => Promise<void>
  completeCurrentSession: () => Promise<number>
  computeChapterWordsLearned: (cap: number) => number
  registerAnsweredWord: (word: string) => void
  markRadioSessionInteraction: () => Promise<void>
  handleRadioProgressChange: (wordsStudied: number) => void
  syncCurrentSessionSnapshot: (activeAt?: number) => void
  isCurrentSessionActive: (at?: number) => boolean
}

function normalizeDuration(total: number | null, extra = 0): number {
  return Math.max(0, Math.round(total ?? 0) + Math.max(0, Math.round(extra)))
}

function getOptionalAIChatFunction<T extends (...args: any[]) => any>(key: string): T | null {
  try {
    const value = Reflect.get(AIChat as object, key)
    return typeof value === 'function' ? (value as T) : null
  } catch {
    return null
  }
}

function getAIChatNumber(key: string, fallback: number): number {
  try {
    const value = Reflect.get(AIChat as object, key)
    return typeof value === 'number' ? value : fallback
  } catch {
    return fallback
  }
}

export function usePracticePageSession({
  mode,
  errorMode,
  chapterId,
  practiceBookId,
  practiceChapterId,
  correctCount,
  wrongCount,
}: UsePracticePageSessionParams): UsePracticePageSessionResult {
  const [settings, setSettings] = useState<AppSettings>(() => readAppSettingsFromStorage())
  const isStudySessionActive = getOptionalAIChatFunction<typeof AIChat.isStudySessionActive>('isStudySessionActive')
  const finalizeStudySessionSegment = getOptionalAIChatFunction<typeof AIChat.finalizeStudySessionSegment>('finalizeStudySessionSegment')
  const markStudySessionRecoveryHandled = getOptionalAIChatFunction<typeof AIChat.markStudySessionRecoveryHandled>('markStudySessionRecoveryHandled')
  const prepareStudySessionForLearningAction = getOptionalAIChatFunction<typeof AIChat.prepareStudySessionForLearningAction>('prepareStudySessionForLearningAction')
  const passiveStudySessionMinSeconds = getAIChatNumber('PASSIVE_STUDY_SESSION_MIN_SECONDS', 30)

  const sessionStartRef = useRef<number>(0)
  const sessionLastActiveAtRef = useRef<number>(0)
  const sessionIdRef = useRef<number | null>(null)
  const sessionCorrectRef = useRef(0)
  const sessionWrongRef = useRef(0)
  const correctCountRef = useRef(0)
  const wrongCountRef = useRef(0)
  const completedSessionDurationSecondsRef = useRef<number | null>(null)
  const sessionLoggedRef = useRef(false)
  const radioInteractionRef = useRef(false)
  const radioWordsStudiedRef = useRef(0)
  const wordsLearnedBaselineRef = useRef(0)
  const uniqueAnsweredRef = useRef<Set<string>>(new Set())
  const sessionUniqueWordsRef = useRef<Set<string>>(new Set())
  const sessionBookIdRef = useRef<string | null>(practiceBookId)
  const sessionChapterIdRef = useRef<string | null>(practiceChapterId)
  const currentModeRef = useRef(mode)
  const effectiveSessionModeRef = useRef(errorMode ? 'errors' : (mode ?? 'smart'))
  const activeSessionModeRef = useRef(errorMode ? 'errors' : (mode ?? 'smart'))
  const previousEffectiveModeRef = useRef(errorMode ? 'errors' : (mode ?? 'smart'))

  useEffect(() => { correctCountRef.current = correctCount }, [correctCount])
  useEffect(() => { wrongCountRef.current = wrongCount }, [wrongCount])
  useEffect(() => { sessionBookIdRef.current = practiceBookId }, [practiceBookId])
  useEffect(() => { sessionChapterIdRef.current = practiceChapterId }, [practiceChapterId])

  const getCurrentSegmentWordsStudied = useCallback((sessionMode = activeSessionModeRef.current) => (
    sessionMode === 'radio'
      ? radioWordsStudiedRef.current
      : sessionUniqueWordsRef.current.size
  ), [])

  const accumulateCompletedDuration = useCallback((durationSeconds: number) => {
    completedSessionDurationSecondsRef.current = normalizeDuration(
      completedSessionDurationSecondsRef.current,
      durationSeconds,
    )
  }, [])

  const resetCurrentSegmentState = useCallback(() => {
    sessionStartRef.current = 0
    sessionLastActiveAtRef.current = 0
    sessionIdRef.current = null
    sessionCorrectRef.current = 0
    sessionWrongRef.current = 0
    sessionUniqueWordsRef.current = new Set()
    radioInteractionRef.current = false
    radioWordsStudiedRef.current = 0
  }, [])

  const syncCurrentSessionSnapshot = useCallback((activeAt?: number) => {
    if (sessionStartRef.current <= 0) return
    const nextActiveAt = activeAt ?? sessionLastActiveAtRef.current
    if (nextActiveAt > 0) {
      sessionLastActiveAtRef.current = Math.max(sessionLastActiveAtRef.current, nextActiveAt)
    }

    if (sessionIdRef.current == null) return
    AIChat.updateStudySessionSnapshot({
      sessionId: sessionIdRef.current,
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookIdRef.current,
      chapterId: sessionChapterIdRef.current,
      startedAt: sessionStartRef.current,
      ...(nextActiveAt > 0 ? { activeAt: nextActiveAt } : {}),
      wordsStudied: getCurrentSegmentWordsStudied(),
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    })
  }, [getCurrentSegmentWordsStudied])

  const isCurrentSessionActive = useCallback((at = Date.now()) => {
    if (sessionStartRef.current <= 0) return false
    if (isStudySessionActive) {
      return isStudySessionActive({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
        lastActiveAt: sessionLastActiveAtRef.current,
      }, at)
    }
    return true
  }, [isStudySessionActive])

  const closeActiveSegment = useCallback(async ({
    markRoundCompleted = false,
    syncStats = true,
    accumulateIntoCompletedRef = true,
  }: {
    markRoundCompleted?: boolean
    syncStats?: boolean
    accumulateIntoCompletedRef?: boolean
  } = {}) => {
    if (sessionStartRef.current <= 0 || sessionLoggedRef.current) {
      if (markRoundCompleted) {
        sessionLoggedRef.current = true
      }
      return completedSessionDurationSecondsRef.current ?? 0
    }

    const sessionMode = activeSessionModeRef.current
    const sessionBookId = sessionBookIdRef.current
    const sessionChapterId = sessionChapterIdRef.current
    if (sessionMode === 'quickmemory') {
      if (markRoundCompleted) {
        sessionLoggedRef.current = true
      }
      resetCurrentSegmentState()
      return completedSessionDurationSecondsRef.current ?? 0
    }

    const payload = {
      sessionId: sessionIdRef.current,
      mode: sessionMode,
      bookId: sessionBookId,
      chapterId: sessionChapterId,
      startedAt: sessionStartRef.current,
      wordsStudied: getCurrentSegmentWordsStudied(sessionMode),
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    }

    let finalized = { discarded: true, durationSeconds: 0 }
    if (finalizeStudySessionSegment) {
      finalized = await finalizeStudySessionSegment(payload)
    } else {
      const durationSeconds = AIChat.resolveStudySessionDurationSeconds({
        sessionId: payload.sessionId,
        startedAt: payload.startedAt,
      })
      const shouldDiscard = (
        payload.wordsStudied <= 0
        && payload.correctCount <= 0
        && payload.wrongCount <= 0
        && durationSeconds < passiveStudySessionMinSeconds
      )
      markStudySessionRecoveryHandled?.()
      if (shouldDiscard) {
        await AIChat.cancelSession(payload.sessionId)
      } else {
        AIChat.updateStudySessionSnapshot({
          sessionId: payload.sessionId,
          mode: payload.mode,
          bookId: payload.bookId,
          chapterId: payload.chapterId,
          startedAt: payload.startedAt,
          wordsStudied: payload.wordsStudied,
          correctCount: payload.correctCount,
          wrongCount: payload.wrongCount,
        })
        await AIChat.logSession({
          ...payload,
          durationSeconds,
        })
        finalized = { discarded: false, durationSeconds }
      }
    }

    if (!finalized.discarded && accumulateIntoCompletedRef) {
      accumulateCompletedDuration(finalized.durationSeconds)
    }
    if (!finalized.discarded && syncStats) {
      syncSmartStatsToBackend({
        bookId: sessionBookId,
        chapterId: sessionChapterId,
        mode: sessionMode,
      })
    }

    sessionLoggedRef.current = markRoundCompleted
    resetCurrentSegmentState()
    return completedSessionDurationSecondsRef.current ?? 0
  }, [
    accumulateCompletedDuration,
    finalizeStudySessionSegment,
    getCurrentSegmentWordsStudied,
    markStudySessionRecoveryHandled,
    passiveStudySessionMinSeconds,
    resetCurrentSegmentState,
  ])

  const prepareSessionForLearningAction = useCallback(async (activityAt = Date.now()) => {
    if (effectiveSessionModeRef.current === 'quickmemory') return

    const stats = {
      wordsStudied: getCurrentSegmentWordsStudied(),
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    }

    if (prepareStudySessionForLearningAction) {
      const prepared = await prepareStudySessionForLearningAction({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
        lastActiveAt: sessionLastActiveAtRef.current,
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        activityAt,
        ...stats,
      })

      if (prepared.segmented) {
        const finalizedPreviousSegment = prepared.finalizedPreviousSegment
        if (finalizedPreviousSegment && !finalizedPreviousSegment.discarded) {
          accumulateCompletedDuration(finalizedPreviousSegment.durationSeconds)
          syncSmartStatsToBackend({
            bookId: sessionBookIdRef.current,
            chapterId: sessionChapterIdRef.current,
            mode: effectiveSessionModeRef.current,
          })
        }
        sessionCorrectRef.current = 0
        sessionWrongRef.current = 0
        sessionUniqueWordsRef.current = new Set()
        radioInteractionRef.current = false
        radioWordsStudiedRef.current = 0
      }

      sessionStartRef.current = prepared.startedAt
      sessionLastActiveAtRef.current = prepared.lastActiveAt
      sessionIdRef.current = prepared.sessionId
      sessionLoggedRef.current = false
      activeSessionModeRef.current = effectiveSessionModeRef.current
      return
    }

    if (sessionStartRef.current > 0) {
      sessionLastActiveAtRef.current = activityAt
      AIChat.touchStudySessionActivity(sessionIdRef.current, activityAt)
      sessionLoggedRef.current = false
      return
    }

    sessionStartRef.current = activityAt
    sessionLastActiveAtRef.current = activityAt
    sessionLoggedRef.current = false
    activeSessionModeRef.current = effectiveSessionModeRef.current
    sessionIdRef.current = await AIChat.startSession({
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookIdRef.current,
      chapterId: sessionChapterIdRef.current,
    }, {
      skipRecovery: true,
      startedAt: activityAt,
    })
  }, [accumulateCompletedDuration, getCurrentSegmentWordsStudied, prepareStudySessionForLearningAction])

  const completeCurrentSession = useCallback(async () => {
    const totalDurationSeconds = await closeActiveSegment({
      markRoundCompleted: true,
      syncStats: true,
    })
    completedSessionDurationSecondsRef.current = totalDurationSeconds
    return totalDurationSeconds
  }, [closeActiveSegment])

  useEffect(() => {
    const nextMode = errorMode ? 'errors' : (mode ?? 'smart')
    const previousMode = previousEffectiveModeRef.current
    currentModeRef.current = mode
    effectiveSessionModeRef.current = nextMode
    if (
      previousMode !== nextMode
      && sessionStartRef.current > 0
      && activeSessionModeRef.current !== 'quickmemory'
      && !sessionLoggedRef.current
    ) {
      void closeActiveSegment({ syncStats: true, accumulateIntoCompletedRef: false })
    }
    previousEffectiveModeRef.current = nextMode
  }, [closeActiveSegment, errorMode, mode])

  useEffect(() => () => {
    void closeActiveSegment({ syncStats: true, accumulateIntoCompletedRef: false })
  }, [closeActiveSegment])

  useEffect(() => {
    const handlePageHide = () => {
      if (currentModeRef.current === 'quickmemory') return
      if (sessionLoggedRef.current || sessionStartRef.current <= 0) return
      AIChat.flushStudySessionOnPageHide({
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        wordsStudied: getCurrentSegmentWordsStudied(),
        correctCount: sessionCorrectRef.current,
        wrongCount: sessionWrongRef.current,
        startedAt: sessionStartRef.current,
        sessionId: sessionIdRef.current,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [getCurrentSegmentWordsStudied])

  const handleRadioSettingChange = useCallback((key: keyof RadioQuickSettings, value: string | boolean) => {
    setSettings(prev => writeAppSettingsToStorage({ ...prev, [key]: value }))
  }, [])

  const beginSession = useCallback((context?: { bookId?: string | null; chapterId?: string | null }) => {
    if (sessionStartRef.current > 0 && !sessionLoggedRef.current && activeSessionModeRef.current !== 'quickmemory') {
      void closeActiveSegment({ syncStats: true, accumulateIntoCompletedRef: false })
    }

    sessionBookIdRef.current = context?.bookId ?? sessionBookIdRef.current
    sessionChapterIdRef.current = context?.chapterId ?? sessionChapterIdRef.current
    activeSessionModeRef.current = effectiveSessionModeRef.current
    completedSessionDurationSecondsRef.current = null
    sessionLoggedRef.current = false
    resetCurrentSegmentState()
  }, [closeActiveSegment, resetCurrentSegmentState])

  const computeChapterWordsLearned = useCallback((cap: number) => {
    if (!chapterId || !cap) return wordsLearnedBaselineRef.current
    return Math.min(cap, Math.max(wordsLearnedBaselineRef.current, uniqueAnsweredRef.current.size))
  }, [chapterId])

  const registerAnsweredWord = useCallback((word: string) => {
    const key = word.trim().toLowerCase()
    if (!key) return
    sessionUniqueWordsRef.current.add(key)
    if (chapterId) uniqueAnsweredRef.current.add(key)
  }, [chapterId])

  const markRadioSessionInteraction = useCallback(async () => {
    await prepareSessionForLearningAction()
    radioInteractionRef.current = true
  }, [prepareSessionForLearningAction])

  const handleRadioProgressChange = useCallback((wordsStudied: number) => {
    const activeAt = Date.now()
    if (!isCurrentSessionActive(activeAt)) return
    radioWordsStudiedRef.current = Math.max(radioWordsStudiedRef.current, wordsStudied)
    syncCurrentSessionSnapshot(activeAt)
  }, [isCurrentSessionActive, syncCurrentSessionSnapshot])

  return {
    settings,
    radioQuickSettings: {
      playbackSpeed: String(settings.playbackSpeed ?? '1.0'),
      playbackCount: String(settings.playbackCount ?? '1'),
      loopMode: Boolean(settings.loopMode ?? false),
      interval: String(settings.interval ?? '2'),
    },
    handleRadioSettingChange,
    sessionStartRef,
    sessionIdRef,
    sessionCorrectRef,
    sessionWrongRef,
    correctCountRef,
    wrongCountRef,
    completedSessionDurationSecondsRef,
    sessionLoggedRef,
    currentModeRef,
    effectiveSessionModeRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    radioWordsStudiedRef,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    sessionUniqueWordsRef,
    beginSession,
    prepareSessionForLearningAction,
    completeCurrentSession,
    computeChapterWordsLearned,
    registerAnsweredWord,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
    isCurrentSessionActive,
  }
}
