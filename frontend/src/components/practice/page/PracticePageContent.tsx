import type { Dispatch, SetStateAction } from 'react'
import type { NavigateFunction } from 'react-router-dom'
import FavoriteToggleButton from '../FavoriteToggleButton'
import PracticeControlBar from '../PracticeControlBar'
import WordListPanel from '../WordListPanel'
import GameMode from './GameMode'
import type {
  AppSettings,
  Chapter,
  LastState,
  OptionItem,
  PracticeMode,
  QuickMemoryRecordState,
  RadioQuickSettings,
  SmartDimension,
  SpellingSubmitSource,
  Word,
  WordListActionControls,
  WordStatuses,
} from '../types'
import PracticePronunciationButton from './PracticePronunciationButton'
import SettingsPanel from '../../settings/SettingsPanel'
import {
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
  handleRadioSettingChange: (key: keyof RadioQuickSettings, value: string | boolean) => void
  markRadioSessionInteraction: () => Promise<void>
  handleRadioProgressChange: (correctDelta: number, wrongDelta?: number) => void
  isCurrentSessionActive: (at?: number) => boolean
  reviewMode: boolean
  reviewSummary: { has_more?: boolean } | null
  reviewOffset: number
  saveWrongWord: (word: Word) => void
  handleQuickMemoryRecordChange: (word: Word, record: QuickMemoryRecordState) => void
  currentWord: Word
  favoriteActive: boolean
  favoriteBusy: boolean
  onFavoriteWordIndexChange: (index: number) => void
  onFavoriteToggle: () => void
  wordListActionControls?: WordListActionControls
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
  handleSpellingSubmit: (source?: SpellingSubmitSource) => void
  handleSkip: () => void
  goBack: () => void
  startRecording: () => Promise<void>
  stopRecording: () => void
  playWord: (word: string) => void
  smartDimension: SmartDimension
  options: OptionItem[]
  choiceOptionsReady: boolean
  selectedAnswer: number | null
  wrongSelections: number[]
  showResult: boolean
  correctIndex: number
  handleOptionSelect: (index: number) => void
  handleMeaningRecallSubmit: (source?: SpellingSubmitSource) => void
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
  isCurrentSessionActive,
  reviewMode,
  reviewSummary,
  reviewOffset,
  saveWrongWord,
  handleQuickMemoryRecordChange,
  currentWord,
  favoriteActive,
  favoriteBusy,
  onFavoriteWordIndexChange,
  onFavoriteToggle,
  wordListActionControls,
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
  handleContinueReview,
}: PracticePageContentProps) {
  const progress = Math.min((queueIndex + 1) / Math.max(queue.length, 1), 1)
  const favoriteButton = (
    <FavoriteToggleButton
      active={favoriteActive}
      pending={favoriteBusy}
      onClick={onFavoriteToggle}
    />
  )
  const speakingButton = (
    <PracticePronunciationButton
      bookId={resolvedPracticeBookId}
      chapterId={resolvedPracticeChapterId}
      targetWord={currentWord.word}
      targetPhonetic={currentWord.phonetic}
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
    onExitHome: () => navigate('/plan'),
    queue,
    wordListActionControls,
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
        isCurrentSessionActive={isCurrentSessionActive}
        onIndexChange={onFavoriteWordIndexChange}
        favoriteSlot={favoriteButton}
        speakingSlot={speakingButton}
      />
    )
  }

  if (mode === 'quickmemory') {
    return (
      <PracticePageQuickMemoryLayout
        {...baseLayoutProps}
        queueIndex={radioIndex}
        wordStatuses={wordStatuses}
        settings={settings}
        reviewMode={reviewMode}
        reviewOffset={reviewOffset}
        reviewHasMore={reviewMode ? Boolean(reviewSummary?.has_more) : false}
        onContinueReview={reviewMode ? handleContinueReview : undefined}
        onWrongWord={saveWrongWord}
        onQuickMemoryRecordChange={handleQuickMemoryRecordChange}
        initialIndex={errorMode ? queueIndex : undefined}
        onIndexChange={onFavoriteWordIndexChange}
        favoriteSlot={favoriteButton}
        speakingSlot={speakingButton}
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
        favoriteSlot={favoriteButton}
        speakingSlot={speakingButton}
      />
    )
  }

  if (mode === 'game') {
    return (
      <div className="practice-session-layout">
        <PracticeControlBar
          mode={mode}
          currentDay={currentDay}
          bookId={resolvedPracticeBookId}
          chapterId={resolvedPracticeChapterId}
          errorMode={errorMode}
          vocabularyLength={vocabulary.length}
          currentChapterTitle={currentChapterTitle}
          bookChapters={bookChapters}
          showWordList={showWordList}
          showPracticeSettings={showPracticeSettings}
          onWordListToggle={() => setShowWordList(value => !value)}
          onSettingsToggle={() => setShowPracticeSettings(value => !value)}
          onModeChange={(nextMode: PracticeMode) => onModeChange?.(nextMode)}
          onDayChange={onDayChange}
          onNavigate={navigate}
          buildChapterPath={resolvedPracticeBookId ? buildChapterPath : undefined}
          onExitHome={() => navigate('/plan')}
        />
        <WordListPanel
          show={showWordList}
          vocabulary={vocabulary}
          queue={queue}
          queueIndex={queueIndex}
          wordStatuses={wordStatuses}
          wordActionControls={wordListActionControls}
          onClose={() => setShowWordList(value => !value)}
        />
        {showPracticeSettings ? (
          <SettingsPanel showSettings={showPracticeSettings} onClose={() => setShowPracticeSettings(value => !value)} />
        ) : null}
        <GameMode
          bookId={resolvedPracticeBookId}
          chapterId={resolvedPracticeChapterId}
          currentDay={currentDay}
          vocabulary={vocabulary}
          playWord={playWord}
          wordListActionControls={wordListActionControls}
        />
      </div>
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
      favoriteSlot={favoriteButton}
      speakingSlot={speakingButton}
    />
  )
}
