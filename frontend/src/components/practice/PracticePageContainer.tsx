import { useNavigate, useSearchParams } from 'react-router-dom'
import type { AppSettings, Chapter, PracticeMode, PracticePageProps, Word } from './types'
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
import { usePracticeChapterGroupControls } from '../../composables/practice/page/usePracticeChapterGroupControls'
import { usePracticePageState } from '../../composables/practice/page/usePracticePageState'
import { PracticePageRenderState } from './PracticePageRenderState'
import { readUserId } from '../../features/practice/practiceSessionHelpers'
export type { PracticeMode, Word, AppSettings, Chapter }
function PracticePageContainer({
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
  const reviewModeParam = searchParams.get('mode') ?? ''
  const requestedPracticeMode: PracticeMode = reviewMode ? (['smart', 'listening', 'meaning', 'dictation', 'follow', 'radio', 'quickmemory'].includes(reviewModeParam) ? reviewModeParam as PracticeMode : 'quickmemory') : (mode ?? 'smart')
  const practiceBookId = reviewMode ? (bookId ?? null) : bookId, practiceChapterId = reviewMode ? (chapterId ?? null) : chapterId
  const {
    backendLearnerProfile, bookChapters, chapterGroupStartRef, chapterQueueWordsRef,
    correctCount, correctIndex, currentChapterTitle, errorProgressHydratedRef,
    errorReviewRound, errorRoundResultsRef, favoriteQueueIndex, lastState,
    noListeningPresets, options, optionsWordKey, practiceCoreSetters,
    practiceGroup, previousWord, queue, queueIndex, queueRef,
    quickMemoryReviewQueueResolved, resumeProgress, reviewContext, reviewOffset,
    reviewQueueError, reviewSummary, selectedAnswer, setBackendLearnerProfile,
    setBookChapters, setCorrectCount, setCorrectIndex, setCurrentChapterTitle,
    setErrorReviewRound, setFavoriteQueueIndex, setLastState, setNoListeningPresets,
    setOptions, setOptionsWordKey, setPreviousWord, setQueue, setQuickMemoryReviewQueueResolved,
    setQueueIndex, setResumeProgress, setReviewContext, setReviewOffset,
    setReviewQueueError, setReviewSummary, setSelectedAnswer, setShowPracticeSettings,
    setShowResult, setShowWordList, setSmartDimension, setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked, setSpellingFeedbackSnapshot, setSpellingInput,
    setSpellingResult, setWordStatuses, setWrongCount, setWrongSelections,
    showPracticeSettings, showResult, showWordList, smartDimension,
    spellingFeedbackDismissing, spellingFeedbackLocked, spellingFeedbackSnapshot,
    spellingInput, spellingResult, vocabRef, vocabulary, wordStatuses, wrongCount,
    wrongSelections,
  } = usePracticePageState()
  const resolvedPracticeBookId = reviewMode ? (bookId ?? reviewContext?.book_id ?? null) : bookId, resolvedPracticeChapterId = reviewMode ? (chapterId ?? reviewContext?.chapter_id ?? null) : chapterId
  const { isCustomPracticeScope, practiceMode, handleCustomListeningFallback } = useCustomListeningFallback({
    requestedPracticeMode, currentDay, bookId, chapterId, resolvedPracticeBookId, resolvedPracticeChapterId, reviewMode, errorMode, showToast, onModeChange,
  })

  const {
    settings,
    radioQuickSettings,
    handleRadioSettingChange,
    sessionIdRef, sessionCorrectRef,
    sessionWrongRef,
    correctCountRef,
    wrongCountRef,
    completedSessionDurationSecondsRef,
    wordsLearnedBaselineRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
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
    ...practiceCoreSetters,
    setBookChapters,
    setCurrentChapterTitle,
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
    chapterGroupStartRef,
    chapterQueueWordsRef,
    wordsLearnedBaselineRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
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
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
    uniqueAnsweredRef,
    ...practiceCoreSetters,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    vocabRef,
    queueRef,
    startSpeechRecording,
    stopSpeechRecording,
    speechConnected,
    setReviewOffset,
    setErrorReviewRound,
  })
  const handleContinueChapterGroup = usePracticeChapterGroupControls({
    bookId,
    chapterId,
    practiceGroup,
    vocabulary,
    queueRef,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    correctCountRef,
    wrongCountRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
    completedSessionDurationSecondsRef,
    beginSession,
    ...practiceCoreSetters,
    setSelectedAnswer,
    setWrongSelections,
    setShowResult,
    setSpellingInput,
    setSpellingResult,
    setSpellingFeedbackLocked,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackSnapshot,
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
    handleFollowReadEvaluated,
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
    spellingRetryTimerRef, sessionIdRef,
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

  return (
    <PracticePageRenderState
      {...{
        navigate, currentDay, bookId, chapterId, errorMode, vocabulary,
        currentChapterTitle, bookChapters, showWordList, setShowWordList,
        showPracticeSettings, setShowPracticeSettings, onModeChange, onDayChange,
        buildChapterPath, queue, queueIndex, wordStatuses, settings, radioQuickSettings,
        handleRadioSettingChange, markRadioSessionInteraction, handleRadioProgressChange,
        markFollowSessionInteraction, completeFollowSession, isCurrentSessionActive,
        reviewMode, reviewSummary, reviewOffset, saveWrongWord, handleQuickMemoryRecordChange,
        currentWord, favoriteActive, favoriteBusy, wordListActionControls,
        spellingInput, spellingResult, speechConnected, speechRecording, previousWord,
        lastState, spellingFeedbackLocked, spellingFeedbackDismissing, spellingFeedbackSnapshot,
        handleSpellingInputChange, handleSpellingSubmit, handleSkip, goBack, startRecording,
        stopRecording, playWord, smartDimension, options, choiceOptionsReady,
        selectedAnswer, wrongSelections, showResult, correctIndex, handleOptionSelect,
        handleMeaningRecallSubmit, handleFollowReadEvaluated, handleContinueReview,
        noListeningPresets, reviewQueueError, quickMemoryReviewQueueResolved,
        correctCount, wrongCount, errorReviewRound, practiceGroup,
        chapterQueueWords: chapterQueueWordsRef.current,
      }}
      mode={practiceMode}
      loadingMode={requestedPracticeMode === 'listening' && isCustomPracticeScope && noListeningPresets ? 'meaning' : practiceMode}
      resolvedPracticeBookId={resolvedPracticeBookId}
      resolvedPracticeChapterId={resolvedPracticeChapterId}
      radioIndex={favoriteQueueIndex}
      onFavoriteWordIndexChange={handlePracticeWordIndexChange}
      onFavoriteToggle={handleFavoriteToggle}
      sessionDurationSeconds={completedSessionDurationSecondsRef.current}
      errorRoundResults={errorRoundResultsRef.current}
      onContinueErrorReview={handleContinueErrorReview}
      onContinueChapterGroup={handleContinueChapterGroup}
      resumePromptOpen={resumePromptOpen}
      resumeMessage={resumeMessage}
      resumeContinueLabel={resumeContinueLabel}
      onResumeContinue={handleResumeContinue}
      onResumeRestart={handleResumeRestart}
    />
  )
}
export default PracticePageContainer
