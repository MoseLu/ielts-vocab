import { useEffect, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { useSpeechRecognition } from '../../../hooks/useSpeechRecognition'
import { setGlobalLearningContext } from '../../../contexts/AIChatContext'
import { loadSmartStats, chooseSmartDimension } from '../../../lib/smartMode'
import { readWrongWordsFromStorage } from '../../../features/vocabulary/wrongWordsStore'
import { buildLearnerProfile, mergeLearnerProfileWithBackend } from '../../../components/practice/learnerProfile'
import {
  generateOptions,
  playWordAudio as playWordUtil,
  stopAudio as stopAudioUtil,
} from '../../../components/practice/utils'
import { normalizeOptionWordKey } from '../../../components/practice/page/practicePageHelpers'
import type {
  LastState,
  OptionItem,
  PracticeMode,
  SmartDimension,
  Word,
} from '../../../components/practice/types'
import type { LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'

interface UsePracticePageEffectsParams {
  userId: string | number | null
  mode?: PracticeMode
  smartDimension: SmartDimension
  setSmartDimension: Dispatch<SetStateAction<SmartDimension>>
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
  currentWord: Word | undefined
  settings: {
    playbackSpeed?: string | number
    volume?: string | number
  }
  backendLearnerProfile: BackendLearnerProfile | null
  setOptions: Dispatch<SetStateAction<OptionItem[]>>
  setCorrectIndex: Dispatch<SetStateAction<number>>
  optionsWordKey: string | null
  setOptionsWordKey: Dispatch<SetStateAction<string | null>>
  setSelectedAnswer: Dispatch<SetStateAction<number | null>>
  setWrongSelections: Dispatch<SetStateAction<number[]>>
  setShowResult: Dispatch<SetStateAction<boolean>>
  setSpellingInput: Dispatch<SetStateAction<string>>
  setSpellingResult: Dispatch<SetStateAction<'correct' | 'wrong' | null>>
  setSpellingFeedbackLocked: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackDismissing: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackSnapshot: Dispatch<SetStateAction<string | null>>
  correctCount: number
  wrongCount: number
  errorMode: boolean
  bookId: string | null
  chapterId: string | null
  currentChapterTitle: string
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  handleSpellingInputChange: (value: string) => void
}

interface UsePracticePageEffectsResult {
  speechConnected: boolean
  speechRecording: boolean
  startSpeechRecording: () => Promise<void>
  stopSpeechRecording: () => void
  choiceOptionsReady: boolean
}

export function usePracticePageEffects({
  userId,
  mode,
  smartDimension,
  setSmartDimension,
  vocabulary,
  queue,
  queueIndex,
  currentWord,
  settings,
  backendLearnerProfile,
  setOptions,
  setCorrectIndex,
  optionsWordKey,
  setOptionsWordKey,
  setSelectedAnswer,
  setWrongSelections,
  setShowResult,
  setSpellingInput,
  setSpellingResult,
  setSpellingFeedbackLocked,
  setSpellingFeedbackDismissing,
  setSpellingFeedbackSnapshot,
  correctCount,
  wrongCount,
  errorMode,
  bookId,
  chapterId,
  currentChapterTitle,
  showToast,
  handleSpellingInputChange,
}: UsePracticePageEffectsParams): UsePracticePageEffectsResult {
  const autoPlayTimerRef = useRef<number | null>(null)
  const autoPlayStartedKeyRef = useRef<string | null>(null)
  const currentOptionsWordKey = normalizeOptionWordKey(currentWord?.word)
  const choiceOptionsReady = currentOptionsWordKey != null && currentOptionsWordKey === optionsWordKey

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
      handleSpellingInputChange(cleanText.toLowerCase())
      showToast?.('识别成功', 'success')
    },
    onPartial: (text: string) => {
      const cleanText = text.replace(/[.,!?;:'" ]+$/, '')
      handleSpellingInputChange(cleanText.toLowerCase())
    },
    onError: (error: string) => {
      showToast?.(`识别失败: ${error}`, 'error')
    },
  })

  useEffect(() => {
    if (!currentWord || !vocabulary.length) return

    let cancelled = false
    const smartStats = loadSmartStats()
    const subMode: SmartDimension = mode === 'smart'
      ? chooseSmartDimension(currentWord.word, smartStats)
      : smartDimension
    if (mode === 'smart') {
      setSmartDimension(prev => (prev === subMode ? prev : subMode))
    }

    const wrongWords = readWrongWordsFromStorage(userId)
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
    const needsOptions = mode === 'listening' || (mode === 'smart' && subMode === 'listening')
    const currentWordKey = normalizeOptionWordKey(currentWord.word)

    const applyGeneratedOptions = ({
      options: nextOptions,
      correctIndex: nextCorrectIndex,
    }: {
      options: OptionItem[]
      correctIndex: number
    }) => {
      if (cancelled) return
      setOptions(nextOptions)
      setCorrectIndex(nextCorrectIndex)
      setOptionsWordKey(currentWordKey)
    }

    if (needsOptions) {
      const localPool = [currentWord, ...vocabulary, ...learnerProfile.priorityWords]
      const localGeneratedOptions = generateOptions(currentWord, localPool, {
        mode: 'listening',
        priorityWords: learnerProfile.priorityWords,
      })
      const presetListeningWords = currentWord.listening_confusables ?? []

      if (presetListeningWords.length >= 3) {
        applyGeneratedOptions(generateOptions(currentWord, [currentWord, ...presetListeningWords], { mode: 'listening' }))
      } else if (presetListeningWords.length > 0) {
        applyGeneratedOptions(generateOptions(
          currentWord,
          [currentWord, ...presetListeningWords, ...vocabulary, ...learnerProfile.priorityWords],
          {
            mode: 'listening',
            priorityWords: [...presetListeningWords, ...learnerProfile.priorityWords],
          },
        ))
      } else {
        applyGeneratedOptions(localGeneratedOptions)
      }
    } else {
      setOptions([])
      setCorrectIndex(0)
      setOptionsWordKey(null)
    }

    setSelectedAnswer(null)
    setWrongSelections([])
    setShowResult(false)
    setSpellingInput('')
    setSpellingResult(null)
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)

    return () => {
      cancelled = true
    }
  }, [
    backendLearnerProfile,
    currentWord?.word,
    mode,
    queueIndex,
    setCorrectIndex,
    setOptions,
    setOptionsWordKey,
    setSelectedAnswer,
    setShowResult,
    setSmartDimension,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    setWrongSelections,
    settings.playbackSpeed,
    settings.volume,
    smartDimension,
    userId,
    vocabulary,
  ])

  useEffect(() => {
    if (!currentWord) return
    const shouldAutoPlay = mode === 'listening'
      || mode === 'dictation'
      || (mode === 'smart' && (smartDimension === 'listening' || smartDimension === 'dictation'))
    if (!shouldAutoPlay) return

    const isDictation = mode === 'dictation' || (mode === 'smart' && smartDimension === 'dictation')
    if (isDictation && currentWord.examples?.[0]?.en) return

    if (autoPlayTimerRef.current != null) {
      window.clearTimeout(autoPlayTimerRef.current)
      autoPlayTimerRef.current = null
    }

    const autoPlayKey = `${mode}:${smartDimension}:${queueIndex}:${currentWord.word}`
    if (autoPlayStartedKeyRef.current === autoPlayKey) return

    autoPlayTimerRef.current = window.setTimeout(() => {
      autoPlayTimerRef.current = null
      autoPlayStartedKeyRef.current = autoPlayKey
      playWordUtil(currentWord.word, settings)
    }, 280)

    return () => {
      if (autoPlayTimerRef.current != null) {
        window.clearTimeout(autoPlayTimerRef.current)
        autoPlayTimerRef.current = null
      }
    }
  }, [currentWord, mode, queueIndex, settings, smartDimension])

  useEffect(() => {
    autoPlayStartedKeyRef.current = null
    return () => {
      stopAudioUtil()
      if (autoPlayTimerRef.current != null) {
        window.clearTimeout(autoPlayTimerRef.current)
        autoPlayTimerRef.current = null
      }
    }
  }, [currentWord?.word, mode, queueIndex])

  useEffect(() => {
    const accuracy = correctCount + wrongCount > 0
      ? Math.round((correctCount / (correctCount + wrongCount)) * 100)
      : undefined
    const wrongWords = readWrongWordsFromStorage(userId)
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
  }, [
    backendLearnerProfile,
    bookId,
    chapterId,
    correctCount,
    currentChapterTitle,
    currentWord,
    errorMode,
    mode,
    queue.length,
    queueIndex,
    smartDimension,
    userId,
    vocabulary,
    wrongCount,
  ])

  return {
    speechConnected,
    speechRecording,
    startSpeechRecording,
    stopSpeechRecording,
    choiceOptionsReady,
  }
}
