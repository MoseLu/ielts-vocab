import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HomePage from './HomePage'

const hooksState = vi.hoisted(() => ({
  vocabBooks: {
    books: [
      {
        id: 'book-1',
        title: '测试词书',
        word_count: 100,
        is_paid: false,
      },
    ],
    loading: false,
  },
  allBookProgress: {
    progressMap: {
      'book-1': { current_index: 20 },
    },
    loading: false,
  },
  myBooks: {
    myBookIds: new Set(['book-1']),
    loading: false,
    addBook: vi.fn(),
    removeBook: vi.fn(),
  },
  learningStats: {
    loading: false,
    alltime: null,
    learnerProfile: {
      date: '2026-04-04',
      summary: {
        date: '2026-04-04',
        today_words: 12,
        today_accuracy: 80,
        today_duration_seconds: 900,
        today_sessions: 2,
        streak_days: 4,
        weakest_mode: 'meaning',
        weakest_mode_label: '汉译英',
        weakest_mode_accuracy: 68,
        due_reviews: 6,
        trend_direction: 'stable',
      },
      dimensions: [],
      focus_words: [],
      repeated_topics: [],
      next_actions: [],
      mode_breakdown: [],
      daily_plan: {
        today_content: {
          date: '2026-04-04',
          studied_words: 12,
          duration_seconds: 900,
          sessions: 2,
          latest_activity_title: '完成测试词书第 1 章',
          latest_activity_at: '2026-04-04T09:00:00',
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
        tasks: [
          {
            id: 'due-review',
            kind: 'due-review',
            title: '到期复习',
            description: '还有 6 个到期词需要先回顾。',
            status: 'pending',
            completion_source: null,
            badge: '6 词到期',
            action: {
              kind: 'due-review',
              cta_label: '去复习',
              mode: 'quickmemory',
              book_id: null,
              dimension: null,
            },
          },
          {
            id: 'error-review',
            kind: 'error-review',
            title: '清错词',
            description: '当前没有待清理的错词。',
            status: 'completed',
            completion_source: 'already_clear',
            badge: '已清空',
            action: {
              kind: 'error-review',
              cta_label: '去清错词',
              mode: 'meaning',
              book_id: null,
              dimension: 'meaning',
            },
          },
          {
            id: 'focus-book',
            kind: 'continue-book',
            title: '推进词书',
            description: '继续《测试词书》，还剩 80 词。',
            status: 'completed',
            completion_source: 'completed_today',
            badge: '20% 已完成',
            action: {
              kind: 'continue-book',
              cta_label: '继续词书',
              mode: null,
              book_id: 'book-1',
              dimension: null,
            },
          },
        ],
      },
    },
  },
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useVocabBooks: () => hooksState.vocabBooks,
  useAllBookProgress: () => hooksState.allBookProgress,
  useMyBooks: () => hooksState.myBooks,
  useLearningStats: () => hooksState.learningStats,
}))

vi.mock('../../books/dialogs/PlanModal', () => ({
  default: () => null,
}))

vi.mock('../../books/dialogs/ChapterModal', () => ({
  default: () => null,
}))

describe('HomePage', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1800,
    })

    hooksState.vocabBooks.books = [
      {
        id: 'book-1',
        title: '测试词书',
        word_count: 100,
        is_paid: false,
      },
    ]
    hooksState.vocabBooks.loading = false
    hooksState.allBookProgress.progressMap = { 'book-1': { current_index: 20 } }
    hooksState.allBookProgress.loading = false
    hooksState.myBooks.myBookIds = new Set(['book-1'])
    hooksState.myBooks.loading = false
    hooksState.myBooks.addBook.mockReset()
    hooksState.myBooks.removeBook.mockReset()
    hooksState.learningStats.loading = false
    hooksState.learningStats.learnerProfile.daily_plan.focus_book = {
      book_id: 'book-1',
      title: '测试词书',
      current_index: 20,
      total_words: 100,
      progress_percent: 20,
      remaining_words: 80,
      is_completed: false,
    }
    hooksState.learningStats.learnerProfile.daily_plan.tasks = [
      {
        id: 'due-review',
        kind: 'due-review',
        title: '到期复习',
        description: '还有 6 个到期词需要先回顾。',
        status: 'pending',
        completion_source: null,
        badge: '6 词到期',
        action: {
          kind: 'due-review',
          cta_label: '去复习',
          mode: 'quickmemory',
          book_id: null,
          dimension: null,
        },
      },
      {
        id: 'error-review',
        kind: 'error-review',
        title: '清错词',
        description: '当前没有待清理的错词。',
        status: 'completed',
        completion_source: 'already_clear',
        badge: '已清空',
        action: {
          kind: 'error-review',
          cta_label: '去清错词',
          mode: 'meaning',
          book_id: null,
          dimension: 'meaning',
        },
      },
      {
        id: 'focus-book',
        kind: 'continue-book',
        title: '推进词书',
        description: '继续《测试词书》，还剩 80 词。',
        status: 'completed',
        completion_source: 'completed_today',
        badge: '20% 已完成',
        action: {
          kind: 'continue-book',
          cta_label: '继续词书',
          mode: null,
          book_id: 'book-1',
          dimension: null,
        },
      },
    ]
  })

  it('renders a page loading gate before profile and book data are ready', () => {
    hooksState.vocabBooks.books = []
    hooksState.vocabBooks.loading = true
    hooksState.allBookProgress.progressMap = {}
    hooksState.allBookProgress.loading = true
    hooksState.myBooks.myBookIds = new Set()
    hooksState.myBooks.loading = true
    hooksState.learningStats.loading = true

    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton--books')).not.toBeNull()
    expect(container.querySelectorAll('.page-skeleton-card--book')).toHaveLength(6)
    expect(container.querySelector('.study-center-shell')).toBeNull()
  })

  it('renders a lightweight daily todo homepage and removes the old heavy recommendation blocks', () => {
    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('今日待办')).toBeInTheDocument()
    expect(screen.getByText('到期复习')).toBeInTheDocument()
    expect(screen.getAllByText('清错词').length).toBeGreaterThan(0)
    expect(screen.getByText('推进词书')).toBeInTheDocument()
    expect(screen.getByText('快捷入口')).toBeInTheDocument()
    expect(screen.getByText('你的词书')).toBeInTheDocument()
    expect(screen.getAllByText('测试词书').length).toBeGreaterThan(0)
    expect(screen.getByText('待完成')).toBeInTheDocument()
    expect(screen.getAllByText('已清空').length).toBeGreaterThan(0)
    expect(screen.getByText('今日完成')).toBeInTheDocument()
    expect(screen.getByText('背新词')).toBeInTheDocument()
    expect(screen.getByText('练弱项')).toBeInTheDocument()
    expect(container.querySelectorAll('.study-todo-item')).toHaveLength(3)
    expect(container.querySelectorAll('.study-todo-item.is-completed')).toHaveLength(2)
    expect(container.querySelector('.study-book-progress-fill')).toHaveStyle({ width: '20%' })

    expect(screen.queryByText('今天推荐这样学')).not.toBeInTheDocument()
    expect(screen.queryByText('系统推荐顺序')).not.toBeInTheDocument()
    expect(screen.queryByText('我现在想...')).not.toBeInTheDocument()
    expect(screen.queryByText('系统提醒')).not.toBeInTheDocument()

    const todoPanel = container.querySelector('.study-todo-panel')
    const booksHeading = screen.getByText('你的词书')
    expect(Boolean(todoPanel && (todoPanel.compareDocumentPosition(booksHeading) & Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true)
  })

  it('shows add-book as the third task when no focus book is available', () => {
    hooksState.myBooks.myBookIds = new Set()
    hooksState.learningStats.learnerProfile.daily_plan.focus_book = null
    hooksState.learningStats.learnerProfile.daily_plan.tasks = [
      hooksState.learningStats.learnerProfile.daily_plan.tasks[0],
      hooksState.learningStats.learnerProfile.daily_plan.tasks[1],
      {
        id: 'focus-book',
        kind: 'add-book',
        title: '添加词书',
        description: '先加入一本词书，首页才会生成今天的新词主线。',
        status: 'pending',
        completion_source: null,
        badge: '缺少词书',
        action: {
          kind: 'add-book',
          cta_label: '去选词书',
          mode: null,
          book_id: null,
          dimension: null,
        },
      },
    ]

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('添加词书')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '去选词书' })).toBeInTheDocument()
  })
})
