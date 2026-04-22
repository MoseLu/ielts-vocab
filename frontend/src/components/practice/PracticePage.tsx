import { useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { AppSettings, Chapter, LastState, OptionItem, PracticeMode, PracticePageProps, ProgressData, SmartDimension, Word, WordStatuses } from './types'
import { usePracticePageSession } from '../../composables/practice/page/usePracticePageSession'
import { usePracticePageData } from '../../composables/practice/page/usePracticePageData'
import { usePracticePageEffects } from '../../composables/practice/page/usePracticePageEffects'
import { usePracticePageActions } from '../../composables/practice/page/usePracticePageActions'
import { usePracticePageControls } from '../../composables/practice/page/usePracticePageControls'
import { usePracticePageKeyboardShortcuts } from '../../composables/practice/page/usePracticePageKeyboardShortcuts'
import { usePracticeResumePrompt } from '../../composables/practice/page/usePracticeResumePrompt'
import { usePracticeSpellingFeedback } from '../../composables/practice/page/usePracticeSpellingFeedback'
import { usePracticePageWordActions } from '../../composables/practice/page/usePracticePageWordActions'
import { useCustomListeningFallback } from '../../composables/practice/page/useCustomListeningFallback'
import { PracticePageContent } from './page/PracticePageContent'
import type { ErrorReviewRoundResults } from './errorReviewSession'
import { PracticeResumeOverlay } from './page/PracticeResumeOverlay'
import { PracticePageCompletedState, PracticePageLoadingState } from './page/PracticePageStates'
import { readUserId, type ReviewQueueContext, type ReviewQueueSummary } from './page/practicePageHelpers'
export type { PracticeMode, Word, AppSettings, Chapter }
function PracticePage({
  user,
  currentDay,
  mode,
  showToast,
  onModeChange,
  onDayChange,
}: PracticePageProps) {
  const navigate = useNavigate()
  const userId = readUserId(user)
  const [searchParams] = useSearchParams()
  const bookId = searchParams.get('book')
  const chapterId = searchParams.get('chapter')
  const errorMode = searchParams.get('mode') === 'errors'
  const reviewMode = searchParams.get('review') === 'due'
  const requestedPracticeMode: PracticeMode = reviewMode ? 'quickmemory' : (mode ?? 'smart')
  const practiceBookId = reviewMode ? (bookId ?? null) : bookId, practiceChapterId = reviewMode ? (chapterId ?? null) : chapterId
  const [vocabulary, setVocabulary] = useState<Word[]>([])
  const [queue, setQueue] = useState<number[]>([])
  const [queueIndex, setQueueIndex] = useState(0)
  const [options, setOptions] = useState<OptionItem[]>([])
  const [optionsWordKey, setOptionsWordKey] = useState<string | null>(null)
  const [correctIndex, setCorrectIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)
  const [wrongSelections, setWrongSelections] = useState<number[]>([])
  const [showResult, setShowResult] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [previousWord, setPreviousWord] = useState<Word | null>(null)
  const [lastState, setLastState] = useState<LastState | null>(null)
  const [spellingInput, setSpellingInput] = useState('')
  const [spellingResult, setSpellingResult] = useState<'correct' | 'wrong' | null>(null)
  const [spellingFeedbackLocked, setSpellingFeedbackLocked] = useState(false)
  const [spellingFeedbackDismissing, setSpellingFeedbackDismissing] = useState(false)
  const [spellingFeedbackSnapshot, setSpellingFeedbackSnapshot] = useState<string | null>(null)
  const [favoriteQueueIndex, setFavoriteQueueIndex] = useState(0)
  const [showWordList, setShowWordList] = useState(false)
  const [showPracticeSettings, setShowPracticeSettings] = useState(false)
  const [bookChapters, setBookChapters] = useState<Chapter[]>([])
  const [currentChapterTitle, setCurrentChapterTitle] = useState('')
  const [wordStatuses, setWordStatuses] = useState<WordStatuses>({})
  const [resumeProgress, setResumeProgress] = useState<ProgressData | null>(null)
  const [backendLearnerProfile, setBackendLearnerProfile] = useState<unknown>(null)
  const [reviewOffset, setReviewOffset] = useState(0)
  const [reviewSummary, setReviewSummary] = useState<ReviewQueueSummary | null>(null)
  const [reviewContext, setReviewContext] = useState<ReviewQueueContext | null>(null)
  const [reviewQueueError, setReviewQueueError] = useState<string | null>(null)
  const [quickMemoryReviewQueueResolved, setQuickMemoryReviewQueueResolved] = useState(false), [noListeningPresets, setNoListeningPresets] = useState(false)
  const [errorReviewRound, setErrorReviewRound] = useState(1)
  const [smartDimension, setSmartDimension] = useState<SmartDimension>('meaning')
  const vocabRef = useRef<Word[]>([]), queueRef = useRef<number[]>([])
  const errorProgressHydratedRef = useRef(false), errorRoundResultsRef = useRef<ErrorReviewRoundResults>({})
  const resolvedPracticeBookId = reviewMode ? (bookId ?? reviewContext?.book_id ?? null) : bookId, resolvedPracticeChapterId = reviewMode ? (chapterId ?? reviewContext?.chapter_id ?? null) : chapterId
  const { isCustomPracticeScope, practiceMode, handleCustomListeningFallback } = useCustomListeningFallback({
    requestedPracticeMode, currentDay, bookId, chapterId, resolvedPracticeBookId, resolvedPracticeChapterId, reviewMode, errorMode, showToast, onModeChange,
  })

  const {
    settings,
    radioQuickSettings,
    handleRadioSettingChange,
    sessionCorrectRef,
    sessionWrongRef,
    correctCountRef,
    wrongCountRef,
    completedSessionDurationSecondsRef,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    beginSession,
    prepareSessionForLearningAction,
    completeCurrentSession,
    computeChapterWordsLearned,
    registerAnsweredWord,
    markFollowSessionInteraction,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
    isCurrentSessionActive,
  } = usePracticePageSession({
    mode: practiceMode,
    errorMode,
    chapterId,
    practiceBookId,
    practiceChapterId,
    correctCount,
    wrongCount,
  })

  const {
    clearSpellingRetryTimer,
    clearSpellingFeedbackDismissTimer,
    handleSpellingInputChange,
    spellingRetryTimerRef,
  } = usePracticeSpellingFeedback({
    spellingFeedbackLocked,
    spellingFeedbackDismissing,
    spellingResult,
    setSpellingInput,
    setSpellingResult,
    setSpellingFeedbackLocked,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackSnapshot,
  })

  usePracticePageData({
    userId,
    currentDay,
    mode: practiceMode,
    bookId,
    chapterId,
    resolvedPracticeBookId,
    resolvedPracticeChapterId,
    reviewMode,
    errorMode,
    isCustomPracticeScope,
    searchParamsKey: searchParams.toString(),
    settings,
    navigate,
    showToast,
    setVocabulary,
    setQueue,
    setQueueIndex,
    setCorrectCount,
    setWrongCount,
    setPreviousWord,
    setLastState,
    setBookChapters,
    setCurrentChapterTitle,
    setWordStatuses,
    setResumeProgress,
    setBackendLearnerProfile,
    setReviewOffset,
    reviewOffset,
    setReviewSummary,
    setReviewContext,
    setReviewQueueError,
    setQuickMemoryReviewQueueResolved,
    setNoListeningPresets,
    setErrorReviewRound,
    vocabRef,
    queueRef,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    beginSession,
    onListeningModeFallback: handleCustomListeningFallback,
  })
  const currentWord = vocabulary[queue[queueIndex]]

  const { favoriteActive, favoriteBusy, handleFavoriteToggle, wordListActionControls } = usePracticePageWordActions({
    userId, mode: practiceMode, vocabulary, queue, queueIndex, favoriteQueueIndex, currentWord,
    practiceBookId: resolvedPracticeBookId,
    practiceChapterId: resolvedPracticeChapterId,
    currentChapterTitle,
    showToast,
  })

  const {
    speechConnected,
    speechRecording,
    startSpeechRecording,
    stopSpeechRecording,
    choiceOptionsReady,
  } = usePracticePageEffects({
    userId,
    mode: practiceMode,
    smartDimension,
    setSmartDimension,
    vocabulary,
    queue,
    queueIndex,
    currentWord,
    optionsCount: options.length,
    settings, backendLearnerProfile: backendLearnerProfile as never,
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
  })

  const {
    saveProgress,
    resetChapterProgress,
    startRecording,
    stopRecording,
    playWord,
    handleContinueReview,
    buildChapterPath,
    handleContinueErrorReview,
  } = usePracticePageControls({
    mode: practiceMode,
    currentDay,
    userId,
    bookId,
    chapterId,
    reviewMode,
    errorMode,
    queue,
    queueIndex,
    vocabulary,
    correctCount,
    wrongCount,
    errorReviewRound,
    settings,
    practiceBookId: resolvedPracticeBookId,
    reviewSummary,
    navigate,
    showToast,
    beginSession,
    computeChapterWordsLearned,
    correctCountRef,
    wrongCountRef,
    uniqueAnsweredRef,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    vocabRef,
    queueRef,
    startSpeechRecording,
    stopSpeechRecording,
    speechConnected,
    setVocabulary,
    setQueue,
    setQueueIndex,
    setCorrectCount,
    setWrongCount,
    setPreviousWord,
    setLastState,
    setWordStatuses,
    setReviewOffset,
    setErrorReviewRound,
  })
  const completeFollowSession = async () => { completedSessionDurationSecondsRef.current = await completeCurrentSession() }
  const {
    handlePracticeWordIndexChange,
    handleResumeContinue,
    handleResumeRestart,
    resumeContinueLabel,
    resumeMessage,
    resumePromptOpen,
  } = usePracticeResumePrompt({
    practiceMode,
    bookId,
    chapterId,
    reviewMode,
    errorMode,
    vocabulary,
    queue,
    queueIndex,
    correctCount,
    wrongCount,
    saveProgress,
    resumeProgress,
    setResumeProgress,
    resetChapterProgress,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    setFavoriteQueueIndex,
    setQueueIndex,
    setCorrectCount,
    setWrongCount,
    setPreviousWord,
    setLastState,
    setWordStatuses,
    setSelectedAnswer,
    setWrongSelections,
    setShowResult,
    setSpellingInput,
    setSpellingResult,
    setSpellingFeedbackLocked,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackSnapshot,
  })

  const {
    saveWrongWord,
    handleQuickMemoryRecordChange,
    goBack,
    handleOptionSelect,
    handleSpellingSubmit,
    handleMeaningRecallSubmit,
    handleSkip,
  } = usePracticePageActions({
    user,
    userId,
    mode: practiceMode,
    smartDimension,
    bookId,
    chapterId,
    currentDay,
    currentWord,
    queue,
    queueIndex,
    vocabulary,
    correctCount,
    wrongCount,
    correctIndex,
    options,
    wrongSelections,
    choiceOptionsReady,
    showResult,
    spellingInput,
    spellingResult,
    errorMode,
    errorReviewRound,
    settings,
    navigate,
    showToast,
    playWord,
    saveProgress,
    clearSpellingRetryTimer,
    clearSpellingFeedbackDismissTimer,
    prepareSessionForLearningAction,
    completeCurrentSession,
    registerAnsweredWord,
    syncCurrentSessionSnapshot,
    lastState,
    setLastState,
    setPreviousWord,
    previousWord,
    setSelectedAnswer,
    setWrongSelections,
    setShowResult,
    setSpellingInput,
    setSpellingResult,
    setSpellingFeedbackLocked,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackSnapshot,
    setQueue,
    setQueueIndex,
    setCorrectCount,
    setWrongCount,
    setWordStatuses,
    spellingRetryTimerRef,
    sessionCorrectRef,
    sessionWrongRef,
    completedSessionDurationSecondsRef,
    errorRoundResultsRef,
  })

  usePracticePageKeyboardShortcuts({
    mode: practiceMode, smartDimension, choiceOptionsReady, showWordList, showPracticeSettings, showResult, spellingResult,
    currentWord, optionsLength: options.length, settings, playWord, handleOptionSelect, handleSkip,
    handleGoBack: goBack, handleFavoriteToggle, onExitHome: () => navigate('/plan'),
  })

  if (!vocabulary.length) return (
    <PracticePageLoadingState
      navigate={navigate}
      mode={requestedPracticeMode === 'listening' && isCustomPracticeScope && noListeningPresets ? 'meaning' : practiceMode}
      noListeningPresets={noListeningPresets}
      reviewMode={reviewMode}
      reviewQueueError={reviewQueueError}
      quickMemoryReviewQueueResolved={quickMemoryReviewQueueResolved}
    />
  )

  if (!currentWord) return (
    <PracticePageCompletedState
      navigate={navigate}
      bookId={bookId}
      chapterId={chapterId}
      currentDay={currentDay}
      correctCount={correctCount}
      wrongCount={wrongCount}
      errorMode={errorMode}
      errorReviewRound={errorReviewRound}
      reviewMode={reviewMode}
      sessionDurationSeconds={completedSessionDurationSecondsRef.current}
      reviewSummary={reviewSummary}
      mode={practiceMode}
      vocabulary={vocabulary}
      errorRoundResults={errorRoundResultsRef.current}
      onContinueReview={handleContinueReview}
      onContinueErrorReview={handleContinueErrorReview}
    />
  )

  return (
    <>
      <PracticePageContent
        mode={practiceMode}
        currentDay={currentDay}
        resolvedPracticeBookId={resolvedPracticeBookId}
        resolvedPracticeChapterId={resolvedPracticeChapterId}
        errorMode={errorMode}
        vocabulary={vocabulary}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        setShowWordList={setShowWordList}
        showPracticeSettings={showPracticeSettings}
        setShowPracticeSettings={setShowPracticeSettings}
        onModeChange={onModeChange}
        onDayChange={onDayChange}
        navigate={navigate}
        buildChapterPath={buildChapterPath}
        queue={queue}
        queueIndex={queueIndex}
        radioIndex={favoriteQueueIndex}
        wordStatuses={wordStatuses}
        settings={settings}
        radioQuickSettings={radioQuickSettings}
        handleRadioSettingChange={handleRadioSettingChange}
        markRadioSessionInteraction={markRadioSessionInteraction}
        handleRadioProgressChange={handleRadioProgressChange}
        markFollowSessionInteraction={markFollowSessionInteraction}
        completeFollowSession={completeFollowSession}
        isCurrentSessionActive={isCurrentSessionActive}
        reviewMode={reviewMode}
        reviewSummary={reviewSummary}
        reviewOffset={reviewOffset}
        saveWrongWord={saveWrongWord}
        handleQuickMemoryRecordChange={handleQuickMemoryRecordChange}
        currentWord={currentWord}
        favoriteActive={favoriteActive}
        favoriteBusy={favoriteBusy}
        onFavoriteWordIndexChange={handlePracticeWordIndexChange}
        onFavoriteToggle={handleFavoriteToggle}
        wordListActionControls={wordListActionControls}
        spellingInput={spellingInput}
        spellingResult={spellingResult}
        speechConnected={speechConnected}
        speechRecording={speechRecording}
        previousWord={previousWord}
        lastState={lastState}
        spellingFeedbackLocked={spellingFeedbackLocked}
        spellingFeedbackDismissing={spellingFeedbackDismissing}
        spellingFeedbackSnapshot={spellingFeedbackSnapshot}
        handleSpellingInputChange={handleSpellingInputChange}
        handleSpellingSubmit={handleSpellingSubmit}
        handleSkip={handleSkip}
        goBack={goBack}
        startRecording={startRecording}
        stopRecording={stopRecording}
        playWord={playWord}
        smartDimension={smartDimension}
        options={options}
        choiceOptionsReady={choiceOptionsReady}
        selectedAnswer={selectedAnswer}
        wrongSelections={wrongSelections}
        showResult={showResult}
        correctIndex={correctIndex}
        handleOptionSelect={handleOptionSelect}
        handleMeaningRecallSubmit={handleMeaningRecallSubmit}
        handleContinueReview={handleContinueReview}
      />
      <PracticeResumeOverlay
        isOpen={resumePromptOpen}
        message={resumeMessage}
        continueLabel={resumeContinueLabel}
        onContinue={handleResumeContinue}
        onRestart={handleResumeRestart}
      />
    </>
  )
}
export default PracticePage
