import type { NavigateFunction } from 'react-router-dom'
import type { ReactNode } from 'react'
import PracticeControlBar from '../PracticeControlBar'
import WordListPanel from '../WordListPanel'
import DictationMode from '../DictationMode'
import FollowMode from '../FollowMode'
import OptionsMode from '../OptionsMode'
import SettingsPanel from '../../settings/SettingsPanel'
import type {
  AppSettings,
  Chapter,
  LastState,
  OptionItem,
  PracticeMode,
  SmartDimension,
  SpellingSubmitSource,
  Word,
  WordPlaybackHandler,
  WordListActionControls,
  WordStatuses,
} from '../types'

interface SharedModeLayoutProps {
  mode?: PracticeMode
  currentDay?: number
  practiceBookId: string | null
  practiceChapterId: string | null
  errorMode: boolean
  vocabulary: Word[]
  currentChapterTitle: string
  bookChapters: Chapter[]
  showWordList: boolean
  showPracticeSettings: boolean
  onWordListToggle: () => void
  onSettingsToggle: () => void
  onModeChange: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  navigate: NavigateFunction
  buildChapterPath?: (chapterId: string | number) => string
  onExitHome: () => void
  queue: number[]
  queueIndex: number
  wordStatuses: WordStatuses
  favoriteSlot?: ReactNode
  speakingSlot?: ReactNode
  wordListActionControls?: WordListActionControls
}

interface PracticePageDictationLayoutProps extends SharedModeLayoutProps {
  currentWord: Word
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  settings: AppSettings
  progressValue: number
  previousWord: Word | null
  lastState: LastState | null
  reviewMode: boolean
  spellingLocked: boolean
  spellingFeedbackDismissing: boolean
  spellingFeedbackSnapshot: string | null
  onSpellingInputChange: (value: string) => void
  onSpellingSubmit: (source?: SpellingSubmitSource) => void
  onSkip: () => void
  onGoBack: () => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: WordPlaybackHandler
}

export function PracticePageDictationLayout(props: PracticePageDictationLayoutProps) {
  const {
    mode,
    currentDay,
    practiceBookId,
    practiceChapterId,
    errorMode,
    vocabulary,
    currentChapterTitle,
    bookChapters,
    showWordList,
    showPracticeSettings,
    onWordListToggle,
    onSettingsToggle,
    onModeChange,
    onDayChange,
    navigate,
    buildChapterPath,
    onExitHome,
    queue,
    queueIndex,
    wordStatuses,
    favoriteSlot,
    speakingSlot,
    wordListActionControls,
    currentWord,
    spellingInput,
    spellingResult,
    speechConnected,
    speechRecording,
    settings,
    progressValue,
    previousWord,
    lastState,
    reviewMode,
    spellingLocked,
    spellingFeedbackDismissing,
    spellingFeedbackSnapshot,
    onSpellingInputChange,
    onSpellingSubmit,
    onSkip,
    onGoBack,
    onStartRecording,
    onStopRecording,
    onPlayWord,
  } = props

  return (
    <div className="practice-session-layout">
      <PracticeControlBar
        mode={mode}
        currentDay={currentDay}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        errorMode={errorMode}
        vocabularyLength={vocabulary.length}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        showPracticeSettings={showPracticeSettings}
        onWordListToggle={onWordListToggle}
        onSettingsToggle={onSettingsToggle}
        onModeChange={onModeChange}
        onDayChange={onDayChange}
        onNavigate={navigate}
        buildChapterPath={buildChapterPath}
        onExitHome={onExitHome}
      />
      <WordListPanel
        show={showWordList}
        vocabulary={vocabulary}
        queue={queue}
        queueIndex={queueIndex}
        wordStatuses={wordStatuses}
        wordActionControls={wordListActionControls}
        onClose={onWordListToggle}
      />
      {showPracticeSettings && (
        <SettingsPanel showSettings={showPracticeSettings} onClose={onSettingsToggle} />
      )}
      <DictationMode
        currentWord={currentWord}
        spellingInput={spellingInput}
        spellingResult={spellingResult}
        speechConnected={speechConnected}
        speechRecording={speechRecording}
        settings={settings}
        progressValue={progressValue}
        total={queue.length}
        queueIndex={queueIndex}
        previousWord={previousWord}
        lastState={lastState}
        errorMode={errorMode}
        reviewMode={reviewMode}
        spellingLocked={spellingLocked}
        spellingFeedbackDismissing={spellingFeedbackDismissing}
        spellingFeedbackSnapshot={spellingFeedbackSnapshot}
        onSpellingInputChange={onSpellingInputChange}
        onSpellingSubmit={onSpellingSubmit}
        onSkip={onSkip}
        onGoBack={onGoBack}
        onStartRecording={onStartRecording}
        onStopRecording={onStopRecording}
        onPlayWord={onPlayWord}
        favoriteSlot={favoriteSlot}
        speakingSlot={speakingSlot}
      />
    </div>
  )
}

