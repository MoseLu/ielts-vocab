import { useLayoutEffect, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { useSpeechRecognition } from '../../../hooks/useSpeechRecognition'
import { loadSmartStats, chooseSmartDimension } from '../../../lib/smartMode'
import { readWrongWordsFromStorage } from '../../../features/vocabulary/wrongWordsStore'
import { buildLearnerProfile, mergeLearnerProfileWithBackend } from '../../../features/practice/learnerProfile'
import {
  buildPresetListeningOptions,
  generateOptions,
} from '../../../features/practice/practiceOptions'
import { normalizeOptionWordKey } from '../../../features/practice/practiceSessionHelpers'
import type {
  AppSettings,
  OptionItem,
  PracticeMode,
  SmartDimension,
  Word,
} from '../../../features/practice/types'
import type { LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'
import { usePracticePageAudioEffects } from './usePracticePageAudioEffects'
import { usePracticeGlobalLearningContext } from './usePracticeGlobalLearningContext'

interface UsePracticePageEffectsParams {
  userId: string | number | null
  mode?: PracticeMode
  smartDimension: SmartDimension
  setSmartDimension: Dispatch<SetStateAction<SmartDimension>>
  vocabulary: Word[]
  listeningOptionPool?: Word[]
  queue: number[]
  queueIndex: number
  currentWord: Word | undefined
  optionsCount: number
  settings: AppSettings
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
  listeningOptionPool = [],
  queue,
  queueIndex,
  currentWord,
  optionsCount,
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
  const interactionStateKeyRef = useRef<string | null>(null)
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

  usePracticePageAudioEffects({
    currentWord,
    mode,
    queue,
    queueIndex,
    settings,
    smartDimension,
    vocabulary,
  })

  usePracticeGlobalLearningContext({
    backendLearnerProfile,
    bookId,
    chapterId,
    correctCount,
    currentChapterTitle,
    currentWord,
    errorMode,
    mode,
    queueIndex,
    queueLength: queue.length,
    smartDimension,
    userId,
    vocabulary,
    wrongCount,
  })

  useLayoutEffect(() => {
    if (!currentWord || !vocabulary.length) return

    let cancelled = false
    const smartStats = mode === 'smart' || mode === 'listening'
      ? loadSmartStats()
      : null
    const subMode: SmartDimension = mode === 'smart' && smartStats
      ? chooseSmartDimension(currentWord.word, smartStats)
      : smartDimension
    if (mode === 'smart') {
      setSmartDimension(prev => (prev === subMode ? prev : subMode))
    }

    const needsOptions = mode === 'listening' || (mode === 'smart' && subMode === 'listening')
    const currentWordKey = normalizeOptionWordKey(currentWord.word)
    const presetListeningWords = currentWord.listening_confusables ?? []
    const hasCompleteListeningPresets = presetListeningWords.length >= 3
    const hasSufficientChoiceOptions = optionsCount >= 4
    const interactionStateKey = currentWordKey
      ? `${mode ?? 'unknown'}:${subMode}:${queueIndex}:${currentWordKey}`
      : null

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

    if (interactionStateKeyRef.current !== interactionStateKey) {
      interactionStateKeyRef.current = interactionStateKey
      setSelectedAnswer(null)
      setWrongSelections([])
      setShowResult(false)
      setSpellingInput('')
      setSpellingResult(null)
      setSpellingFeedbackLocked(false)
      setSpellingFeedbackDismissing(false)
      setSpellingFeedbackSnapshot(null)
    }

    if (needsOptions) {
      if (currentWordKey != null && currentWordKey === optionsWordKey && hasSufficientChoiceOptions) {
        return () => {
          cancelled = true
        }
      }

      const resolvedSmartStats = smartStats ?? loadSmartStats()
      const wrongWords = readWrongWordsFromStorage(userId)
      const localLearnerProfile = buildLearnerProfile({
        vocabulary,
        currentWord,
        mode,
        smartDimension: subMode,
        smartStats: resolvedSmartStats,
        wrongWords,
      })
      const learnerProfile = mergeLearnerProfileWithBackend({
        localProfile: localLearnerProfile,
        backendProfile: backendLearnerProfile,
        vocabulary,
        wrongWords,
      })
      const listeningCandidates = listeningOptionPool.length ? listeningOptionPool : vocabulary
      if (hasCompleteListeningPresets) {
        const presetOptions = buildPresetListeningOptions(currentWord, presetListeningWords)
        if (presetOptions.options.length >= 4) {
          applyGeneratedOptions(presetOptions)
        } else {
          applyGeneratedOptions(generateOptions(
            currentWord,
            [currentWord, ...presetListeningWords, ...listeningCandidates, ...learnerProfile.priorityWords],
            {
              mode: 'listening',
              priorityWords: [...presetListeningWords, ...learnerProfile.priorityWords],
            },
          ))
        }
      } else if (presetListeningWords.length > 0) {
        applyGeneratedOptions(generateOptions(
          currentWord,
          [currentWord, ...presetListeningWords, ...listeningCandidates, ...learnerProfile.priorityWords],
          {
            mode: 'listening',
            priorityWords: [...presetListeningWords, ...learnerProfile.priorityWords],
          },
        ))
      } else {
        applyGeneratedOptions(generateOptions(currentWord, [currentWord, ...listeningCandidates, ...learnerProfile.priorityWords], {
          mode: 'listening',
          priorityWords: learnerProfile.priorityWords,
        }))
      }
    } else {
      setOptions([])
      setCorrectIndex(0)
      setOptionsWordKey(null)
    }

    return () => {
      cancelled = true
    }
  }, [
    backendLearnerProfile,
    currentWord?.word,
    mode,
    optionsWordKey,
    optionsCount,
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
    listeningOptionPool,
    vocabulary,
  ])

  return {
    speechConnected,
    speechRecording,
    startSpeechRecording,
    stopSpeechRecording,
    choiceOptionsReady,
  }
}
