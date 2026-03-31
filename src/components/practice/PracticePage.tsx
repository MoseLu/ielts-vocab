// Practice Page (Main Container)

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition'
import type { PracticePageProps, PracticeMode, Word, ProgressData, AppSettings, Chapter, LastState, WordStatuses, RadioQuickSettings, SmartDimension } from './types'
import { shuffleArray, generateOptions, playWordAudio as playWordUtil, stopAudio as stopAudioUtil } from './utils'
import { DEFAULT_SETTINGS, STORAGE_KEYS } from '../../constants'
import { setGlobalLearningContext } from '../../contexts/AIChatContext'
import { loadSmartStats, recordWordResult, chooseSmartDimension, buildSmartQueue, syncSmartStatsToBackend, loadSmartStatsFromBackend } from '../../lib/smartMode'
import { recordModeAnswer, logSession, startSession, cancelSession } from '../../hooks/useAIChat'
import { apiFetch, buildApiUrl } from '../../lib'
import { addWrongWordToList, loadWrongWords, readWrongWordsFromStorage, writeWrongWordsToStorage } from '../../features/vocabulary/wrongWordsStore'
import { LearnerProfileSchema, type LearnerProfile as BackendLearnerProfile } from '../../lib/schemas'
import { safeParse } from '../../lib/validation'
import PracticeControlBar from './PracticeControlBar'
import WordListPanel from './WordListPanel'
import RadioMode from './RadioMode'
import DictationMode from './DictationMode'
import OptionsMode from './OptionsMode'
import QuickMemoryMode from './QuickMemoryMode'
import { buildLearnerProfile, mergeLearnerProfileWithBackend } from './learnerProfile'
import SettingsPanel from '../SettingsPanel'
import { PageSkeleton } from '../ui'

// Re-export types for use by parent components
export type { PracticeMode, Word, ProgressData, AppSettings, Chapter }

interface WrongWordsProgressData {
  current_index: number
  correct_count: number
  wrong_count: number
  is_completed: boolean
  queue_words?: string[]
  mode?: PracticeMode
  updatedAt?: string
}

interface ReviewQueueSummary {
  due_count: number
  upcoming_count: number
  returned_count: number
  review_window_days: number
  offset: number
  limit: number
  total_count: number
  has_more: boolean
  next_offset: number | null
}

function readWrongWordsProgress(currentMode?: PracticeMode): WrongWordsProgressData | null {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEYS.WRONG_WORDS_PROGRESS) || '{}') as {
      _last?: WrongWordsProgressData
    }
    const snapshot = stored._last
    if (!snapshot) return null
    if (snapshot.mode && currentMode && snapshot.mode !== currentMode) return null

    return {
      current_index: Math.max(0, Number(snapshot.current_index) || 0),
      correct_count: Math.max(0, Number(snapshot.correct_count) || 0),
      wrong_count: Math.max(0, Number(snapshot.wrong_count) || 0),
      is_completed: Boolean(snapshot.is_completed),
      queue_words: Array.isArray(snapshot.queue_words) ? snapshot.queue_words : undefined,
      mode: snapshot.mode,
      updatedAt: snapshot.updatedAt,
    }
  } catch {
    return null
  }
}

function buildWrongWordsQueue(words: Word[], queueWords?: string[]): number[] | null {
  if (!queueWords?.length) return null

  const indexByWord = new Map<string, number>()
  words.forEach((word, index) => {
    indexByWord.set(word.word.trim().toLowerCase(), index)
  })

  const restoredQueue: number[] = []
  const seen = new Set<number>()

  for (const queuedWord of queueWords) {
    const index = indexByWord.get(queuedWord.trim().toLowerCase())
    if (index == null || seen.has(index)) continue
    restoredQueue.push(index)
    seen.add(index)
  }

  words.forEach((word, index) => {
    if (seen.has(index)) return
    restoredQueue.push(index)
  })

  return restoredQueue.length ? restoredQueue : null
}

function persistWrongWordsProgress(snapshot: WrongWordsProgressData) {
  localStorage.setItem(
    STORAGE_KEYS.WRONG_WORDS_PROGRESS,
    JSON.stringify({
      _last: {
        ...snapshot,
        updatedAt: new Date().toISOString(),
      },
    }),
  )
}