interface PracticePageOptionsLayoutProps extends SharedModeLayoutProps {
  currentWord: Word
  previousWord: Word | null
  lastState: LastState | null
  smartDimension: SmartDimension
  reviewMode: boolean
  options: OptionItem[]
  optionsLoading: boolean
  selectedAnswer: number | null
  wrongSelections: number[]
  showResult: boolean
  correctIndex: number
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  settings: AppSettings
  progressValue: number
  onOptionSelect: (index: number) => void
  onSkip: () => void
  onGoBack: () => void
  onSpellingSubmit: (source?: SpellingSubmitSource) => void
  onSpellingInputChange: (value: string) => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: WordPlaybackHandler
}

export function PracticePageOptionsLayout(props: PracticePageOptionsLayoutProps) {
  const {
    mode,
    currentDay,
    practiceBookId,
    practiceChapterId,
    errorMode,
    vocabulary,
    currentChapterTitle,
    bookChapters,
    showWordList,
    showPracticeSettings,
    onWordListToggle,
    onSettingsToggle,
    onModeChange,
    onDayChange,
    navigate,
    buildChapterPath,
    onExitHome,
    queue,
    queueIndex,
    wordStatuses,
    favoriteSlot,
    speakingSlot,
    wordListActionControls,
    currentWord,
    previousWord,
    lastState,
    smartDimension,
    reviewMode,
    options,
    optionsLoading,
    selectedAnswer,
    wrongSelections,
    showResult,
    correctIndex,
    spellingInput,
    spellingResult,
    speechConnected,
    speechRecording,
    settings,
    progressValue,
    onOptionSelect,
    onSkip,
    onGoBack,
    onSpellingSubmit,
    onSpellingInputChange,
    onStartRecording,
    onStopRecording,
    onPlayWord,
  } = props

  return (
    <div className="practice-session-layout">
      <PracticeControlBar
        mode={mode}
        currentDay={currentDay}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        errorMode={errorMode}
        vocabularyLength={vocabulary.length}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        showPracticeSettings={showPracticeSettings}
        onWordListToggle={onWordListToggle}
        onSettingsToggle={onSettingsToggle}
        onModeChange={onModeChange}
        onDayChange={onDayChange}
        onNavigate={navigate}
        buildChapterPath={buildChapterPath}
        onExitHome={onExitHome}
      />
      <WordListPanel
        show={showWordList}
        vocabulary={vocabulary}
        queue={queue}
        queueIndex={queueIndex}
        wordStatuses={wordStatuses}
        wordActionControls={wordListActionControls}
        onClose={onWordListToggle}
      />
      {showPracticeSettings && (
        <SettingsPanel showSettings={showPracticeSettings} onClose={onSettingsToggle} />
      )}
      <OptionsMode
        currentWord={currentWord}
        previousWord={previousWord}
        lastState={lastState}
        mode={mode as PracticeMode}
        smartDimension={smartDimension}
        errorMode={errorMode}
        reviewMode={reviewMode}
        options={options}
        optionsLoading={optionsLoading}
        selectedAnswer={selectedAnswer}
        wrongSelections={wrongSelections}
        showResult={showResult}
        correctIndex={correctIndex}
        spellingInput={spellingInput}
        spellingResult={spellingResult}
        speechConnected={speechConnected}
        speechRecording={speechRecording}
        settings={settings}
        progressValue={progressValue}
        total={queue.length}
        queueIndex={queueIndex}
        onOptionSelect={onOptionSelect}
        onSkip={onSkip}
        onGoBack={onGoBack}
        onSpellingSubmit={onSpellingSubmit}
        onSpellingInputChange={onSpellingInputChange}
        onStartRecording={onStartRecording}
        onStopRecording={onStopRecording}
        onPlayWord={onPlayWord}
        favoriteSlot={favoriteSlot}
        speakingSlot={speakingSlot}
      />
    </div>
  )
}

