import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PracticePageCompletedState, PracticePageLoadingState } from './PracticePageStates'

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

    expect(screen.getByText('本轮完成')).toBeInTheDocument()
    expect(screen.getByText('错词复习')).toBeInTheDocument()
    expect(screen.getByText('2分5秒')).toBeInTheDocument()
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

    expect(screen.getByText('本轮完成')).toBeInTheDocument()
    expect(screen.getByText('错词复习')).toBeInTheDocument()
    expect(screen.getByText('2分5秒')).toBeInTheDocument()
  })

  it('shows duration-only summary for follow completion', () => {
    render(
      <PracticePageCompletedState
        navigate={vi.fn()}
        bookId="book-1"
        chapterId="1"
        currentDay={1}
        mode="follow"
        correctCount={8}
        wrongCount={2}
        errorMode={false}
        errorReviewRound={1}
        reviewMode={false}
        sessionDurationSeconds={92}
        reviewSummary={null}
        vocabulary={[]}
        errorRoundResults={{}}
        onContinueReview={() => {}}
        onContinueErrorReview={() => {}}
      />,
    )

    expect(screen.getByText('跟读练习')).toBeInTheDocument()
    expect(screen.getByText('1分32秒')).toBeInTheDocument()
    expect(screen.getByText('跟读模式只记录学习时长，不计入测试正确率、错词或掌握度。')).toBeInTheDocument()
    expect(screen.queryByText('正确率')).not.toBeInTheDocument()
  })
})

describe('PracticePageLoadingState review errors', () => {
  it('shows a visible retry message when due-review loading fails', () => {
    render(
      <PracticePageLoadingState
        navigate={vi.fn()}
        mode="quickmemory"
        noListeningPresets={false}
        reviewMode
        reviewQueueError="加载到期复习失败，请刷新后重试。"
        quickMemoryReviewQueueResolved
      />,
    )

    expect(screen.getByText('到期复习暂时打不开')).toBeInTheDocument()
    expect(screen.getByText('加载到期复习失败，请刷新后重试。')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument()
  })
})
