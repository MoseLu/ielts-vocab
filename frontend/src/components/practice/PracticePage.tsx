import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type {
  AppSettings,
  Chapter,
  LastState,
  OptionItem,
  PracticeMode,
  PracticePageProps,
  SmartDimension,
  Word,
  WordStatuses,
} from './types'
import { usePracticePageSession } from '../../composables/practice/page/usePracticePageSession'
import { usePracticePageData } from '../../composables/practice/page/usePracticePageData'
import { usePracticePageEffects } from '../../composables/practice/page/usePracticePageEffects'
import { usePracticePageActions } from '../../composables/practice/page/usePracticePageActions'
import { usePracticePageControls } from '../../composables/practice/page/usePracticePageControls'
import { usePracticePageKeyboardShortcuts } from '../../composables/practice/page/usePracticePageKeyboardShortcuts'
import { usePracticePageWordActions } from '../../composables/practice/page/usePracticePageWordActions'
import { PracticePageContent } from './page/PracticePageContent'
import type { ErrorReviewRoundResults } from './errorReviewSession'
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
  const practiceBookId = reviewMode ? (bookId ?? null) : bookId
  const practiceChapterId = reviewMode ? (chapterId ?? null) : chapterId

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
  const [backendLearnerProfile, setBackendLearnerProfile] = useState<unknown>(null)
  const [reviewOffset, setReviewOffset] = useState(0)
  const [reviewSummary, setReviewSummary] = useState<ReviewQueueSummary | null>(null)
  const [reviewContext, setReviewContext] = useState<ReviewQueueContext | null>(null)
  const [quickMemoryReviewQueueResolved, setQuickMemoryReviewQueueResolved] = useState(false)
  const [noListeningPresets, setNoListeningPresets] = useState(false)
  const [errorReviewRound, setErrorReviewRound] = useState(1)
  const [smartDimension, setSmartDimension] = useState<SmartDimension>('meaning')

  const vocabRef = useRef<Word[]>([])
  const queueRef = useRef<number[]>([])
  const errorProgressHydratedRef = useRef(false)
  const errorRoundResultsRef = useRef<ErrorReviewRoundResults>({})
  const spellingRetryTimerRef = useRef<number | null>(null)
  const spellingFeedbackDismissTimerRef = useRef<number | null>(null)

  const {
    settings,
    radioQuickSettings,
    handleRadioSettingChange,
    sessionStartRef,
    sessionIdRef,
    sessionCorrectRef,
    sessionWrongRef,
    correctCountRef,
    wrongCountRef,
    completedSessionDurationSecondsRef,
    sessionLoggedRef,
    effectiveSessionModeRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    sessionUniqueWordsRef,
    beginSession,
    computeChapterWordsLearned,
    registerAnsweredWord,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
  } = usePracticePageSession({
    mode,
    errorMode,
    chapterId,
    practiceBookId,
    practiceChapterId,
    correctCount,
    wrongCount,
  })

  const clearSpellingRetryTimer = useCallback(() => {
    if (spellingRetryTimerRef.current === null) return
    window.clearTimeout(spellingRetryTimerRef.current)
    spellingRetryTimerRef.current = null
  }, [])

  const clearSpellingFeedbackDismissTimer = useCallback(() => {
    if (spellingFeedbackDismissTimerRef.current === null) return
    window.clearTimeout(spellingFeedbackDismissTimerRef.current)
    spellingFeedbackDismissTimerRef.current = null
  }, [])

  const resolvedPracticeBookId = reviewMode ? (bookId ?? reviewContext?.book_id ?? null) : bookId
  const resolvedPracticeChapterId = reviewMode ? (chapterId ?? reviewContext?.chapter_id ?? null) : chapterId

  const handleSpellingInputChange = useCallback((value: string) => {
    if (spellingFeedbackLocked && spellingResult === 'wrong' && !spellingFeedbackDismissing) {
      clearSpellingRetryTimer()
      clearSpellingFeedbackDismissTimer()
      setSpellingFeedbackLocked(false)
      setSpellingFeedbackDismissing(true)
      spellingFeedbackDismissTimerRef.current = window.setTimeout(() => {
        setSpellingResult(current => (current === 'wrong' ? null : current))
        setSpellingFeedbackDismissing(false)
        setSpellingFeedbackSnapshot(null)
        spellingFeedbackDismissTimerRef.current = null
      }, 120)
    }
    setSpellingInput(value)
  }, [
    clearSpellingFeedbackDismissTimer,
    clearSpellingRetryTimer,
    spellingFeedbackDismissing,
    spellingFeedbackLocked,
    spellingResult,
  ])

  useEffect(() => () => {
    clearSpellingRetryTimer()
    clearSpellingFeedbackDismissTimer()
  }, [clearSpellingFeedbackDismissTimer, clearSpellingRetryTimer])

  usePracticePageData({
    user,
    userId,
    currentDay,
    mode,
    bookId,
    chapterId,
    resolvedPracticeBookId,
    resolvedPracticeChapterId,
    reviewMode,
    errorMode,
    searchParams,
    settings,
    navigate,
    showToast,
    vocabulary,
    queue,
    queueIndex,
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
    setBackendLearnerProfile,
    setReviewOffset,
    reviewOffset,
    setReviewSummary,
    setReviewContext,
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
  })
  const currentWord = vocabulary[queue[queueIndex]]

  useEffect(() => {
    const nextIndex = queue.length > 0 ? Math.min(queueIndex, queue.length - 1) : 0
    setFavoriteQueueIndex(nextIndex)
  }, [bookId, chapterId, errorMode, mode, queue.length, queueIndex, reviewMode])

  const { favoriteActive, favoriteBusy, handleFavoriteToggle, wordListActionControls } = usePracticePageWordActions({
    userId, mode, vocabulary, queue, queueIndex, favoriteQueueIndex, currentWord,
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
    mode,
    smartDimension,
    setSmartDimension,
    vocabulary,
    queue,
    queueIndex,
    currentWord,
    settings,
    backendLearnerProfile: backendLearnerProfile as never,
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
    startRecording,
    stopRecording,
    playWord,
    handleContinueReview,
    buildChapterPath,
    handleContinueErrorReview,
  } = usePracticePageControls({
    mode,
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
    mode,
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
    sessionStartRef,
    sessionIdRef,
    sessionLoggedRef,
    completedSessionDurationSecondsRef,
    sessionUniqueWordsRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    effectiveSessionModeRef,
    errorRoundResultsRef,
  })

  usePracticePageKeyboardShortcuts({
    mode,
    smartDimension,
    choiceOptionsReady,
    showWordList,
    showPracticeSettings,
    showResult,
    spellingResult,
    currentWord,
    optionsLength: options.length,
    settings,
    playWord,
    handleOptionSelect,
    handleSkip,
    handleGoBack: goBack,
    handleFavoriteToggle: handleFavoriteToggle,
    onExitHome: () => navigate('/plan'),
  })

  if (!vocabulary.length) {
    return (
      <PracticePageLoadingState
        navigate={navigate}
        mode={mode}
        noListeningPresets={noListeningPresets}
        reviewMode={reviewMode}
        quickMemoryReviewQueueResolved={quickMemoryReviewQueueResolved}
      />
    )
  }

  if (!currentWord) {
    return (
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
        vocabulary={vocabulary}
        errorRoundResults={errorRoundResultsRef.current}
        onContinueReview={handleContinueReview}
        onContinueErrorReview={handleContinueErrorReview}
      />
    )
  }

  return (
    <PracticePageContent
      mode={mode}
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
      reviewMode={reviewMode}
      reviewSummary={reviewSummary}
      reviewOffset={reviewOffset}
      saveWrongWord={saveWrongWord}
      handleQuickMemoryRecordChange={handleQuickMemoryRecordChange}
      currentWord={currentWord}
      favoriteActive={favoriteActive}
      favoriteBusy={favoriteBusy}
      onFavoriteWordIndexChange={setFavoriteQueueIndex}
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
  )
}
export default PracticePage
