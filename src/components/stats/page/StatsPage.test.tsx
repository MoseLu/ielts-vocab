import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import StatsPage from './StatsPage'

const hooksState = vi.hoisted(() => ({
  wrongWords: {
    words: [],
    loading: false,
  },
  learningStats: {
    daily: [],
    books: [],
    modes: [],
    summary: null,
    alltime: null,
    modeBreakdown: [],
    pieChart: [],
    wrongTop10: [],
    chapterBreakdown: [],
    chapterModeStats: [],
    learnerProfile: null,
    useFallback: false,
    loading: true,
    refreshing: false,
    refetch: vi.fn(),
  },
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useWrongWords: () => hooksState.wrongWords,
  useLearningStats: () => hooksState.learningStats,
}))

describe('StatsPage', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        media: '',
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    class MockResizeObserver {
      observe = vi.fn()
      unobserve = vi.fn()
      disconnect = vi.fn()
    }

    Object.defineProperty(globalThis, 'ResizeObserver', {
      writable: true,
      value: MockResizeObserver,
    })
  })

  beforeEach(() => {
    hooksState.wrongWords.words = []
    hooksState.wrongWords.loading = false
    hooksState.learningStats.daily = []
    hooksState.learningStats.books = []
    hooksState.learningStats.modes = []
    hooksState.learningStats.summary = null
    hooksState.learningStats.alltime = null
    hooksState.learningStats.modeBreakdown = []
    hooksState.learningStats.pieChart = []
    hooksState.learningStats.wrongTop10 = []
    hooksState.learningStats.chapterBreakdown = []
    hooksState.learningStats.chapterModeStats = []
    hooksState.learningStats.learnerProfile = null
    hooksState.learningStats.useFallback = false
    hooksState.learningStats.loading = true
    hooksState.learningStats.refreshing = false
    hooksState.learningStats.refetch.mockReset()
  })

  it('shows a page skeleton before statistics data resolves', () => {
    const { container } = render(
      <MemoryRouter>
        <StatsPage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton--stats')).not.toBeNull()
    expect(container.querySelector('.page-content.stats-page')).not.toBeNull()
  })

  it('renders the statistics dashboard after data resolves', () => {
    hooksState.learningStats.alltime = {
      total_words: 120,
      accuracy: 88,
      duration_seconds: 7200,
      today_accuracy: 92,
      today_duration_seconds: 900,
      today_new_words: 15,
      today_review_words: 10,
      alltime_review_words: 48,
      cumulative_review_events: 60,
      ebbinghaus_rate: 75,
      ebbinghaus_due_total: 20,
      ebbinghaus_met: 15,
      qm_word_total: 160,
      ebbinghaus_stages: [],
      upcoming_reviews_3d: 4,
      streak_days: 6,
      weakest_mode: 'listening',
      weakest_mode_accuracy: 70,
      trend_direction: 'improving',
    }
    hooksState.learningStats.summary = {
      total_words: 40,
      total_duration_seconds: 1200,
      total_sessions: 3,
      accuracy: 90,
    }
    hooksState.learningStats.learnerProfile = {
      date: '2026-03-31',
      summary: {
        date: '2026-03-31',
        today_words: 42,
        today_accuracy: 82,
        today_duration_seconds: 1200,
        today_sessions: 3,
        streak_days: 6,
        weakest_mode: 'listening',
        weakest_mode_label: '听音选义',
        weakest_mode_accuracy: 70,
        due_reviews: 4,
        trend_direction: 'improving',
      },
      dimensions: [
        { dimension: 'meaning', label: '释义拼词（会想）', correct: 12, wrong: 8, attempts: 20, accuracy: 60, weakness: 0.4 },
      ],
      focus_words: [
        { word: 'kind', definition: 'type', wrong_count: 4, dominant_dimension: 'meaning', dominant_dimension_label: '释义拼词（会想）', dominant_wrong: 3, focus_score: 11 },
      ],
      repeated_topics: [
        { title: 'kind of vs a kind of', count: 2, word_context: 'kind', latest_answer: '...', latest_at: null },
      ],
      next_actions: ['优先复习 4 个已到期的速记单词。'],
      mode_breakdown: [],
      daily_plan: {
        tasks: [],
        today_content: {
          date: '2026-03-31',
          studied_words: 42,
          duration_seconds: 1200,
          sessions: 3,
          latest_activity_title: '完成测试词书第 1 章',
          latest_activity_at: '2026-03-31T09:00:00',
        },
        focus_book: {
          book_id: 'book-1',
          title: '测试词书',
          current_index: 20,
          total_words: 100,
          progress_percent: 20,
          remaining_words: 80,
          is_completed: false,
        },
      },
    }
    hooksState.learningStats.loading = false

    const { container } = render(
      <MemoryRouter>
        <StatsPage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton')).toBeNull()
    expect(container.querySelector('.stats-insight-grid .stats-main-card--profile .stats-card-profile')).not.toBeNull()
    expect(container.querySelector('.stats-wrong-cluster')).not.toBeNull()
    expect(container.querySelector('.stats-wrong-cluster-grid .stats-main-card--wrong-history .stats-card-wrong')).not.toBeNull()
    expect(container.querySelector('.stats-wrong-cluster-grid .stats-main-card--wrong-pending .stats-card-wrong')).not.toBeNull()
    expect(screen.getByText('到期待复习词')).toBeInTheDocument()
    expect(screen.getByText('待清错词')).toBeInTheDocument()
    expect(screen.getByText('当前词书剩余')).toBeInTheDocument()
    expect(screen.getByText('今日学习词数')).toBeInTheDocument()
    expect(screen.getByText('当前弱项模式')).toBeInTheDocument()
    expect(screen.getByText('累计学过的不同词')).toBeInTheDocument()
    expect(screen.getAllByText('怎么算')).toHaveLength(3)
    expect(screen.getByText(/优先看今天还剩多少没清掉/)).toBeInTheDocument()
    expect(screen.getByText(/只有连续答对到目标次数才会消掉/)).toBeInTheDocument()
    expect(screen.getByText(/表示做完到期复习和错词清理后/)).toBeInTheDocument()
    expect(screen.getByText('80词')).toBeInTheDocument()
    expect(screen.getByText('连续学习天数')).toBeInTheDocument()
    expect(screen.getByText('统一学习画像')).toBeInTheDocument()
    expect(screen.getByText('按时复习率')).toBeInTheDocument()
    expect(screen.getByText('已到复习点')).toBeInTheDocument()
    expect(screen.getByText('复习库词数')).toBeInTheDocument()
    expect(screen.queryByText('章节正确率（细项）')).not.toBeInTheDocument()
    expect(screen.queryByText('章节 × 模式 正确率')).not.toBeInTheDocument()
    expect(screen.getAllByText('kind').length).toBeGreaterThan(0)
  })

  it('explains zero due counts when no word has reached its review time yet', () => {
    hooksState.learningStats.alltime = {
      total_words: 120,
      accuracy: 88,
      duration_seconds: 7200,
      today_accuracy: 92,
      today_duration_seconds: 900,
      today_new_words: 15,
      today_review_words: 10,
      alltime_review_words: 48,
      cumulative_review_events: 60,
      ebbinghaus_rate: null,
      ebbinghaus_due_total: 0,
      ebbinghaus_met: 0,
      qm_word_total: 1798,
      ebbinghaus_stages: [],
      upcoming_reviews_3d: 0,
      streak_days: 6,
      weakest_mode: 'listening',
      weakest_mode_accuracy: 70,
      trend_direction: 'improving',
    }
    hooksState.learningStats.summary = {
      total_words: 40,
      total_duration_seconds: 1200,
      total_sessions: 3,
      accuracy: 90,
    }
    hooksState.learningStats.loading = false

    render(
      <MemoryRouter>
        <StatsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('当前暂无到点词')).toBeInTheDocument()
    expect(screen.getByText(/当前没有词到达复习点，所以前两项会显示 0/)).toBeInTheDocument()
  })

  it('keeps cached chart sections visible during background refreshes', () => {
    hooksState.learningStats.alltime = {
      total_words: 120,
      accuracy: 88,
      duration_seconds: 7200,
      today_accuracy: 92,
      today_duration_seconds: 900,
      today_new_words: 15,
      today_review_words: 10,
      alltime_review_words: 48,
      cumulative_review_events: 60,
      ebbinghaus_rate: 75,
      ebbinghaus_due_total: 20,
      ebbinghaus_met: 15,
      qm_word_total: 160,
      ebbinghaus_stages: [],
      upcoming_reviews_3d: 4,
      streak_days: 6,
      weakest_mode: 'listening',
      weakest_mode_accuracy: 70,
      trend_direction: 'improving',
    }
    hooksState.learningStats.summary = {
      total_words: 40,
      total_duration_seconds: 1200,
      total_sessions: 3,
      accuracy: 90,
    }
    hooksState.learningStats.loading = false
    hooksState.learningStats.refreshing = true

    const { container } = render(
      <MemoryRouter>
        <StatsPage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton')).toBeNull()
    expect(container.querySelector('.stats-skeleton')).toBeNull()
    expect(screen.getByText('模式占比与各模式统计')).toBeInTheDocument()
    expect(screen.getByText('学习记录')).toBeInTheDocument()
  })
})
