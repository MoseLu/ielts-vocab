import { useCallback, useEffect, useRef, useState } from 'react'
import type { MutableRefObject } from 'react'
import type { AppSettings, PracticeMode, RadioQuickSettings } from '../../../components/practice/types'
import {
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  cancelSession,
  flushStudySessionOnPageHide,
  logSession,
  startSession,
  touchStudySessionActivity,
  updateStudySessionSnapshot,
} from '../../../hooks/useAIChat'
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
  computeChapterWordsLearned: (cap: number) => number
  registerAnsweredWord: (word: string) => void
  markRadioSessionInteraction: () => void
  handleRadioProgressChange: (wordsStudied: number) => void
  syncCurrentSessionSnapshot: (activeAt?: number) => void
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

  const sessionStartRef = useRef<number>(0)
  const sessionIdRef = useRef<number | null>(null)
  const pendingSessionCancelRef = useRef(false)
  const sessionCorrectRef = useRef(0)
  const sessionWrongRef = useRef(0)
  const correctCountRef = useRef(0)
  const wrongCountRef = useRef(0)
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

  useEffect(() => { correctCountRef.current = correctCount }, [correctCount])
  useEffect(() => { wrongCountRef.current = wrongCount }, [wrongCount])
  useEffect(() => { currentModeRef.current = mode }, [mode])
  useEffect(() => { sessionBookIdRef.current = practiceBookId }, [practiceBookId])
  useEffect(() => { sessionChapterIdRef.current = practiceChapterId }, [practiceChapterId])
  useEffect(() => {
    effectiveSessionModeRef.current = errorMode ? 'errors' : (mode ?? 'smart')
  }, [errorMode, mode])

  useEffect(() => {
    return () => {
      if (currentModeRef.current === 'quickmemory') return
      if (sessionLoggedRef.current) return
      const sessionUnique = sessionUniqueWordsRef.current.size
      const isRadio = currentModeRef.current === 'radio'
      const sessionStart = sessionStartRef.current
      const durationSeconds = sessionStart > 0 ? Math.round((Date.now() - sessionStart) / 1000) : 0
      const passiveDurationEnough = durationSeconds >= PASSIVE_STUDY_SESSION_MIN_SECONDS
      const shouldCancelSession = isRadio
        ? (!radioInteractionRef.current && radioWordsStudiedRef.current <= 0 && !passiveDurationEnough)
        : (sessionUnique <= 0 && !passiveDurationEnough)

      if (shouldCancelSession) {
        pendingSessionCancelRef.current = true
        cancelSession(sessionIdRef.current)
        return
      }

      updateStudySessionSnapshot({
        sessionId: sessionIdRef.current,
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        startedAt: sessionStartRef.current,
        activeAt: Date.now(),
        wordsStudied: isRadio ? radioWordsStudiedRef.current : sessionUniqueWordsRef.current.size,
        correctCount: sessionCorrectRef.current,
        wrongCount: sessionWrongRef.current,
      })

      logSession({
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        wordsStudied: isRadio ? radioWordsStudiedRef.current : sessionUnique,
        correctCount: sessionCorrectRef.current,
        wrongCount: sessionWrongRef.current,
        durationSeconds,
        startedAt: sessionStart,
        sessionId: sessionIdRef.current,
      })
      syncSmartStatsToBackend({
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        mode: effectiveSessionModeRef.current,
      })
    }
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
      if (currentModeRef.current === 'quickmemory') return
      if (sessionLoggedRef.current || sessionStartRef.current <= 0) return
      const isRadio = currentModeRef.current === 'radio'
      flushStudySessionOnPageHide({
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        wordsStudied: isRadio ? radioWordsStudiedRef.current : sessionUniqueWordsRef.current.size,
        correctCount: sessionCorrectRef.current,
        wrongCount: sessionWrongRef.current,
        startedAt: sessionStartRef.current,
        sessionId: sessionIdRef.current,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [])

  const handleRadioSettingChange = useCallback((key: keyof RadioQuickSettings, value: string | boolean) => {
    setSettings(prev => writeAppSettingsToStorage({ ...prev, [key]: value }))
  }, [])

  const beginSession = useCallback((context?: { bookId?: string | null; chapterId?: string | null }) => {
    const sessionBookId = context?.bookId ?? sessionBookIdRef.current
    const sessionChapterId = context?.chapterId ?? sessionChapterIdRef.current
    sessionBookIdRef.current = sessionBookId
    sessionChapterIdRef.current = sessionChapterId

    if (effectiveSessionModeRef.current === 'quickmemory') {
      sessionStartRef.current = 0
      sessionIdRef.current = null
      sessionCorrectRef.current = 0
      sessionWrongRef.current = 0
      sessionUniqueWordsRef.current = new Set()
      sessionLoggedRef.current = false
      radioInteractionRef.current = false
      radioWordsStudiedRef.current = 0
      pendingSessionCancelRef.current = false
      return
    }

    sessionStartRef.current = Date.now()
    sessionCorrectRef.current = 0
    sessionWrongRef.current = 0
    sessionUniqueWordsRef.current = new Set()
    sessionLoggedRef.current = false
    radioInteractionRef.current = false
    radioWordsStudiedRef.current = 0
    pendingSessionCancelRef.current = false

    startSession({
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookId,
      chapterId: sessionChapterId,
    }).then(id => {
      sessionIdRef.current = id
      if (pendingSessionCancelRef.current && id) {
        cancelSession(id)
      }
    }).catch(() => {})
  }, [])

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

  const markRadioSessionInteraction = useCallback(() => {
    radioInteractionRef.current = true
    touchStudySessionActivity(sessionIdRef.current)
  }, [])

  const handleRadioProgressChange = useCallback((wordsStudied: number) => {
    radioWordsStudiedRef.current = Math.max(radioWordsStudiedRef.current, wordsStudied)
    updateStudySessionSnapshot({
      sessionId: sessionIdRef.current,
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookIdRef.current,
      chapterId: sessionChapterIdRef.current,
      startedAt: sessionStartRef.current,
      activeAt: Date.now(),
      wordsStudied: radioWordsStudiedRef.current,
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    })
  }, [])

  const syncCurrentSessionSnapshot = useCallback((activeAt = Date.now()) => {
    const isRadio = currentModeRef.current === 'radio'
    updateStudySessionSnapshot({
      sessionId: sessionIdRef.current,
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookIdRef.current,
      chapterId: sessionChapterIdRef.current,
      startedAt: sessionStartRef.current,
      activeAt,
      wordsStudied: isRadio ? radioWordsStudiedRef.current : sessionUniqueWordsRef.current.size,
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    })
  }, [])

  return {
    settings,
    radioQuickSettings: {
      playbackSpeed: String(settings.playbackSpeed ?? '0.8'),
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
    computeChapterWordsLearned,
    registerAnsweredWord,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
  }
}
