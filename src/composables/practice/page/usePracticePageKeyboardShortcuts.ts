import { useEffect } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { PracticeMode, SmartDimension, Word } from '../../../components/practice/types'

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
  playWord: (word: string) => void
  handleOptionSelect: (index: number) => void
  handleSkip: () => void
  setIsPaused: Dispatch<SetStateAction<boolean>>
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
  playWord,
  handleOptionSelect,
  handleSkip,
  setIsPaused,
}: UsePracticePageKeyboardShortcutsParams) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const tagName = target?.tagName
      const isEditableTarget = tagName === 'INPUT' || tagName === 'TEXTAREA' || target?.isContentEditable === true
      const isSpellingInput = tagName === 'INPUT' && target?.classList.contains('spelling-input')
      const supportsChoiceShortcuts =
        mode === 'listening' || (mode === 'smart' && smartDimension === 'listening')
      const supportsReplayShortcut =
        mode === 'listening'
        || mode === 'dictation'
        || (mode === 'smart' && (smartDimension === 'listening' || smartDimension === 'dictation'))

      if (showWordList || showPracticeSettings || showResult || spellingResult) return

      if (
        supportsReplayShortcut
        && event.key === 'Tab'
        && !event.altKey
        && !event.ctrlKey
        && !event.metaKey
        && (!isEditableTarget || isSpellingInput)
      ) {
        event.preventDefault()
        playWord(currentWord?.word ?? '')
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

      if (event.key === 'Escape') setIsPaused(value => !value)
    }

    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [
    choiceOptionsReady,
    currentWord?.word,
    handleOptionSelect,
    handleSkip,
    mode,
    optionsLength,
    playWord,
    setIsPaused,
    showPracticeSettings,
    showResult,
    showWordList,
    smartDimension,
    spellingResult,
  ])
}