interface PracticePageFollowLayoutProps extends SharedModeLayoutProps {
  currentWord: Word
  settings: AppSettings
  speechConnected: boolean
  speechRecording: boolean
  recognizedText: string
  onIndexChange: (index: number) => void
  onCompleteSession: () => Promise<void>
  onStartRecording: () => Promise<void>
  onStopRecording: () => void
  onSessionInteraction: () => Promise<void>
  onPronunciationEvaluated?: Parameters<typeof FollowMode>[0]['onPronunciationEvaluated']
}

export function PracticePageFollowLayout(props: PracticePageFollowLayoutProps) {
  const {
    mode,
    currentDay,
    practiceBookId,
    practiceChapterId,
    errorMode,
    vocabulary,
    currentChapterTitle,
    bookChapters,
    showWordList,
    showPracticeSettings,
    onWordListToggle,
    onSettingsToggle,
    onModeChange,
    onDayChange,
    navigate,
    buildChapterPath,
    onExitHome,
    queue,
    queueIndex,
    wordStatuses,
    favoriteSlot,
    wordListActionControls,
    currentWord,
    settings,
    speechConnected,
    speechRecording,
    recognizedText,
    onIndexChange,
    onCompleteSession,
    onStartRecording,
    onStopRecording,
    onSessionInteraction,
    onPronunciationEvaluated,
  } = props

  return (
    <div className="practice-session-layout practice-session-layout--follow">
      <PracticeControlBar
        mode={mode}
        currentDay={currentDay}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        errorMode={errorMode}
        vocabularyLength={vocabulary.length}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        showPracticeSettings={showPracticeSettings}
        onWordListToggle={onWordListToggle}
        onSettingsToggle={onSettingsToggle}
        onModeChange={onModeChange}
        onDayChange={onDayChange}
        onNavigate={navigate}
        buildChapterPath={buildChapterPath}
        onExitHome={onExitHome}
      />
      <WordListPanel
        show={showWordList}
        vocabulary={vocabulary}
        queue={queue}
        queueIndex={queueIndex}
        wordStatuses={wordStatuses}
        wordActionControls={wordListActionControls}
        onClose={onWordListToggle}
      />
      {showPracticeSettings && (
        <SettingsPanel showSettings={showPracticeSettings} onClose={onSettingsToggle} />
      )}
      <FollowMode
        currentWord={currentWord}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        queueIndex={queueIndex}
        total={queue.length}
        settings={settings}
        speechConnected={speechConnected}
        speechRecording={speechRecording}
        recognizedText={recognizedText}
        favoriteSlot={favoriteSlot}
        onIndexChange={onIndexChange}
        onCompleteSession={onCompleteSession}
        onStartRecording={onStartRecording}
        onStopRecording={onStopRecording}
        onSessionInteraction={onSessionInteraction}
        onPronunciationEvaluated={onPronunciationEvaluated}
      />
    </div>
  )
}