function PracticePage({ user, currentDay, mode, showToast, onModeChange, onDayChange }: PracticePageProps) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const bookId = searchParams.get('book')
  const chapterId = searchParams.get('chapter')
  const errorMode = searchParams.get('mode') === 'errors'
  const reviewMode = searchParams.get('review') === 'due'

  // Core state
  const [vocabulary, setVocabulary] = useState<Word[]>([])
  const [queue, setQueue] = useState<number[]>([])
  const [queueIndex, setQueueIndex] = useState(0)
  const [options, setOptions] = useState<{ definition: string; pos: string }[]>([])
  const [correctIndex, setCorrectIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [previousWord, setPreviousWord] = useState<Word | null>(null)
  const [lastState, setLastState] = useState<LastState | null>(null)
  const [spellingInput, setSpellingInput] = useState('')
  const [spellingResult, setSpellingResult] = useState<'correct' | 'wrong' | null>(null)

  // Radio mode state (initial index only; RadioMode manages its own position)
  const [radioIndex] = useState(0)

  // Pause state
  const [isPaused, setIsPaused] = useState(false)

  // UI panel state
  const [showWordList, setShowWordList] = useState(false)
  const [showPracticeSettings, setShowPracticeSettings] = useState(false)

  // Book chapters for context switcher
  const [bookChapters, setBookChapters] = useState<Chapter[]>([])
  const [currentChapterTitle, setCurrentChapterTitle] = useState('')

  // Track word statuses
  const [wordStatuses, setWordStatuses] = useState<WordStatuses>({})
  const [backendLearnerProfile, setBackendLearnerProfile] = useState<BackendLearnerProfile | null>(null)
  const [reviewOffset, setReviewOffset] = useState(0)
  const [reviewSummary, setReviewSummary] = useState<ReviewQueueSummary | null>(null)

  // Smart mode: current word's test dimension (闊?鎰?褰?
  const [smartDimension, setSmartDimension] = useState<SmartDimension>('meaning')

  // Refs
  const vocabRef = useRef<Word[]>([])
  const queueRef = useRef<number[]>([])
  // sessionStartRef: set when vocabulary is first loaded (not at mount) to avoid counting
  // page-load time or restored-progress counts from a previous session as part of this one.
  const sessionStartRef = useRef<number>(0)
  // Server-assigned session ID from /api/ai/start-session (enables server-side duration).
  const sessionIdRef = useRef<number | null>(null)
  const pendingSessionCancelRef = useRef(false)
  // Session-specific correct/wrong counts always start at 0 and never include restored progress.
  const sessionCorrectRef = useRef(0)
  const sessionWrongRef = useRef(0)
  // Mirrors of correctCount/wrongCount for use in cleanup (avoids stale closure)
  const correctCountRef = useRef(0)
  const wrongCountRef = useRef(0)
  // Prevents double-logging when goNext already logs before navigate
  const sessionLoggedRef = useRef(false)
  const radioInteractionRef = useRef(false)
  const radioWordsStudiedRef = useRef(0)
  // Chapter-level unique answered words, used to compute words_learned against the saved baseline.
  const wordsLearnedBaselineRef = useRef(0)
  const uniqueAnsweredRef = useRef<Set<string>>(new Set())
  // Unique words answered in the current session, used by session logging and stats.
  const sessionUniqueWordsRef = useRef<Set<string>>(new Set())
  // Tracks current mode (keeps cleanup up-to-date when mode prop changes)
  const currentModeRef = useRef(mode)
  /** Mode persisted into log-session and start-session. Error practice uses `errors`. */
  const effectiveSessionModeRef = useRef(errorMode ? 'errors' : (mode ?? 'smart'))
  const errorProgressHydratedRef = useRef(false)

  // Keep refs in sync with state so the unmount cleanup always has current values
  useEffect(() => { correctCountRef.current = correctCount }, [correctCount])
  useEffect(() => { wrongCountRef.current = wrongCount }, [wrongCount])
  useEffect(() => { currentModeRef.current = mode }, [mode])
  useEffect(() => {
    effectiveSessionModeRef.current = errorMode ? 'errors' : (mode ?? 'smart')
  }, [mode, errorMode])

  // Log the session on unmount. This covers complete, pause->exit, navigate away, and browser close.
  useEffect(() => {
    return () => {
      if (sessionLoggedRef.current) return          // already logged by goNext
      const sessionUnique = sessionUniqueWordsRef.current.size
      const isRadio = currentModeRef.current === 'radio'
      const sessionStart = sessionStartRef.current
      const durationSeconds = sessionStart > 0
        ? Math.round((Date.now() - sessionStart) / 1000)
        : 0
      // Radio mode has no answer tracking, so rely on elapsed time and studied words.
      const hasMeaningfulInteraction = isRadio
        ? radioInteractionRef.current && radioWordsStudiedRef.current > 0
        : sessionUnique > 0
      if (!hasMeaningfulInteraction) {
        pendingSessionCancelRef.current = true
        cancelSession(sessionIdRef.current)
        return
      }
      logSession({
        mode: effectiveSessionModeRef.current,
        bookId,
        chapterId,
        wordsStudied: isRadio ? radioWordsStudiedRef.current : sessionUnique,
        correctCount: sessionCorrectRef.current,
        wrongCount: sessionWrongRef.current,
        durationSeconds,
        startedAt: sessionStart,
        sessionId: sessionIdRef.current,
      })
      // Sync smart stats to backend on every exit
      syncSmartStatsToBackend()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // intentionally empty; refs provide current values without re-registering

  // Reactive settings (so RadioMode picks up changes from the toolbar controls)
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = localStorage.getItem('app_settings')
      if (!saved) return DEFAULT_SETTINGS as AppSettings
      return JSON.parse(saved) as AppSettings
    } catch {
      return DEFAULT_SETTINGS as AppSettings
    }
  })

  const handleRadioSettingChange = useCallback((key: keyof RadioQuickSettings, value: string | boolean) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value }
      localStorage.setItem('app_settings', JSON.stringify(next))
      return next
    })
  }, [])

  const radioQuickSettings: RadioQuickSettings = {
    playbackSpeed: String(settings.playbackSpeed ?? '0.8'),
    playbackCount: String(settings.playbackCount ?? '1'),
    loopMode:      Boolean(settings.loopMode ?? false),
    interval:      String(settings.interval ?? '2'),
  }

  // Speech recognition hook
  const {
    isConnected: speechConnected,
    isRecording: speechRecording,
    startRecording: startSpeechRecording,
    stopRecording: stopSpeechRecording,
  } = useSpeechRecognition({
    language: 'en',
    enableVad: true,
    autoStop: true,
    onResult: (text: string) => {
      const cleanText = text.replace(/[.,!?;:'" ]+$/, '')
      setSpellingInput(cleanText.toLowerCase())
      showToast?.('识别成功', 'success')
    },
    onPartial: (text: string) => {
      const cleanText = text.replace(/[.,!?;:'" ]+$/, '')
      setSpellingInput(cleanText.toLowerCase())
    },
    onError: (error: string) => {
      showToast?.(`识别失败: ${error}`, 'error')
    },
  })

  // Fetch book chapters
  useEffect(() => {
    if (!bookId) return
    fetch(buildApiUrl(`/api/books/${bookId}/chapters`))
      .then(r => r.json())
      .then((d: { chapters?: Chapter[] }) => {
        const chs = d.chapters || []
        setBookChapters(chs)
        const current = chs.find(c => String(c.id) === String(chapterId)) || chs[0]
        if (current) setCurrentChapterTitle(current.title)
      })
      .catch(() => {})
  }, [bookId])

  // Update chapter title
  useEffect(() => {
    if (!bookId || !bookChapters.length) return
    const current = bookChapters.find(c => String(c.id) === String(chapterId)) || bookChapters[0]
    if (current) setCurrentChapterTitle(current.title)
  }, [chapterId, bookChapters])

  useEffect(() => {
    if (!reviewMode || mode !== 'quickmemory') {
      setReviewOffset(0)
      setReviewSummary(null)
      return
    }

    setReviewOffset(0)
  }, [mode, reviewMode, settings.reviewInterval, settings.reviewLimit])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const data = await apiFetch<unknown>('/api/ai/learner-profile')
        const parsed = safeParse(LearnerProfileSchema, data)

        if (!cancelled) {
          setBackendLearnerProfile(parsed.success ? parsed.data : null)
        }
      } catch {
        if (!cancelled) {
          setBackendLearnerProfile(null)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [user?.id, currentDay])

  // Start the server-side session timer once vocabulary is actually ready.
  // Resets client-side fallback timer and session-specific answer counters.
  const beginSession = () => {
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
      bookId,
      chapterId,
    }).then(id => {
      sessionIdRef.current = id
      if (pendingSessionCancelRef.current && id) {
        cancelSession(id)
      }
    }).catch(() => {})
  }

  const computeChapterWordsLearned = (cap: number) => {
    if (!chapterId || !cap) return wordsLearnedBaselineRef.current
    return Math.min(cap, Math.max(wordsLearnedBaselineRef.current, uniqueAnsweredRef.current.size))
  }

  const registerAnsweredWord = (word: string) => {
    const key = word.trim().toLowerCase()
    if (!key) return
    sessionUniqueWordsRef.current.add(key)
    if (chapterId) uniqueAnsweredRef.current.add(key)
  }

  const markRadioSessionInteraction = useCallback(() => {
    radioInteractionRef.current = true
  }, [])

  const handleRadioProgressChange = useCallback((wordsStudied: number) => {
    radioWordsStudiedRef.current = Math.max(radioWordsStudiedRef.current, wordsStudied)
  }, [])

  // Restore progress helper
  const restoreProgress = (data: ProgressData, vocabLen: number) => {
    const cap = vocabLen || 0
    // If the chapter was already completed, restart from the beginning so the
    // user can practice again rather than immediately seeing the "done" screen.
    if (data.is_completed) {
      setQueueIndex(0); setCorrectCount(0); setWrongCount(0)
      setPreviousWord(null); setLastState(null); setWordStatuses({})
      if (chapterId) {
        wordsLearnedBaselineRef.current = Math.min(data.words_learned ?? cap, cap)
        uniqueAnsweredRef.current = new Set()
      } else {
        wordsLearnedBaselineRef.current = 0
        uniqueAnsweredRef.current = new Set()
      }
      return
    }
    // Cap to queue.length (not queue.length - 1) to allow the completion screen
    // to show naturally when current_index was saved as queueIndex + 1 for the
    // last word.
    setQueueIndex(Math.min(data.current_index || 0, queueRef.current.length))
    setCorrectCount(data.correct_count || 0)
    setWrongCount(data.wrong_count || 0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    if (chapterId) {
      wordsLearnedBaselineRef.current = Math.min(data.words_learned ?? 0, cap)
      uniqueAnsweredRef.current = new Set(data.answered_words ?? [])
    } else {
      wordsLearnedBaselineRef.current = 0
      uniqueAnsweredRef.current = new Set()
    }
  }

  // Load vocabulary data
  useEffect(() => {
    let cancelled = false
    errorProgressHydratedRef.current = false

    // Hydrate smart stats from backend if localStorage is empty (handles cleared storage)
    if (Object.keys(loadSmartStats()).length === 0) {
      loadSmartStatsFromBackend()
    }

    if (reviewMode && mode === 'quickmemory') {
      void (async () => {
        try {
          const reviewWindowDays = Math.max(1, parseInt(String(settings.reviewInterval ?? '1'), 10) || 1)
          const reviewLimit = Math.max(1, parseInt(String(settings.reviewLimit ?? '20'), 10) || 20)
          const data = await apiFetch<{ words?: Word[]; summary?: ReviewQueueSummary }>(
            `/api/ai/quick-memory/review-queue?limit=${reviewLimit}&within_days=${reviewWindowDays}&offset=${reviewOffset}`,
          )
          if (cancelled) return

          const words = data.words || []
          const q = Array.from({ length: words.length }, (_, i) => i)

          setVocabulary(words)
          vocabRef.current = words
          setQueue(q)
          queueRef.current = q
          setQueueIndex(0)
          setCorrectCount(0)
          setWrongCount(0)
          setPreviousWord(null)
          setLastState(null)
          setWordStatuses({})
          setReviewSummary(data.summary ?? null)
          setCurrentChapterTitle('艾宾浩斯复习')
          beginSession()
        } catch {
          if (!cancelled) showToast?.('加载复习队列失败', 'error')
        }
      })()

      return () => {
        cancelled = true
      }
    }

    // reviewMode is set from the URL; mode='quickmemory' is applied via a
    // custom event in App.tsx and may not yet be reflected on the first render.
    // Guard here so we don't fall through to day/chapter loading and
    // potentially navigate('/plan') while the mode update is in flight.
    if (reviewMode) return

    if (errorMode) {
      void (async () => {
        try {
          const wrongWords = await loadWrongWords({
            user,
            fetchRemote: () => apiFetch<{ words?: Word[] }>('/api/ai/wrong-words'),
          })
          if (cancelled) return

          const saved: Word[] = wrongWords.map(word => ({
            word: word.word,
            phonetic: word.phonetic,
            pos: word.pos,
            definition: word.definition,
          }))
          setVocabulary(saved)
          vocabRef.current = saved
          const indices = Array.from({ length: saved.length }, (_, i) => i)
          const fallbackQueue = settings.shuffle !== false ? shuffleArray(indices) : indices
          const savedProgress = readWrongWordsProgress(mode)
          const q = savedProgress?.is_completed
            ? fallbackQueue
            : buildWrongWordsQueue(saved, savedProgress?.queue_words) ?? fallbackQueue
          const maxIndex = Math.max(q.length - 1, 0)

          setQueue(q)
          queueRef.current = q
          setQueueIndex(savedProgress?.is_completed ? 0 : Math.min(savedProgress?.current_index ?? 0, maxIndex))
          setCorrectCount(savedProgress?.is_completed ? 0 : (savedProgress?.correct_count ?? 0))
          setWrongCount(savedProgress?.is_completed ? 0 : (savedProgress?.wrong_count ?? 0))
          setPreviousWord(null)
          setLastState(null)
          setWordStatuses({})
          errorProgressHydratedRef.current = true
          beginSession()
        } catch {
          if (!cancelled) showToast?.('加载错词失败', 'error')
        }
      })()

      return () => {
        cancelled = true
      }
    }

    // Helper: build queue based on mode (smart = sorted by weakness, others = shuffle)
    const buildQueue = (words: Word[]) => {
      const indices = Array.from({ length: words.length }, (_, i) => i)
      if (mode === 'smart') return buildSmartQueue(words.map(w => w.word), loadSmartStats())
      return settings.shuffle !== false ? shuffleArray(indices) : indices
    }

    if (bookId) {
      if (chapterId) {
        fetch(buildApiUrl(`/api/books/${bookId}/chapters/${chapterId}`))
          .then(res => res.json())
          .then(async (data: { words?: Word[] }) => {
            const words = data.words || []
            vocabRef.current = words
            // Resolve progress first so we can restore the saved queue order.
            let progress: ProgressData | null = null
            const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
            const key = `${bookId}_${chapterId}`
            if (saved[key]) {
              progress = saved[key]
            } else {
              try {
                const pd = await apiFetch<{ chapter_progress?: Record<string, ProgressData> }>(
                  `/api/books/${bookId}/chapters/progress`
                )
                progress = pd.chapter_progress?.[String(chapterId)] ?? null
              } catch { /* not logged in or network error; start fresh */ }
            }
            // Restore saved queue order when available so a shuffle reload does
            // not invalidate the stored current_index.
            const q = buildWrongWordsQueue(words, progress?.queue_words) ?? buildQueue(words)
            queueRef.current = q
            // Apply all state in one block for a single render.
            setVocabulary(words)
            setQueue(q)
            if (progress) restoreProgress(progress, words.length)
            else {
              setQueueIndex(0); setCorrectCount(0); setWrongCount(0)
              wordsLearnedBaselineRef.current = 0
              uniqueAnsweredRef.current = new Set()
            }
            beginSession()
          })
          .catch(() => showToast?.('加载章节词汇失败', 'error'))
        return
      }

      fetch(buildApiUrl(`/api/books/${bookId}/words?per_page=100`))
        .then(res => res.json())
        .then(async (data: { words?: Word[] }) => {
          const words = data.words || []
          vocabRef.current = words
          let progress: ProgressData | null = null
          const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('book_progress') || '{}')
          if (saved[bookId]) {
            progress = saved[bookId]
          } else {
            try {
              const pd = await apiFetch<{ progress?: ProgressData }>(`/api/books/progress/${bookId}`)
              progress = pd.progress ?? null
            } catch { /* not logged in or network error; start fresh */ }
          }
          const q = buildWrongWordsQueue(words, progress?.queue_words) ?? buildQueue(words)
          queueRef.current = q
          setVocabulary(words)
          setQueue(q)
          if (progress) restoreProgress(progress, words.length)
          else {
            setQueueIndex(0); setCorrectCount(0); setWrongCount(0)
            wordsLearnedBaselineRef.current = 0
            uniqueAnsweredRef.current = new Set()
          }
          beginSession()
        })
        .catch(() => showToast?.('加载词书失败', 'error'))
      return
    }

    if (!currentDay) { navigate('/plan'); return }
    fetch(buildApiUrl(`/api/vocabulary/day/${currentDay}`))
      .then(res => res.json())
      .then(async (data: { vocabulary?: Word[]; words?: Word[] }) => {
        const words = data.vocabulary || data.words || []
        vocabRef.current = words
        let progress: ProgressData | null = null
        const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('day_progress') || '{}')
        if (saved[String(currentDay)]) {
          progress = saved[String(currentDay)]
        } else {
          try {
            const pd = await apiFetch<{ progress?: Array<{ day: number; current_index: number; correct_count: number; wrong_count: number }> }>('/api/progress')
            const entry = pd.progress?.find(p => p.day === currentDay)
            progress = entry ?? null
          } catch { /* not logged in or network error; start fresh */ }
        }
        const q = buildWrongWordsQueue(words, progress?.queue_words) ?? buildQueue(words)
        queueRef.current = q
        setVocabulary(words)
        setQueue(q)
        if (progress) restoreProgress(progress, words.length)
        else {
          setQueueIndex(0); setCorrectCount(0); setWrongCount(0)
          wordsLearnedBaselineRef.current = 0
          uniqueAnsweredRef.current = new Set()
        }
        beginSession()
      })
      .catch(() => showToast?.('加载词汇失败', 'error'))
    return () => {
      cancelled = true
    }
  }, [bookId, chapterId, currentDay, errorMode, mode, reviewMode, reviewOffset, settings.reviewInterval, settings.reviewLimit, user])

  // Persist wrong-words progress when the queue position or word list changes.
  // Deliberately excludes correctCount/wrongCount from deps: those are saved by
  // saveProgress() on every answer (with the correct queueIndex+1 offset).
  // Including them here would re-run with the stale queueIndex right after an
  // answer, overwriting is_completed:true with is_completed:false for the last
  // word before goNext() has a chance to navigate away.
  useEffect(() => {
    if (!errorMode || !errorProgressHydratedRef.current || !vocabulary.length) return

    const queueWords = queue
      .map(index => vocabulary[index]?.word)
      .filter((word): word is string => Boolean(word))

    persistWrongWordsProgress({
      current_index: Math.min(queueIndex, Math.max(queue.length - 1, 0)),
      correct_count: correctCountRef.current,
      wrong_count: wrongCountRef.current,
      is_completed: queue.length > 0 && queueIndex >= queue.length,
      queue_words: queueWords,
      mode,
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [errorMode, mode, queue, queueIndex, vocabulary])

  const currentWord: Word | undefined = vocabulary[queue[queueIndex]]

  // Update options when word changes
  useEffect(() => {
    if (!currentWord || !vocabulary.length) return

    const smartStats = loadSmartStats()
    // For smart mode: choose which dimension to test for this word
    let subMode: SmartDimension = smartDimension
    if (mode === 'smart') {
      subMode = chooseSmartDimension(currentWord.word, smartStats)
      setSmartDimension(subMode)
    }

    const wrongWords = readWrongWordsFromStorage()
    const localLearnerProfile = buildLearnerProfile({
      vocabulary,
      currentWord,
      mode,
      smartDimension: subMode,
      smartStats,
      wrongWords,
    })
    const learnerProfile = mergeLearnerProfileWithBackend({
      localProfile: localLearnerProfile,
      backendProfile: backendLearnerProfile,
      vocabulary,
      wrongWords,
    })

    // Generate options for multiple-choice modes (not needed for dictation sub-mode)
    const needsOptions = mode === 'listening' || mode === 'meaning' ||
      (mode === 'smart' && subMode !== 'dictation')
    const isListeningMode = mode === 'listening' || (mode === 'smart' && subMode === 'listening')

    if (needsOptions) {
      const localPool = [currentWord, ...vocabulary, ...learnerProfile.priorityWords]
      // Set immediate local options (user is still listening to audio)
      const { options: opts, correctIndex: ci } = generateOptions(currentWord, localPool, {
        mode: isListeningMode ? 'listening' : subMode,
        priorityWords: learnerProfile.priorityWords,
      })
      setOptions(opts); setCorrectIndex(ci)

      // For listening mode: replace with global-pool confusable distractors
      if (isListeningMode) {
        const word = currentWord
        const params = new URLSearchParams({ word: word.word, n: '10' })
        if (word.phonetic) params.set('phonetic', word.phonetic)
        if (word.pos)      params.set('pos', word.pos)
        apiFetch<{ words: Word[] }>(`/api/ai/similar-words?${params}`)
          .then(data => {
            if (!data?.words?.length) return
            // Pool = similar words from global vocabulary (excluding the correct word)
            const pool = data.words.filter(w => w.definition !== word.definition)
            if (pool.length < 3) return  // not enough distractors, keep local ones
            const { options: newOpts, correctIndex: newCi } = generateOptions(
              word,
              [word, ...pool, ...learnerProfile.priorityWords],
              {
                mode: 'listening',
                priorityWords: learnerProfile.priorityWords,
              },
            )
            setOptions(newOpts); setCorrectIndex(newCi)
          })
          .catch(() => { /* keep local options on network error */ })
      }
    }

    setSelectedAnswer(null); setShowResult(false); setSpellingInput(''); setSpellingResult(null)

    // Auto-play audio for audio-first modes
    const shouldAutoPlay = mode === 'listening' || mode === 'dictation' ||
      (mode === 'smart' && (subMode === 'listening' || subMode === 'dictation'))
    if (!shouldAutoPlay) return

    const isDictation = mode === 'dictation' || (mode === 'smart' && subMode === 'dictation')
    const exampleSentence = isDictation ? currentWord.examples?.[0]?.en : undefined
    if (exampleSentence) return

    const timerId = window.setTimeout(() => {
      playWordUtil(currentWord.word, settings)
    }, 280)

    return () => {
      window.clearTimeout(timerId)
      stopAudioUtil()
    }
  }, [queueIndex, currentWord?.word, mode, smartDimension, settings.playbackSpeed, settings.volume, backendLearnerProfile, vocabulary])

  // Log learning context to AI chat whenever state changes
  useEffect(() => {
    const accuracy = correctCount + wrongCount > 0
      ? Math.round((correctCount / (correctCount + wrongCount)) * 100)
      : undefined
    const wrongWords = readWrongWordsFromStorage()
    const localLearnerProfile = buildLearnerProfile({
      vocabulary,
      currentWord,
      mode,
      smartDimension,
      smartStats: loadSmartStats(),
      wrongWords,
    })
    const learnerProfile = mergeLearnerProfileWithBackend({
      localProfile: localLearnerProfile,
      backendProfile: backendLearnerProfile,
      vocabulary,
      wrongWords,
    })
    if (!currentWord) {
      // Session just completed; record final state so AI sees the full round.
      if (vocabulary.length > 0) {
        setGlobalLearningContext({
          currentWord: undefined,
          sessionCompleted: true,
          sessionProgress: queue.length,
          totalWords: vocabulary.length,
          wordsCompleted: correctCount + wrongCount,
          sessionAccuracy: accuracy,
          practiceMode: mode as string,
          mode: errorMode ? 'review' : 'learning',
          currentBook: bookId ?? undefined,
          currentChapter: chapterId ?? undefined,
          currentChapterTitle: currentChapterTitle || undefined,
          currentFocusDimension: learnerProfile.activeDimension,
          weakestDimension: learnerProfile.weakestDimension,
          weakDimensionOrder: learnerProfile.weakDimensionOrder,
          weakFocusWords: learnerProfile.weakFocusWords,
          recentWrongWords: learnerProfile.recentWrongWords,
          trapStrategy: learnerProfile.trapStrategy,
          priorityDistractorWords: learnerProfile.priorityWords.map(word => word.word),
        })
      }
      return
    }
    setGlobalLearningContext({
      currentWord: currentWord.word,
      currentPhonetic: currentWord.phonetic,
      currentPos: currentWord.pos,
      currentDefinition: currentWord.definition,
      practiceMode: mode as string,
      mode: errorMode ? 'review' : 'learning',
      sessionProgress: queueIndex + 1,
      totalWords: vocabulary.length,
      wordsCompleted: correctCount + wrongCount,
      sessionAccuracy: accuracy,
      sessionCompleted: false,
      currentBook: bookId ?? undefined,
      currentChapter: chapterId ?? undefined,
      currentChapterTitle: currentChapterTitle || undefined,
      currentFocusDimension: learnerProfile.activeDimension,
      weakestDimension: learnerProfile.weakestDimension,
      weakDimensionOrder: learnerProfile.weakDimensionOrder,
      weakFocusWords: learnerProfile.weakFocusWords,
      recentWrongWords: learnerProfile.recentWrongWords,
      trapStrategy: learnerProfile.trapStrategy,
      priorityDistractorWords: learnerProfile.priorityWords.map(word => word.word),
    })
  }, [currentWord, mode, queueIndex, correctCount, wrongCount, errorMode, vocabulary, smartDimension, bookId, chapterId, currentChapterTitle, backendLearnerProfile])

  // Save progress
  const saveProgress = useCallback((correct: number, wrong: number) => {
    if (errorMode) {
      const queueWords = queue
        .map(index => vocabulary[index]?.word)
        .filter((word): word is string => Boolean(word))
      persistWrongWordsProgress({
        current_index: Math.min(queueIndex + 1, Math.max(queue.length - 1, 0)),
        correct_count: correct,
        wrong_count: wrong,
        is_completed: queue.length > 0 && queueIndex + 1 >= queue.length,
        queue_words: queueWords,
        mode,
      })
      return
    }

    const chapterDone = Boolean(
      chapterId
      && vocabulary.length > 0
      && uniqueAnsweredRef.current.size >= vocabulary.length
      && queueIndex + 1 >= queue.length,
    )
    // Save the next word to answer (queueIndex + 1) so that on resume the user
    // picks up exactly where they left off rather than re-answering the last word.
    const nextIndex = queueIndex + 1
    const progressData: ProgressData = {
      current_index: nextIndex,
      correct_count: correct,
      wrong_count: wrong,
      is_completed: chapterId ? chapterDone : (correct + wrong >= vocabulary.length),
    }
    // Queue order persisted locally so a shuffle reload doesn't scramble the position.
    const queueWords = queue
      .map(index => vocabulary[index]?.word)
      .filter((w): w is string => Boolean(w))

    if (bookId) {
      const bookProgress: Record<string, ProgressData> = JSON.parse(localStorage.getItem('book_progress') || '{}')
      bookProgress[bookId] = { ...progressData, queue_words: queueWords, updatedAt: new Date().toISOString() }
      localStorage.setItem('book_progress', JSON.stringify(bookProgress))

      // queue_words is local-only; strip it before sending to the backend.
      apiFetch('/api/books/progress', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId, ...progressData })
      }).catch(() => showToast?.('进度保存失败，请检查网络连接', 'error'))

      if (chapterId) {
        const cap = vocabulary.length
        const wl = computeChapterWordsLearned(cap)
        const answeredWords = Array.from(uniqueAnsweredRef.current)
        const chapterProgress: Record<string, ProgressData> = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
        chapterProgress[`${bookId}_${chapterId}`] = {
          ...progressData,
          words_learned: wl,
          answered_words: answeredWords,
          queue_words: queueWords,
          updatedAt: new Date().toISOString(),
        }
        localStorage.setItem('chapter_progress', JSON.stringify(chapterProgress))
        apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
          method: 'POST',
          body: JSON.stringify({
            ...progressData,
            words_learned: wl,
            answered_words: answeredWords,
          }),
        }).catch(() => {})

        // Save per-mode accuracy to the backend. Each mode is stored independently.
        if (mode && correct + wrong > 0) {
          apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
            method: 'POST',
            body: JSON.stringify({
              mode,
              correct_count: correct,
              wrong_count: wrong,
              is_completed: progressData.is_completed ?? false,
            }),
          }).catch(() => {})
        }
      }
    } else {
      const dayProgress: Record<string, ProgressData> = JSON.parse(localStorage.getItem('day_progress') || '{}')
      dayProgress[String(currentDay)] = {
        ...progressData,
        is_completed: correct + wrong >= vocabulary.length,
        queue_words: queueWords,
        updatedAt: new Date().toISOString(),
      }
      localStorage.setItem('day_progress', JSON.stringify(dayProgress))

      apiFetch('/api/progress', {
        method: 'POST',
        body: JSON.stringify({ day: currentDay, ...progressData })
      }).catch(() => {})
    }
  }, [bookId, chapterId, currentDay, errorMode, mode, queue, queue.length, queueIndex, vocabulary])

  const saveWrongWord = (word: Word) => {
    // Update localStorage list (for error-mode practice queue)
    const existing = addWrongWordToList(
      JSON.parse(localStorage.getItem('wrong_words') || '[]'),
      word,
    )
    writeWrongWordsToStorage(existing)
    // Always sync wrong words to the backend and include dimension stats.
    const ws = loadSmartStats()[word.word]
    apiFetch('/api/ai/wrong-words/sync', {
      method: 'POST',
      body: JSON.stringify({
        words: [{
          word: word.word,
          phonetic: word.phonetic,
          pos: word.pos,
          definition: word.definition,
          listeningCorrect: ws?.listening.correct ?? 0,
          listeningWrong:   ws?.listening.wrong   ?? 0,
          meaningCorrect:   ws?.meaning.correct   ?? 0,
          meaningWrong:     ws?.meaning.wrong     ?? 0,
          dictationCorrect: ws?.dictation.correct ?? 0,
          dictationWrong:   ws?.dictation.wrong   ?? 0,
        }]
        }),
      }).catch(() => {})
  }

  const goNext = (wasCorrect: boolean) => {
    setLastState({ qi: queueIndex, cc: correctCount, wc: wrongCount, prevWord: previousWord })
    setPreviousWord(currentWord ?? null)
    if (!wasCorrect && settings.repeatWrong !== false) {
      setQueue(prev => { const c = [...prev]; c.push(queue[queueIndex]); return c })
    }
    if (queueIndex + 1 >= queue.length) {
      // Session complete; mark it so the unmount cleanup does not double-log.
      const finalSessionCorrect = wasCorrect ? sessionCorrectRef.current + 1 : sessionCorrectRef.current
      const finalSessionWrong = wasCorrect ? sessionWrongRef.current : sessionWrongRef.current + 1
      const sessionStart = sessionStartRef.current
      sessionLoggedRef.current = true
      logSession({
        mode: effectiveSessionModeRef.current,
        bookId,
        chapterId,
        wordsStudied: sessionUniqueWordsRef.current.size,
        correctCount: finalSessionCorrect,
        wrongCount: finalSessionWrong,
        durationSeconds: sessionStart > 0 ? Math.round((Date.now() - sessionStart) / 1000) : 0,
        startedAt: sessionStart,
        sessionId: sessionIdRef.current,
      })
      // Sync smart stats to backend at session end
      syncSmartStatsToBackend()
      navigate('/plan')
    } else {
      setQueueIndex(prev => prev + 1)
    }
  }

  const goBack = () => {
    if (!lastState) return
    setQueueIndex(lastState.qi); setCorrectCount(lastState.cc); setWrongCount(lastState.wc)
    setPreviousWord(lastState.prevWord); setLastState(null)
    setSelectedAnswer(null); setShowResult(false); setSpellingInput(''); setSpellingResult(null)
  }

  const handleOptionSelect = (idx: number) => {
    if (showResult) return
    setSelectedAnswer(idx); setShowResult(true)
    const isCorrect = idx === correctIndex
    const nc = isCorrect ? correctCount + 1 : correctCount
    const nw = isCorrect ? wrongCount : wrongCount + 1
    setCorrectCount(nc); setWrongCount(nw)
    if (isCorrect) { sessionCorrectRef.current++ } else { sessionWrongRef.current++ }
    if (currentWord) registerAnsweredWord(currentWord.word)
    saveProgress(nc, nw)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: isCorrect ? 'correct' : 'wrong' }))
    // Record per-dimension stats first, then sync wrong word (so dim stats are included)
    if (currentWord) {
      const dim: SmartDimension = mode === 'smart' ? smartDimension
        : mode === 'listening' ? 'listening' : 'meaning'
      recordWordResult(currentWord.word, dim, isCorrect)
      if (!isCorrect) saveWrongWord(currentWord)
    }
    recordModeAnswer(mode ?? 'smart', isCorrect)
    setTimeout(() => goNext(isCorrect), 1200)
  }

  const handleSpellingSubmit = () => {
    if (spellingResult || !currentWord) return
    const isCorrect = spellingInput.trim().toLowerCase() === currentWord.word.toLowerCase()
    setSpellingResult(isCorrect ? 'correct' : 'wrong')
    const nc = isCorrect ? correctCount + 1 : correctCount
    const nw = isCorrect ? wrongCount : wrongCount + 1
    setCorrectCount(nc); setWrongCount(nw)
    if (isCorrect) { sessionCorrectRef.current++ } else { sessionWrongRef.current++ }
    registerAnsweredWord(currentWord.word)
    saveProgress(nc, nw)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: isCorrect ? 'correct' : 'wrong' }))
    // Record dictation stats first, then sync wrong word (so dim stats are included)
    recordWordResult(currentWord.word, 'dictation', isCorrect)
    if (!isCorrect) saveWrongWord(currentWord)
    recordModeAnswer(mode ?? 'dictation', isCorrect)
    setTimeout(() => goNext(isCorrect), 1500)
  }

  const handleSkip = () => {
    if (!currentWord) return
    saveWrongWord(currentWord)
    registerAnsweredWord(currentWord.word)
    const nw = wrongCount + 1
    setWrongCount(nw); saveProgress(correctCount, nw)
    sessionWrongRef.current++
    recordModeAnswer(mode ?? 'smart', false)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: 'wrong' }))
    goNext(false)
  }

  const startRecording = async () => {
    if (!speechConnected) {
      showToast?.('语音服务未连接，请稍后重试', 'error')
      return
    }
    showToast?.('请说出单词...', 'info')
    await startSpeechRecording()
  }

  const stopRecording = () => {
    stopSpeechRecording()
  }

  const playWord = (word: string) => {
    playWordUtil(word, settings)
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (showResult || spellingResult) return
      if (['listening', 'meaning', 'smart'].includes(mode as string)) {
        if (e.key >= '1' && e.key <= '4') { const idx = parseInt(e.key) - 1; if (idx < options.length) handleOptionSelect(idx) }
        if (e.key === '5') handleSkip()
        if (e.key === 'Tab') { e.preventDefault(); playWord(currentWord?.word ?? '') }
      }
      if (e.key === 'Escape') setIsPaused(p => !p)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [showResult, spellingResult, options, mode, queueIndex])

  const handleContinueReview = useCallback(() => {
    const nextOffset = reviewSummary?.next_offset
    if (!reviewSummary?.has_more || nextOffset == null) return

    setVocabulary([])
    vocabRef.current = []
    setQueue([])
    queueRef.current = []
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    setReviewOffset(nextOffset)
  }, [reviewSummary])

  // Loading state — but if we're in review mode and the session has started
  // (beginSession sets sessionStartRef) with an empty result, show "no due
  // words" instead of an infinite skeleton.
  if (!vocabulary.length) {
    if (reviewMode && mode === 'quickmemory' && sessionStartRef.current > 0) {
      return (
        <div className="practice-session-layout">
          <div className="practice-complete">
            <div className="complete-emoji" aria-hidden="true">✓</div>
            <h2>暂无待复习的单词</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              目前没有到期需要复习的单词，继续学习新词后再来！
            </p>
            <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
          </div>
        </div>
      )
    }
    return (
      <div className="practice-session-layout">
        <PageSkeleton variant="practice" />
      </div>
    )
  }

  // Completed state fallback. Normally goNext navigates away before this renders.
  if (!currentWord) {
    const reviewRemaining = reviewSummary?.has_more
      ? (reviewSummary.total_count - reviewSummary.offset - reviewSummary.returned_count)
      : 0
    return (
      <div className="practice-session-layout">
        <div className="practice-complete">
        <div className="complete-emoji" aria-hidden="true">Completed</div>
        <h2>
          {errorMode ? '错词复习完成'
            : reviewMode ? '本批复习完成'
            : bookId ? '本章完成'
            : `Day ${currentDay} 完成`}
        </h2>
        <div className="complete-stats-row">
          <span className="stat-correct">正确 {correctCount}</span>
          <span className="stat-wrong">错误 {wrongCount}</span>
        </div>
        {reviewMode && reviewSummary?.has_more && (
          <button className="complete-btn" onClick={handleContinueReview}>
            继续复习{reviewRemaining > 0 ? `（还有 ${reviewRemaining} 个）` : ''}
          </button>
        )}
        <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
        </div>
      </div>
    )
  }

  const progress = queueIndex / Math.max(vocabulary.length, 1)

  // Pause overlay shared across all render branches.
  const pauseOverlay = isPaused && (
    <div className="practice-pause-overlay">
      <div className="practice-pause-card">
        <div className="practice-pause-icon-wrap">
          <svg viewBox="0 0 24 24" fill="currentColor" width="34" height="34">
            <rect x="5" y="3" width="4" height="18" rx="1.5"/>
            <rect x="15" y="3" width="4" height="18" rx="1.5"/>
          </svg>
        </div>
        <h2 className="practice-pause-title">练习已暂停</h2>
        {mode !== 'radio' && (
          <div className="practice-pause-stats">
            <span className="practice-pause-stat">
              {mode === 'quickmemory'
                ? <>共 <strong>{queue.length}</strong> 个单词</>
                : <>第 <strong>{queueIndex}</strong> / {queue.length} 个单词</>
              }
            </span>
            {mode !== 'quickmemory' && (correctCount > 0 || wrongCount > 0) && (
              <span className="practice-pause-sub">
                <span className="practice-pause-correct">正确 {correctCount}</span>
                <span className="practice-pause-wrong">错误 {wrongCount}</span>
              </span>
            )}
          </div>
        )}
        <p className="practice-pause-hint">
          进度已自动保存。退出后再次回到本章节，仍可从这里继续。
        </p>
        <div className="practice-pause-actions">
          <button className="practice-pause-resume" onClick={() => setIsPaused(false)}>
            继续练习
          </button>
          <button className="practice-pause-exit" onClick={() => navigate('/plan')}>
            退出到主页
          </button>
        </div>
      </div>
    </div>
  )

  // Render different modes
  if (mode === 'radio') {
    return (
      <div className="practice-session-layout">
        <PracticeControlBar
          mode={mode}
          currentDay={currentDay}
          bookId={bookId}
          chapterId={chapterId}
          errorMode={errorMode}
          vocabularyLength={vocabulary.length}
          currentChapterTitle={currentChapterTitle}
          bookChapters={bookChapters}
          showWordList={showWordList}
          showPracticeSettings={showPracticeSettings}
          onWordListToggle={() => setShowWordList(v => !v)}
          onSettingsToggle={() => setShowPracticeSettings(v => !v)}
          onModeChange={(m) => onModeChange?.(m)}
          onDayChange={(d) => onDayChange?.(d)}
          onNavigate={navigate}
          onPause={() => setIsPaused(true)}
          radioQuickSettings={radioQuickSettings}
          onRadioSettingChange={handleRadioSettingChange}
        />
        <WordListPanel
          show={showWordList}
          vocabulary={vocabulary}
          queue={queue}
          queueIndex={radioIndex}
          wordStatuses={wordStatuses}
          onClose={() => setShowWordList(false)}
        />
        {showPracticeSettings && (
          <SettingsPanel showSettings={showPracticeSettings} onClose={() => setShowPracticeSettings(false)} />
        )}
        <RadioMode
          vocabulary={vocabulary}
          queue={queue}
          radioIndex={radioIndex}
          showSettings={false}
          settings={settings}
          onRadioSkipPrev={() => {}}
          onRadioSkipNext={() => {}}
          onRadioPause={() => {}}
          onRadioResume={() => {}}
          onRadioRestart={() => {}}
          onRadioStop={() => {}}
          onNavigate={navigate}
          onCloseSettings={() => setShowPracticeSettings(false)}
          onModeChange={(m) => onModeChange?.(m as PracticeMode)}
          onSessionInteraction={markRadioSessionInteraction}
          onProgressChange={handleRadioProgressChange}
        />
        {pauseOverlay}
      </div>
    )
  }

  if (mode === 'quickmemory') {
    return (
      <div className="practice-session-layout">
        <PracticeControlBar
          mode={mode}
          currentDay={currentDay}
          bookId={bookId}
          chapterId={chapterId}
          errorMode={errorMode}
          vocabularyLength={vocabulary.length}
          currentChapterTitle={currentChapterTitle}
          bookChapters={bookChapters}
          showWordList={showWordList}
          showPracticeSettings={showPracticeSettings}
          onWordListToggle={() => setShowWordList(v => !v)}
          onSettingsToggle={() => setShowPracticeSettings(v => !v)}
          onModeChange={(m) => onModeChange?.(m)}
          onDayChange={(d) => onDayChange?.(d)}
          onNavigate={navigate}
          onPause={() => setIsPaused(true)}
        />
        {showPracticeSettings && (
          <SettingsPanel showSettings={showPracticeSettings} onClose={() => setShowPracticeSettings(false)} />
        )}
        <QuickMemoryMode
          key={`quickmemory-${bookId ?? 'day'}-${chapterId ?? currentDay ?? 'all'}-${errorMode ? 'errors' : 'normal'}-${reviewMode ? `review-${reviewOffset}` : 'default'}`}
          vocabulary={vocabulary}
          queue={queue}
          settings={settings}
          bookId={bookId}
          chapterId={chapterId}
          bookChapters={bookChapters}
          reviewHasMore={reviewMode ? Boolean(reviewSummary?.has_more) : false}
          onContinueReview={reviewMode ? handleContinueReview : undefined}
          onModeChange={(m) => onModeChange?.(m as PracticeMode)}
          onNavigate={navigate}
          onWrongWord={saveWrongWord}
        />
        {pauseOverlay}
      </div>
    )
  }

  if (mode === 'dictation') {
    return (
      <div className="practice-session-layout">
        <PracticeControlBar
          mode={mode}
          currentDay={currentDay}
          bookId={bookId}
          chapterId={chapterId}
          errorMode={errorMode}
          vocabularyLength={vocabulary.length}
          currentChapterTitle={currentChapterTitle}
          bookChapters={bookChapters}
          showWordList={showWordList}
          showPracticeSettings={showPracticeSettings}
          onWordListToggle={() => setShowWordList(v => !v)}
          onSettingsToggle={() => setShowPracticeSettings(v => !v)}
          onModeChange={(m) => onModeChange?.(m)}
          onDayChange={(d) => onDayChange?.(d)}
          onNavigate={navigate}
          onPause={() => setIsPaused(true)}
        />
        <WordListPanel
          show={showWordList}
          vocabulary={vocabulary}
          queue={queue}
          queueIndex={queueIndex}
          wordStatuses={wordStatuses}
          onClose={() => setShowWordList(false)}
        />
        {showPracticeSettings && (
          <SettingsPanel showSettings={showPracticeSettings} onClose={() => setShowPracticeSettings(false)} />
        )}
        <DictationMode
          currentWord={currentWord}
          spellingInput={spellingInput}
          spellingResult={spellingResult}
          speechConnected={speechConnected}
          speechRecording={speechRecording}
          settings={settings}
          progressValue={progress}
          total={vocabulary.length}
          previousWord={previousWord}
          lastState={lastState}
          onSpellingInputChange={setSpellingInput}
          onSpellingSubmit={handleSpellingSubmit}
          onSkip={handleSkip}
          onGoBack={goBack}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          onPlayWord={playWord}
        />
        {pauseOverlay}
      </div>
    )
  }

  // Listening / Meaning / Smart modes
  return (
    <div className="practice-session-layout">
      <PracticeControlBar
        mode={mode}
        currentDay={currentDay}
        bookId={bookId}
        chapterId={chapterId}
        errorMode={errorMode}
        vocabularyLength={vocabulary.length}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        showPracticeSettings={showPracticeSettings}
        onWordListToggle={() => setShowWordList(v => !v)}
        onSettingsToggle={() => setShowPracticeSettings(v => !v)}
        onModeChange={(m) => onModeChange?.(m)}
        onDayChange={(d) => onDayChange?.(d)}
        onNavigate={navigate}
        onPause={() => setIsPaused(true)}
      />
      <WordListPanel
        show={showWordList}
        vocabulary={vocabulary}
        queue={queue}
        queueIndex={queueIndex}
        wordStatuses={wordStatuses}
        onClose={() => setShowWordList(false)}
      />
      {showPracticeSettings && (
        <SettingsPanel showSettings={showPracticeSettings} onClose={() => setShowPracticeSettings(false)} />
      )}
      <OptionsMode
        currentWord={currentWord}
        previousWord={previousWord}
        lastState={lastState}
        mode={mode as PracticeMode}
        smartDimension={smartDimension}
        options={options}
        selectedAnswer={selectedAnswer}
        showResult={showResult}
        correctIndex={correctIndex}
        spellingInput={spellingInput}
        spellingResult={spellingResult}
        speechConnected={speechConnected}
        speechRecording={speechRecording}
        settings={settings}
        progressValue={progress}
        total={vocabulary.length}
        queueIndex={queueIndex}
        onOptionSelect={handleOptionSelect}
        onSkip={handleSkip}
        onGoBack={goBack}
        onSpellingSubmit={handleSpellingSubmit}
        onSpellingInputChange={setSpellingInput}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
        onPlayWord={playWord}
      />
      {pauseOverlay}
    </div>
  )
}

export default PracticePage

