import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PracticePageContent } from './PracticePageContent'
import type { PracticeMode, RadioQuickSettings, SmartDimension, Word } from '../types'

vi.mock('../FavoriteToggleButton', () => ({
  default: () => <div data-testid="favorite-toggle" />,
}))

vi.mock('../PracticeControlBar', () => ({
  default: () => null,
}))

vi.mock('../../settings/SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('./PracticePronunciationButton', () => ({
  default: ({ targetWord }: { targetWord: string }) => <div data-testid="pronunciation-word">{targetWord}</div>,
}))

vi.mock('./PracticePageStates', () => ({
  PracticePageQuickMemoryLayout: ({ speakingSlot }: { speakingSlot?: React.ReactNode }) => (
    <div data-testid="quickmemory-layout">{speakingSlot}</div>
  ),
  PracticePageRadioLayout: () => null,
}))

vi.mock('./PracticePageModeLayouts', () => ({
  PracticePageDictationLayout: () => null,
  PracticePageFollowLayout: () => null,
  PracticePageOptionsLayout: () => null,
}))

const vocabulary: Word[] = [
  { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
  { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
]

function buildProps(radioIndex: number) {
  const navigate = vi.fn()
  const practiceMode: PracticeMode = 'quickmemory'
  const smartDimension: SmartDimension = 'meaning'
  const radioQuickSettings: RadioQuickSettings = {
    playbackSpeed: '1',
    playbackCount: '1',
    loopMode: false,
    interval: '0',
  }

  return {
    mode: practiceMode,
    currentDay: 1,
    resolvedPracticeBookId: null,
    resolvedPracticeChapterId: null,
    errorMode: false,
    vocabulary,
    currentChapterTitle: '艾宾浩斯复习',
    bookChapters: [],
    showWordList: false,
    setShowWordList: vi.fn(),
    showPracticeSettings: false,
    setShowPracticeSettings: vi.fn(),
    onModeChange: vi.fn(),
    onDayChange: vi.fn(),
    navigate,
    buildChapterPath: vi.fn(() => '/practice'),
    queue: [0, 1],
    queueIndex: 0,
    radioIndex,
    wordStatuses: {},
    settings: {},
    radioQuickSettings,
    handleRadioSettingChange: vi.fn(),
    markRadioSessionInteraction: vi.fn(async () => {}),
    handleRadioProgressChange: vi.fn(),
    markFollowSessionInteraction: vi.fn(async () => {}),
    completeFollowSession: vi.fn(async () => {}),
    isCurrentSessionActive: vi.fn(() => true),
    reviewMode: true,
    reviewSummary: null,
    reviewOffset: 0,
    saveWrongWord: vi.fn(),
    handleQuickMemoryRecordChange: vi.fn(),
    currentWord: vocabulary[0],
    favoriteActive: false,
    favoriteBusy: false,
    onFavoriteWordIndexChange: vi.fn(),
    onFavoriteToggle: vi.fn(),
    wordListActionControls: undefined,
    spellingInput: '',
    spellingResult: null,
    speechConnected: false,
    speechRecording: false,
    previousWord: null,
    lastState: null,
    spellingFeedbackLocked: false,
    spellingFeedbackDismissing: false,
    spellingFeedbackSnapshot: null,
    handleSpellingInputChange: vi.fn(),
    handleSpellingSubmit: vi.fn(),
    handleSkip: vi.fn(),
    goBack: vi.fn(),
    startRecording: vi.fn(async () => {}),
    stopRecording: vi.fn(),
    playWord: vi.fn(),
    smartDimension,
    options: [],
    choiceOptionsReady: true,
    selectedAnswer: null,
    wrongSelections: [],
    showResult: false,
    correctIndex: 0,
    handleOptionSelect: vi.fn(),
    handleMeaningRecallSubmit: vi.fn(),
    handleContinueReview: vi.fn(),
  }
}

describe('PracticePageContent quick-memory pronunciation target', () => {
  it('tracks the currently displayed quick-memory word instead of the stale parent currentWord', () => {
    const { rerender } = render(<PracticePageContent {...buildProps(0)} />)

    expect(screen.getByTestId('pronunciation-word')).toHaveTextContent('alpha')

    rerender(<PracticePageContent {...buildProps(1)} />)

    expect(screen.getByTestId('pronunciation-word')).toHaveTextContent('beta')
  })
})
