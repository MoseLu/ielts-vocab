import type { ComponentProps } from 'react'
import { PracticeResumeOverlay } from './page/PracticeResumeOverlay'
import { PracticePageContent } from './page/PracticePageContent'
import { PracticePageCompletedState, PracticePageLoadingState } from './page/PracticePageStates'
import type { PracticeMode, Word } from './types'

type ContentProps = ComponentProps<typeof PracticePageContent>
type CompletedProps = ComponentProps<typeof PracticePageCompletedState>

interface PracticePageRenderStateProps extends Omit<ContentProps, 'currentWord' | 'mode'> {
  mode: PracticeMode
  loadingMode: PracticeMode
  currentWord?: Word
  bookId: string | null
  chapterId: string | null
  noListeningPresets: boolean
  reviewQueueError: string | null
  quickMemoryReviewQueueResolved: boolean
  correctCount: number
  wrongCount: number
  errorReviewRound: number
  sessionDurationSeconds: number
  errorRoundResults: CompletedProps['errorRoundResults']
  practiceGroup: CompletedProps['practiceGroup']
  onContinueErrorReview: () => void
  onContinueChapterGroup: () => void
  resumePromptOpen: boolean
  resumeMessage: string
  resumeContinueLabel: string
  onResumeContinue: () => void
  onResumeRestart: () => void
}

export function PracticePageRenderState({
  mode,
  loadingMode,
  currentWord,
  bookId,
  chapterId,
  noListeningPresets,
  reviewQueueError,
  quickMemoryReviewQueueResolved,
  correctCount,
  wrongCount,
  errorReviewRound,
  sessionDurationSeconds,
  errorRoundResults,
  practiceGroup,
  onContinueErrorReview,
  onContinueChapterGroup,
  resumePromptOpen,
  resumeMessage,
  resumeContinueLabel,
  onResumeContinue,
  onResumeRestart,
  ...contentProps
}: PracticePageRenderStateProps) {
  if (!contentProps.vocabulary.length) {
    return (
      <PracticePageLoadingState
        navigate={contentProps.navigate}
        currentDay={contentProps.currentDay}
        bookId={contentProps.resolvedPracticeBookId}
        chapterId={contentProps.resolvedPracticeChapterId}
        errorMode={contentProps.errorMode}
        mode={loadingMode}
        currentChapterTitle={contentProps.currentChapterTitle}
        bookChapters={contentProps.bookChapters}
        buildChapterPath={contentProps.buildChapterPath}
        onModeChange={contentProps.onModeChange}
        onDayChange={contentProps.onDayChange}
        noListeningPresets={noListeningPresets}
        reviewMode={contentProps.reviewMode}
        reviewQueueError={reviewQueueError}
        quickMemoryReviewQueueResolved={quickMemoryReviewQueueResolved}
      />
    )
  }

  if (!currentWord) {
    return (
      <PracticePageCompletedState
        navigate={contentProps.navigate}
        bookId={bookId}
        chapterId={chapterId}
        currentDay={contentProps.currentDay}
        mode={mode}
        correctCount={correctCount}
        wrongCount={wrongCount}
        errorMode={contentProps.errorMode}
        errorReviewRound={errorReviewRound}
        reviewMode={contentProps.reviewMode}
        sessionDurationSeconds={sessionDurationSeconds}
        reviewSummary={contentProps.reviewSummary}
        vocabulary={contentProps.vocabulary}
        errorRoundResults={errorRoundResults}
        onContinueReview={contentProps.handleContinueReview}
        onContinueErrorReview={onContinueErrorReview}
        practiceGroup={practiceGroup}
        onContinueChapterGroup={onContinueChapterGroup}
      />
    )
  }

  return (
    <>
      <PracticePageContent {...contentProps} mode={mode} currentWord={currentWord} />
      <PracticeResumeOverlay
        isOpen={resumePromptOpen}
        message={resumeMessage}
        continueLabel={resumeContinueLabel}
        onContinue={onResumeContinue}
        onRestart={onResumeRestart}
      />
    </>
  )
}
