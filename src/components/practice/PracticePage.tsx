// ── Practice Page (Main Container) ──────────────────────────────────────────────

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition'
import type { PracticePageProps, PracticeMode, Word, ProgressData, AppSettings, Chapter, LastState, WordStatuses, RadioQuickSettings, SmartDimension } from './types'
import { shuffleArray, generateOptions, playWordAudio as playWordUtil } from './utils'
import { DEFAULT_SETTINGS } from '../../constants'
import { setGlobalLearningContext } from '../../contexts/AIChatContext'
import { loadSmartStats, recordWordResult, chooseSmartDimension, buildSmartQueue } from '../../lib/smartMode'
import { recordModeAnswer, logSession } from '../../hooks/useAIChat'
import PracticeControlBar from './PracticeControlBar'
import WordListPanel from './WordListPanel'
import RadioMode from './RadioMode'
import DictationMode from './DictationMode'
import OptionsMode from './OptionsMode'
import QuickMemoryMode from './QuickMemoryMode'
import SettingsPanel from '../SettingsPanel'

// Re-export types for use by parent components
export type { PracticeMode, Word, ProgressData, AppSettings, Chapter }

function PracticePage({ user, currentDay, mode, showToast, onModeChange, onDayChange }: PracticePageProps) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const bookId = searchParams.get('book')
  const chapterId = searchParams.get('chapter')
  const errorMode = searchParams.get('mode') === 'errors'

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

  // Smart mode: current word's test dimension (音/意/形)
  const [smartDimension, setSmartDimension] = useState<SmartDimension>('meaning')

  // Refs
  const vocabRef = useRef<Word[]>([])
  const queueRef = useRef<number[]>([])
  const sessionStartRef = useRef<number>(Date.now())

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
      showToast?.('识别成功！', 'success')
    },
    onPartial: (text: string) => {
      const cleanText = text.replace(/[.,!?;:'" ]+$/, '')
      setSpellingInput(cleanText.toLowerCase())
    },
    onError: (error: string) => {
      showToast?.('识别失败: ' + error, 'error')
    },
  })

  // Fetch book chapters
  useEffect(() => {
    if (!bookId) return
    fetch(`/api/books/${bookId}/chapters`)
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

  // Restore progress helper
  const restoreProgress = (data: ProgressData) => {
    setQueueIndex(data.current_index || 0)
    setCorrectCount(data.correct_count || 0)
    setWrongCount(data.wrong_count || 0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
  }

  // Load vocabulary data
  useEffect(() => {
    if (errorMode) {
      try {
        const saved: Word[] = JSON.parse(localStorage.getItem('wrong_words') || '[]')
        setVocabulary(saved)
        vocabRef.current = saved
        const indices = Array.from({ length: saved.length }, (_, i) => i)
        const q = settings.shuffle !== false ? shuffleArray(indices) : indices
        setQueue(q)
        queueRef.current = q
        setQueueIndex(0); setCorrectCount(0); setWrongCount(0)
      } catch {
        showToast?.('加载错词失败', 'error')
      }
      return
    }

    // Helper: build queue based on mode (smart = sorted by weakness, others = shuffle)
    const buildQueue = (words: Word[]) => {
      const indices = Array.from({ length: words.length }, (_, i) => i)
      if (mode === 'smart') return buildSmartQueue(words.map(w => w.word), loadSmartStats())
      return settings.shuffle !== false ? shuffleArray(indices) : indices
    }

    if (bookId) {
      if (chapterId) {
        fetch(`/api/books/${bookId}/chapters/${chapterId}`)
          .then(res => res.json())
          .then((data: { words?: Word[] }) => {
            const words = data.words || []
            setVocabulary(words)
            vocabRef.current = words
            const q = buildQueue(words)
            setQueue(q)
            queueRef.current = q
            const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
            const key = `${bookId}_${chapterId}`
            if (saved[key]) restoreProgress(saved[key])
            else { setQueueIndex(0); setCorrectCount(0); setWrongCount(0) }
          })
          .catch(() => showToast?.('加载章节词汇失败', 'error'))
        return
      }

      fetch(`/api/books/${bookId}/words?per_page=100`)
        .then(res => res.json())
        .then((data: { words?: Word[] }) => {
          const words = data.words || []
          setVocabulary(words)
          vocabRef.current = words
          const q = buildQueue(words)
          setQueue(q)
          queueRef.current = q
          const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('book_progress') || '{}')
          if (saved[bookId]) restoreProgress(saved[bookId])
          else { setQueueIndex(0); setCorrectCount(0); setWrongCount(0) }
        })
        .catch(() => showToast?.('加载词书失败', 'error'))
      return
    }

    if (!currentDay) { navigate('/'); return }
    fetch(`/api/vocabulary/day/${currentDay}`)
      .then(res => res.json())
      .then((data: { vocabulary?: Word[]; words?: Word[] }) => {
        const words = data.vocabulary || data.words || []
        setVocabulary(words)
        vocabRef.current = words
        const q = buildQueue(words)
        setQueue(q)
        queueRef.current = q
        const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('day_progress') || '{}')
        if (saved[String(currentDay)]) restoreProgress(saved[String(currentDay)])
        else { setQueueIndex(0); setCorrectCount(0); setWrongCount(0) }
      })
      .catch(() => showToast?.('加载词汇失败', 'error'))
  }, [currentDay, bookId, errorMode, chapterId])

  const currentWord: Word | undefined = vocabulary[queue[queueIndex]]

  // Update options when word changes
  useEffect(() => {
    if (!currentWord || !vocabulary.length) return

    // For smart mode: choose which dimension to test for this word
    let subMode: SmartDimension = smartDimension
    if (mode === 'smart') {
      const stats = loadSmartStats()
      subMode = chooseSmartDimension(currentWord.word, stats)
      setSmartDimension(subMode)
    }

    // Generate options for multiple-choice modes (not needed for dictation sub-mode)
    const needsOptions = mode === 'listening' || mode === 'meaning' ||
      (mode === 'smart' && subMode !== 'dictation')
    if (needsOptions) {
      const { options: opts, correctIndex: ci } = generateOptions(currentWord, vocabulary)
      setOptions(opts); setCorrectIndex(ci)
    }

    setSelectedAnswer(null); setShowResult(false); setSpellingInput(''); setSpellingResult(null)

    // Auto-play audio for audio-first modes
    const shouldAutoPlay = mode === 'listening' || mode === 'dictation' ||
      (mode === 'smart' && (subMode === 'listening' || subMode === 'dictation'))
    if (shouldAutoPlay) {
      setTimeout(() => playWordUtil(currentWord.word, settings), 300)
    }
  }, [queueIndex, currentWord?.word, mode])

  // Log learning context to AI chat whenever state changes
  useEffect(() => {
    const accuracy = correctCount + wrongCount > 0
      ? Math.round((correctCount / (correctCount + wrongCount)) * 100)
      : undefined
    if (!currentWord) {
      // Session just completed — record final state so AI sees the full round
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
    })
  }, [currentWord, mode, queueIndex, correctCount, wrongCount, errorMode])

  // Save progress
  const saveProgress = useCallback((correct: number, wrong: number) => {
    const token = localStorage.getItem('auth_token')

    if (errorMode) {
      const wrongProgress: Record<string, { correctCount: number; wrongCount: number; updatedAt: string }> =
        JSON.parse(localStorage.getItem('wrong_words_progress') || '{}')
      wrongProgress['_last'] = { correctCount: correct, wrongCount: wrong, updatedAt: new Date().toISOString() }
      localStorage.setItem('wrong_words_progress', JSON.stringify(wrongProgress))
      return
    }

    const progressData: ProgressData = {
      current_index: queueIndex,
      correct_count: correct,
      wrong_count: wrong,
      is_completed: correct + wrong >= vocabulary.length
    }

    if (bookId) {
      const bookProgress: Record<string, ProgressData> = JSON.parse(localStorage.getItem('book_progress') || '{}')
      bookProgress[bookId] = { ...progressData, updatedAt: new Date().toISOString() }
      localStorage.setItem('book_progress', JSON.stringify(bookProgress))

      if (token) {
        fetch('/api/books/progress', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ book_id: bookId, ...progressData })
        }).catch(() => {})

        if (chapterId) {
          const chapterProgress: Record<string, ProgressData> = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
          chapterProgress[`${bookId}_${chapterId}`] = { words_learned: correct + wrong, ...progressData, updatedAt: new Date().toISOString() }
          localStorage.setItem('chapter_progress', JSON.stringify(chapterProgress))
          fetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ words_learned: correct + wrong, ...progressData })
          }).catch(() => {})

          // Save per-mode accuracy to the backend — each mode is stored independently
          if (mode && correct + wrong > 0) {
            fetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
              body: JSON.stringify({
                mode,
                correct_count: correct,
                wrong_count: wrong,
                is_completed: progressData.is_completed ?? false,
              }),
            }).catch(() => {})
          }
        }
      }
    } else {
      const dayProgress: Record<string, ProgressData> = JSON.parse(localStorage.getItem('day_progress') || '{}')
      dayProgress[String(currentDay)] = { ...progressData, is_completed: correct + wrong >= vocabulary.length, updatedAt: new Date().toISOString() }
      localStorage.setItem('day_progress', JSON.stringify(dayProgress))

      if (token) {
        fetch('/api/progress', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ day: currentDay, ...progressData })
        }).catch(() => {})
      }
    }
  }, [bookId, chapterId, currentDay, errorMode, queueIndex, vocabulary.length])

  const saveWrongWord = (word: Word) => {
    const existing: Word[] = JSON.parse(localStorage.getItem('wrong_words') || '[]')
    if (!existing.find(w => w.word === word.word)) {
      existing.push(word)
      localStorage.setItem('wrong_words', JSON.stringify(existing))
      // Sync to backend
      const token = localStorage.getItem('auth_token')
      if (token) {
        fetch('/api/ai/wrong-words/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ words: [word] }),
        }).catch(() => {})
      }
    }
  }

  const goNext = (wasCorrect: boolean) => {
    setLastState({ qi: queueIndex, cc: correctCount, wc: wrongCount, prevWord: previousWord })
    setPreviousWord(currentWord ?? null)
    if (!wasCorrect && settings.repeatWrong !== false) {
      setQueue(prev => { const c = [...prev]; c.push(queue[queueIndex]); return c })
    }
    if (queueIndex + 1 >= queue.length) navigate('/')
    else setQueueIndex(prev => prev + 1)
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
    if (!isCorrect && currentWord) saveWrongWord(currentWord)
    saveProgress(nc, nw)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: isCorrect ? 'correct' : 'wrong' }))
    // Record per-dimension stats for smart mode weighting
    if (currentWord) {
      const dim: SmartDimension = mode === 'smart' ? smartDimension
        : mode === 'listening' ? 'listening' : 'meaning'
      recordWordResult(currentWord.word, dim, isCorrect)
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
    if (!isCorrect) saveWrongWord(currentWord)
    saveProgress(nc, nw)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: isCorrect ? 'correct' : 'wrong' }))
    // Record dictation stats for smart mode weighting
    recordWordResult(currentWord.word, 'dictation', isCorrect)
    recordModeAnswer(mode ?? 'dictation', isCorrect)
    setTimeout(() => goNext(isCorrect), 1500)
  }

  const handleSkip = () => {
    if (!currentWord) return
    saveWrongWord(currentWord)
    const nw = wrongCount + 1
    setWrongCount(nw); saveProgress(correctCount, nw)
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

  // Loading state
  if (!vocabulary.length) {
    return <div className="practice-loading"><div className="loading-spinner"></div><p>加载词汇中...</p></div>
  }

  // Completed state — log session for AI analysis
  if (!currentWord) {
    const durationSec = Math.round((Date.now() - sessionStartRef.current) / 1000)
    // Fire-and-forget session log (non-blocking)
    logSession({
      mode: mode ?? 'smart',
      bookId,
      chapterId,
      wordsStudied: correctCount + wrongCount,
      correctCount,
      wrongCount,
      durationSeconds: durationSec,
      startedAt: sessionStartRef.current,
    })
    return (
      <div className="practice-complete">
        <div className="complete-emoji">🎉</div>
        <h2>{errorMode ? '错词复习完成！' : bookId ? '本章完成！' : `Day ${currentDay} 完成！`}</h2>
        <div className="complete-stats-row">
          <span className="stat-correct">✓ 正确 {correctCount}</span>
          <span className="stat-wrong">✗ 错误 {wrongCount}</span>
        </div>
        <button className="complete-btn" onClick={() => navigate('/')}>返回主页</button>
      </div>
    )
  }

  const progress = queueIndex / Math.max(vocabulary.length, 1)

  // Pause overlay — shared across all render branches
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
                <span className="practice-pause-correct">✓ {correctCount}</span>
                <span className="practice-pause-wrong">✗ {wrongCount}</span>
              </span>
            )}
          </div>
        )}
        <p className="practice-pause-hint">
          进度已自动保存 — 退出登录后再回到本章节，仍可从这里继续
        </p>
        <div className="practice-pause-actions">
          <button className="practice-pause-resume" onClick={() => setIsPaused(false)}>
            继续练习
          </button>
          <button className="practice-pause-exit" onClick={() => navigate('/')}>
            退出到主页
          </button>
        </div>
      </div>
    </div>
  )

  // Render different modes
  if (mode === 'radio') {
    return (
      <>
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
        />
        {pauseOverlay}
      </>
    )
  }

  if (mode === 'quickmemory') {
    return (
      <>
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
          vocabulary={vocabulary}
          queue={queue}
          settings={settings}
          bookId={bookId}
          chapterId={chapterId}
          bookChapters={bookChapters}
          onModeChange={(m) => onModeChange?.(m as PracticeMode)}
          onNavigate={navigate}
          onWrongWord={saveWrongWord}
        />
        {pauseOverlay}
      </>
    )
  }

  if (mode === 'dictation') {
    return (
      <>
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
      </>
    )
  }

  // Listening / Meaning / Smart modes
  return (
    <>
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
    </>
  )
}

export default PracticePage
