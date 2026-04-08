import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PracticePageCompletedState } from './PracticePageStates'

describe('PracticePageCompletedState session duration', () => {
  it('shows session duration for chapter-scoped error review completion', () => {
    render(
      <PracticePageCompletedState
        navigate={vi.fn()}
        bookId="book-1"
        chapterId="1"
        currentDay={1}
        correctCount={8}
        wrongCount={2}
        errorMode
        errorReviewRound={2}
        reviewMode={false}
        sessionDurationSeconds={125}
        reviewSummary={null}
        vocabulary={[]}
        errorRoundResults={{}}
        onContinueReview={() => {}}
        onContinueErrorReview={() => {}}
      />,
    )

    expect(screen.getByText('错词复习完成')).toBeInTheDocument()
    expect(screen.getByText(/本次用时 2分5秒/)).toBeInTheDocument()
  })

  it('shows session duration for non-chapter error review completion', () => {
    render(
      <PracticePageCompletedState
        navigate={vi.fn()}
        bookId={null}
        chapterId={null}
        currentDay={1}
        correctCount={8}
        wrongCount={2}
        errorMode
        errorReviewRound={2}
        reviewMode={false}
        sessionDurationSeconds={125}
        reviewSummary={null}
        vocabulary={[]}
        errorRoundResults={{}}
        onContinueReview={() => {}}
        onContinueErrorReview={() => {}}
      />,
    )

    expect(screen.getByText('错词复习完成')).toBeInTheDocument()
    expect(screen.getByText(/本次用时 2分5秒/)).toBeInTheDocument()
  })
})
