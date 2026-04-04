import type { Dispatch, SetStateAction } from 'react'
import type { NavigateFunction } from 'react-router-dom'
import type {
  AppSettings,
  Chapter,
  LastState,
  PracticeMode,
  QuickMemoryRecordState,
  RadioQuickSettings,
  SmartDimension,
  Word,
  WordStatuses,
} from '../types'
import {
  PracticePagePauseOverlay,
  PracticePageQuickMemoryLayout,
  PracticePageRadioLayout,
} from './PracticePageStates'
import {
  PracticePageDictationLayout,
  PracticePageOptionsLayout,
} from './PracticePageModeLayouts'

interface PracticePageContentProps {
  mode?: PracticeMode
  currentDay?: number
  resolvedPracticeBookId: string | null
  resolvedPracticeChapterId: string | null
  errorMode: boolean
  vocabulary: Word[]
  currentChapterTitle: string
  bookChapters: Chapter[]
  showWordList: boolean
  setShowWordList: Dispatch<SetStateAction<boolean>>
  showPracticeSettings: boolean
  setShowPracticeSettings: Dispatch<SetStateAction<boolean>>
  onModeChange?: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  navigate: NavigateFunction
  buildChapterPath: (chapterId: string | number) => string
  queue: number[]
  queueIndex: number
  radioIndex: number
  wordStatuses: WordStatuses
  settings: AppSettings
  radioQuickSettings: RadioQuickSettings
  handleRadioSettingChange: (key: string, value: boolean) => void
  markRadioSessionInteraction: () => void
  handleRadioProgressChange: (correctDelta: number, wrongDelta?: number) => void
  reviewMode: boolean
  reviewSummary: { has_more?: boolean } | null
  reviewOffset: number
  saveWrongWord: (word: Word) => void
  handleQuickMemoryRecordChange: (word: Word, record: QuickMemoryRecordState) => void
  setQueueIndex: Dispatch<SetStateAction<number>>
  currentWord: Word
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  previousWord: Word | null
  lastState: LastState | null
  spellingFeedbackLocked: boolean
  spellingFeedbackDismissing: boolean
  spellingFeedbackSnapshot: string | null
  handleSpellingInputChange: (value: string) => void
  handleSpellingSubmit: () => void
  handleSkip: () => void
  goBack: () => void
  startRecording: () => Promise<void>
  stopRecording: () => void
  playWord: (word: string) => void
  smartDimension: SmartDimension
  options: Array<{ text: string }>
  choiceOptionsReady: boolean
  selectedAnswer: number | null
  wrongSelections: number[]
  showResult: boolean
  correctIndex: number
  handleOptionSelect: (index: number) => void
  handleMeaningRecallSubmit: () => void
  isPaused: boolean
  setIsPaused: Dispatch<SetStateAction<boolean>>
  correctCount: number
  wrongCount: number
  handleContinueReview: () => void
}

