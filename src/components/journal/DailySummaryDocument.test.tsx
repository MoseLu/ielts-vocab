import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DailySummaryDocument from './DailySummaryDocument'

vi.mock('../../lib/journalMarkdown', () => ({
  renderJournalMarkdown: vi.fn(() => '<p>mock html</p>'),
}))

describe('DailySummaryDocument', () => {
  it('shows a document skeleton while the summary is loading', () => {
    const { container } = render(
      <DailySummaryDocument
        summary={null}
        learnerProfile={null}
        learnerProfileLoading={false}
        summaryLoading
        summaryError=""
        summaryProgress={null}
        formatDateTime={() => '2026-03-30 12:00'}
      />,
    )

    expect(container.querySelector('.journal-doc-skeleton')).not.toBeNull()
    expect(container.textContent).not.toContain('加载中')
  })

  it('renders learner profile insights above the markdown summary body', () => {
    render(
      <DailySummaryDocument
        summary={{
          id: 1,
          date: '2026-03-30',
          content: '# Summary',
          generated_at: '2026-03-30T12:00:00',
        }}
        learnerProfile={{
          date: '2026-03-30',
          summary: {
            date: '2026-03-30',
            today_words: 32,
            today_accuracy: 84,
            today_duration_seconds: 1500,
            today_sessions: 3,
            streak_days: 7,
            weakest_mode: 'meaning',
            weakest_mode_label: '词义辨析',
            weakest_mode_accuracy: 68,
            due_reviews: 5,
            trend_direction: 'improving',
          },
          dimensions: [
            {
              dimension: 'meaning',
              label: '词义辨析',
              correct: 9,
              wrong: 5,
              attempts: 14,
              accuracy: 64,
              weakness: 0.3571,
            },
          ],
          focus_words: [
            {
              word: 'kind',
              definition: 'type',
              wrong_count: 3,
              dominant_dimension: 'meaning',
              dominant_dimension_label: '词义辨析',
              dominant_wrong: 2,
              focus_score: 8,
            },
          ],
          repeated_topics: [
            {
              title: 'kind of vs a kind of',
              count: 2,
              word_context: 'kind',
              latest_answer: '...',
              latest_at: '2026-03-30T12:00:00',
            },
          ],
          next_actions: ['优先复习 5 个已到期的速记单词。'],
          mode_breakdown: [],
        }}
        learnerProfileLoading={false}
        summaryLoading={false}
        summaryError=""
        summaryProgress={null}
        formatDateTime={() => '2026-03-30 12:00'}
      />,
    )

    expect(screen.getByText('统一学习画像')).toBeInTheDocument()
    expect(screen.getByText('kind of vs a kind of')).toBeInTheDocument()
    expect(screen.getByText('优先复习 5 个已到期的速记单词。')).toBeInTheDocument()
  })
})
