import { useEffect } from 'react'
import { playExampleAudio } from '../../../components/practice/utils'
import type { AppSettings, PracticeMode, SmartDimension, Word } from '../../../components/practice/types'
import { openGlobalWordSearch } from '../../../components/layout/navigation/globalWordSearchEvents'
import {
  dispatchPracticeGlobalShortcutNext,
  dispatchPracticeGlobalShortcutPrevious,
  dispatchPracticeGlobalShortcutReplay,
} from '../../../components/practice/page/practiceGlobalShortcutEvents'

interface UsePracticePageKeyboardShortcutsParams {
  mode?: PracticeMode
  smartDimension: SmartDimension
  choiceOptionsReady: boolean
  showWordList: boolean
  showPracticeSettings: boolean
  showResult: boolean
  spellingResult: 'correct' | 'wrong' | null
  currentWord: Word | undefined
  optionsLength: number
  settings: AppSettings
  playWord: (word: string) => void
  handleOptionSelect: (index: number) => void
  handleSkip: () => void
  handleGoBack: () => void
  handleFavoriteToggle: () => void
  onExitHome: () => void
}

export function usePracticePageKeyboardShortcuts({
  mode,
  smartDimension,
  choiceOptionsReady,
  showWordList,
  showPracticeSettings,
  showResult,
  spellingResult,
  currentWord,
  optionsLength,
  settings,
  playWord,
  handleOptionSelect,
  handleSkip,
  handleGoBack,
  handleFavoriteToggle,
  onExitHome,
}: UsePracticePageKeyboardShortcutsParams) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const tagName = target?.tagName
      const isEditableTarget = tagName === 'INPUT' || tagName === 'TEXTAREA' || target?.isContentEditable === true
      const isSpellingInput = tagName === 'INPUT' && target?.classList.contains('spelling-input')
      const usesModeShortcutBridge = mode === 'quickmemory' || mode === 'radio'
      const supportsChoiceShortcuts =
        mode === 'listening' || (mode === 'smart' && smartDimension === 'listening')
      const exampleSentence = currentWord?.examples?.[0]?.en?.trim() ?? ''
      const supportsReplayShortcut = Boolean(currentWord)
      const supportsExampleShortcut = Boolean(exampleSentence) && (
        mode === 'dictation'
        || mode === 'listening'
        || (mode === 'smart' && smartDimension === 'listening')
      )
      const overlayLocked = showWordList || showPracticeSettings
      const navigationLocked = overlayLocked || showResult || Boolean(spellingResult)

      if (event.repeat) return

      if (
        event.shiftKey
        && !event.altKey
        && !event.ctrlKey
        && !event.metaKey
        && !isEditableTarget
      ) {
        const key = event.key.toLowerCase()
        if (key === 'q') {
          event.preventDefault()
          event.stopImmediatePropagation()
          openGlobalWordSearch()
          return
        }
        if (key === 'w') {
          event.preventDefault()
          handleFavoriteToggle()
          return
        }
      }

      if (overlayLocked) {
        if (event.key === 'Escape') onExitHome()
        return
      }

      if (
        supportsExampleShortcut
        && event.key === 'Alt'
        && event.altKey
        && !event.shiftKey
        && !event.ctrlKey
        && !event.metaKey
      ) {
        event.preventDefault()
        event.stopImmediatePropagation()
        if (currentWord?.word && exampleSentence) {
          playExampleAudio(exampleSentence, currentWord.word, settings)
        }
        return
      }

      if (navigationLocked) {
        if (event.key === 'Escape') onExitHome()
        return
      }

      if (
        supportsReplayShortcut
        && event.key === 'Tab'
        && !event.altKey
        && !event.ctrlKey
        && !event.metaKey
        && (!isEditableTarget || isSpellingInput)
      ) {
        event.preventDefault()
        if (usesModeShortcutBridge) {
          dispatchPracticeGlobalShortcutReplay()
        } else {
          playWord(currentWord?.word ?? '')
        }
        return
      }

      if (!isEditableTarget && event.key === 'ArrowLeft') {
        event.preventDefault()
        if (usesModeShortcutBridge) {
          dispatchPracticeGlobalShortcutPrevious()
        } else {
          handleGoBack()
        }
        return
      }

      if (!isEditableTarget && event.key === 'ArrowRight') {
        event.preventDefault()
        if (usesModeShortcutBridge) {
          dispatchPracticeGlobalShortcutNext()
        } else {
          handleSkip()
        }
        return
      }

      if (isEditableTarget) return

      if (supportsChoiceShortcuts && choiceOptionsReady) {
        if (event.key >= '1' && event.key <= '4') {
          const index = parseInt(event.key, 10) - 1
          if (index < optionsLength) handleOptionSelect(index)
        }
        if (event.key === '5') handleSkip()
      }

      if (event.key === 'Escape') onExitHome()
    }

    window.addEventListener('keydown', handleKey, true)
    return () => window.removeEventListener('keydown', handleKey, true)
  }, [
    choiceOptionsReady,
    currentWord?.word,
    handleOptionSelect,
    handleFavoriteToggle,
    handleGoBack,
    handleSkip,
    mode,
    optionsLength,
    settings,
    playWord,
    onExitHome,
    showPracticeSettings,
    showResult,
    showWordList,
    smartDimension,
    spellingResult,
  ])
}