export function PracticePageContent({
  mode,
  currentDay,
  resolvedPracticeBookId,
  resolvedPracticeChapterId,
  errorMode,
  vocabulary,
  currentChapterTitle,
  bookChapters,
  showWordList,
  setShowWordList,
  showPracticeSettings,
  setShowPracticeSettings,
  onModeChange,
  onDayChange,
  navigate,
  buildChapterPath,
  queue,
  queueIndex,
  radioIndex,
  wordStatuses,
  settings,
  radioQuickSettings,
  handleRadioSettingChange,
  markRadioSessionInteraction,
  handleRadioProgressChange,
  reviewMode,
  reviewSummary,
  reviewOffset,
  saveWrongWord,
  handleQuickMemoryRecordChange,
  setQueueIndex,
  currentWord,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  previousWord,
  lastState,
  spellingFeedbackLocked,
  spellingFeedbackDismissing,
  spellingFeedbackSnapshot,
  handleSpellingInputChange,
  handleSpellingSubmit,
  handleSkip,
  goBack,
  startRecording,
  stopRecording,
  playWord,
  smartDimension,
  options,
  choiceOptionsReady,
  selectedAnswer,
  wrongSelections,
  showResult,
  correctIndex,
  handleOptionSelect,
  handleMeaningRecallSubmit,
  isPaused,
  setIsPaused,
  correctCount,
  wrongCount,
  handleContinueReview,
}: PracticePageContentProps) {
  const progress = queueIndex / Math.max(vocabulary.length, 1)
  const pauseOverlay = (
    <PracticePagePauseOverlay
      isPaused={isPaused}
      mode={mode}
      queue={queue}
      queueIndex={queueIndex}
      correctCount={correctCount}
      wrongCount={wrongCount}
      onResume={() => setIsPaused(false)}
      onExit={() => navigate('/plan')}
    />
  )

  const baseLayoutProps = {
    mode,
    currentDay,
    practiceBookId: resolvedPracticeBookId,
    practiceChapterId: resolvedPracticeChapterId,
    errorMode,
    vocabulary,
    currentChapterTitle,
    bookChapters,
    showWordList,
    showPracticeSettings,
    onWordListToggle: () => setShowWordList(value => !value),
    onSettingsToggle: () => setShowPracticeSettings(value => !value),
    onModeChange: (nextMode: PracticeMode) => onModeChange?.(nextMode),
    onDayChange,
    navigate,
    buildChapterPath: resolvedPracticeBookId ? buildChapterPath : undefined,
    onPause: () => setIsPaused(true),
    queue,
  }

  if (mode === 'radio') {
    return (
      <PracticePageRadioLayout
        {...baseLayoutProps}
        radioIndex={radioIndex}
        wordStatuses={wordStatuses}
        settings={settings}
        radioQuickSettings={radioQuickSettings}
        onRadioSettingChange={handleRadioSettingChange}
        markRadioSessionInteraction={markRadioSessionInteraction}
        handleRadioProgressChange={handleRadioProgressChange}
        pauseOverlay={pauseOverlay}
      />
    )
  }

  if (mode === 'quickmemory') {
    return (
      <PracticePageQuickMemoryLayout
        {...baseLayoutProps}
        settings={settings}
        reviewMode={reviewMode}
        reviewOffset={reviewOffset}
        reviewHasMore={reviewMode ? Boolean(reviewSummary?.has_more) : false}
        onContinueReview={reviewMode ? handleContinueReview : undefined}
        onWrongWord={saveWrongWord}
        onQuickMemoryRecordChange={handleQuickMemoryRecordChange}
        initialIndex={errorMode ? queueIndex : undefined}
        onIndexChange={errorMode ? setQueueIndex : undefined}
        pauseOverlay={pauseOverlay}
      />
    )
  }

  if (mode === 'dictation') {
    return (
      <PracticePageDictationLayout
        {...baseLayoutProps}
        queueIndex={queueIndex}
        wordStatuses={wordStatuses}
        currentWord={currentWord}
        spellingInput={spellingInput}
        spellingResult={spellingResult}
        speechConnected={speechConnected}
        speechRecording={speechRecording}
        settings={settings}
        progressValue={progress}
        previousWord={previousWord}
        lastState={lastState}
        reviewMode={reviewMode}
        spellingLocked={spellingFeedbackLocked}
        spellingFeedbackDismissing={spellingFeedbackDismissing}
        spellingFeedbackSnapshot={spellingFeedbackSnapshot}
        onSpellingInputChange={handleSpellingInputChange}
        onSpellingSubmit={handleSpellingSubmit}
        onSkip={handleSkip}
        onGoBack={goBack}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
        onPlayWord={playWord}
        pauseOverlay={pauseOverlay}
      />
    )
  }

  return (
    <PracticePageOptionsLayout
      {...baseLayoutProps}
      queueIndex={queueIndex}
      wordStatuses={wordStatuses}
      currentWord={currentWord}
      previousWord={previousWord}
      lastState={lastState}
      smartDimension={smartDimension}
      reviewMode={reviewMode}
      options={options}
      optionsLoading={!choiceOptionsReady}
      selectedAnswer={selectedAnswer}
      wrongSelections={wrongSelections}
      showResult={showResult}
      correctIndex={correctIndex}
      spellingInput={spellingInput}
      spellingResult={spellingResult}
      speechConnected={speechConnected}
      speechRecording={speechRecording}
      settings={settings}
      progressValue={progress}
      onOptionSelect={handleOptionSelect}
      onSkip={handleSkip}
      onGoBack={goBack}
      onSpellingSubmit={handleMeaningRecallSubmit}
      onSpellingInputChange={handleSpellingInputChange}
      onStartRecording={startRecording}
      onStopRecording={stopRecording}
      onPlayWord={playWord}
      pauseOverlay={pauseOverlay}
    />
  )
}
