import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import StatsPage from './StatsPage'

const hooksState = vi.hoisted(() => ({
  learningStats: {
    daily: [],
    books: [],
    modes: [],
    summary: null,
    alltime: null,
    modeBreakdown: [],
    pieChart: [],
    wrongTop10: [],
    historyWrongTop10: [],
    pendingWrongTop10: [],
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
    hooksState.learningStats.daily = []
    hooksState.learningStats.books = []
    hooksState.learningStats.modes = []
    hooksState.learningStats.summary = null
    hooksState.learningStats.alltime = null
    hooksState.learningStats.modeBreakdown = []
    hooksState.learningStats.pieChart = []
    hooksState.learningStats.wrongTop10 = []
    hooksState.learningStats.historyWrongTop10 = []
    hooksState.learningStats.pendingWrongTop10 = []
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
    hooksState.learningStats.modes = ['radio', 'smart', 'unknown']
    hooksState.learningStats.modeBreakdown = [
      {
        mode: 'radio',
        words_studied: 18,
        correct_count: 0,
        wrong_count: 0,
        duration_seconds: 600,
        sessions: 2,
        accuracy: null,
        attempts: 0,
        avg_words_per_session: 9,
      },
      {
        mode: 'smart',
        words_studied: 24,
        correct_count: 18,
        wrong_count: 6,
        duration_seconds: 900,
        sessions: 3,
        accuracy: 75,
        attempts: 24,
        avg_words_per_session: 8,
      },
    ]
    hooksState.learningStats.pieChart = [
      { mode: 'radio', value: 18, sessions: 2 },
      { mode: 'smart', value: 24, sessions: 3 },
    ]
    hooksState.learningStats.historyWrongTop10 = [
      { word: 'alpha', wrong_count: 5, phonetic: '/ˈalfə/', pos: 'n.', meaning_wrong: 5 },
    ]
    hooksState.learningStats.pendingWrongTop10 = [
      { word: 'beta', wrong_count: 3, phonetic: '/ˈbeɪtə/', pos: 'n.', listening_wrong: 3 },
    ]
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
    expect(screen.getByText('今日学习新词')).toBeInTheDocument()
    expect(screen.getByText('今日复习旧词')).toBeInTheDocument()
    expect(screen.getByText('累计学习新词')).toBeInTheDocument()
    expect(screen.getByText('今日触达词数')).toBeInTheDocument()
    expect(
      screen.getByText('今日触达词数').closest('.stats-card')?.querySelector('.stats-card-value')?.textContent,
    ).toBe('25')
    expect(screen.getByText('累计复习旧词')).toBeInTheDocument()
    expect(screen.getByText('总学习时长')).toBeInTheDocument()
    expect(screen.getAllByText('2小时').length).toBeGreaterThan(0)
    expect(screen.getAllByText('随身听').length).toBeGreaterThan(0)
    expect(screen.queryByText('选择模式')).not.toBeInTheDocument()
    expect(screen.getAllByText('怎么算')).toHaveLength(3)
    expect(screen.getByText(/第一次进入速记记忆队列/)).toBeInTheDocument()
    expect(screen.getByText(/今天有复习记录且首次学习时间早于今天/)).toBeInTheDocument()
    expect(screen.getByText(/章节累计明显虚高时，会回退到全局去重口径/)).toBeInTheDocument()
    expect(screen.queryByText('到期待复习词')).not.toBeInTheDocument()
    expect(screen.queryByText('待清错词')).not.toBeInTheDocument()
    expect(screen.queryByText('当前词书剩余')).not.toBeInTheDocument()
    expect(screen.queryByText('当前弱项模式')).not.toBeInTheDocument()
    expect(screen.getByText('连续学习天数')).toBeInTheDocument()
    expect(screen.getByText('统一学习画像')).toBeInTheDocument()
    expect(screen.getByText('按时复习率')).toBeInTheDocument()
    expect(screen.getByText('已到复习点')).toBeInTheDocument()
    expect(screen.getByText('复习库词数')).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'unknown' })).not.toBeInTheDocument()
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
