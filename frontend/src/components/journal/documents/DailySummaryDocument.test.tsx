import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DailySummaryDocument from './DailySummaryDocument'

vi.mock('../../../lib/journalMarkdown', () => ({
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
            weakest_mode_label: '默写模式',
            weakest_mode_accuracy: 68,
            due_reviews: 5,
            trend_direction: 'improving',
          },
          dimensions: [
            {
              dimension: 'meaning',
              label: '默写模式',
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
              dominant_dimension_label: '默写模式',
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
          activity_summary: {
            total_events: 5,
            study_sessions: 2,
            quick_memory_reviews: 1,
            wrong_word_records: 1,
            assistant_questions: 1,
            chapter_updates: 0,
            books_touched: 1,
            chapters_touched: 2,
            words_touched: 4,
            total_duration_seconds: 1500,
            correct_count: 18,
            wrong_count: 4,
          },
          activity_source_breakdown: [
            {
              source: 'practice',
              label: '练习会话',
              count: 2,
            },
            {
              source: 'assistant',
              label: 'AI 助手',
              count: 1,
            },
          ],
          recent_activity: [
            {
              id: 101,
              event_type: 'study_session',
              label: '练习会话',
              source: 'practice',
              source_label: '练习会话',
              mode: 'smart',
              mode_label: '智能练习',
              book_id: 'book-1',
              chapter_id: '2',
              word: null,
              item_count: 12,
              correct_count: 10,
              wrong_count: 2,
              duration_seconds: 780,
              occurred_at: '2026-03-30T09:18:00',
              title: '智能练习 第2章',
              payload: {},
            },
            {
              id: 102,
              event_type: 'assistant_question',
              label: '助手问答',
              source: 'assistant',
              source_label: 'AI 助手',
              mode: null,
              mode_label: '',
              book_id: null,
              chapter_id: null,
              word: null,
              item_count: 0,
              correct_count: 0,
              wrong_count: 0,
              duration_seconds: 0,
              occurred_at: '2026-03-30T10:05:00',
              title: '向助手提问：kind of 和 a kind of 区别',
              payload: {},
            },
          ],
        }}
        learnerProfileLoading={false}
        summaryLoading={false}
        summaryError=""
        summaryProgress={null}
        formatDateTime={() => '2026-03-30 12:00'}
      />,
    )

    expect(screen.getByText('统一学习画像')).toBeInTheDocument()
    expect(screen.getByText('今日行为流')).toBeInTheDocument()
    expect(screen.getByText('今日共追踪 5 条学习动作，覆盖 1 本词书、2 个章节、4 个单词，累计 25分钟，动作口径答题正确率 82%。')).toBeInTheDocument()
    expect(screen.getByText('智能模式 第2章')).toBeInTheDocument()
    expect(screen.getByText('kind of vs a kind of')).toBeInTheDocument()
    expect(screen.getByText('优先复习 5 个已到期的速记单词。')).toBeInTheDocument()
  })
})
