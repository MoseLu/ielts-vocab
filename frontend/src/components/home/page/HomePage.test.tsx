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
    alltime: {
      total_words: 120,
      accuracy: 76,
      duration_seconds: 3600,
      today_accuracy: 80,
      today_duration_seconds: 900,
      today_new_words: 12,
      today_review_words: 6,
      alltime_review_words: 30,
      cumulative_review_events: 56,
      ebbinghaus_rate: 33,
      ebbinghaus_due_total: 6,
      ebbinghaus_met: 2,
      qm_word_total: 18,
      ebbinghaus_stages: [],
      upcoming_reviews_3d: 9,
      streak_days: 4,
      weakest_mode: 'meaning',
      weakest_mode_accuracy: 68,
      trend_direction: 'stable',
    },
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
        weakest_mode_label: '默写模式',
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
    hooksState.learningStats.alltime = {
      total_words: 120,
      accuracy: 76,
      duration_seconds: 3600,
      today_accuracy: 80,
      today_duration_seconds: 900,
      today_new_words: 12,
      today_review_words: 6,
      alltime_review_words: 30,
      cumulative_review_events: 56,
      ebbinghaus_rate: 33,
      ebbinghaus_due_total: 6,
      ebbinghaus_met: 2,
      qm_word_total: 18,
      ebbinghaus_stages: [],
      upcoming_reviews_3d: 9,
      streak_days: 4,
      weakest_mode: 'meaning',
      weakest_mode_accuracy: 68,
      trend_direction: 'stable',
    }
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

    expect(screen.queryByText('今日待办')).not.toBeInTheDocument()
    expect(screen.queryByText('指标怎么达成')).not.toBeInTheDocument()
    expect(screen.getByText('错词怎么减少')).toBeInTheDocument()
    expect(screen.getByText('复习怎样算完成')).toBeInTheDocument()
    expect(screen.getByText('每个模式看什么')).toBeInTheDocument()
    expect(screen.getByText('系统还缺哪一关')).toBeInTheDocument()
    expect(screen.getByText('到期复习')).toBeInTheDocument()
    expect(screen.getAllByText('清错词').length).toBeGreaterThan(0)
    expect(screen.getByText('推进词书')).toBeInTheDocument()
    expect(screen.queryByText('快捷入口')).not.toBeInTheDocument()
    expect(screen.queryByText('今天已学')).not.toBeInTheDocument()
    expect(screen.queryByText('学习时长')).not.toBeInTheDocument()
    expect(screen.queryByText('主线词书')).not.toBeInTheDocument()
    expect(screen.queryByText('最近学习')).not.toBeInTheDocument()
    expect(screen.getAllByText('测试词书').length).toBeGreaterThan(0)
    expect(screen.getByText('待完成')).toBeInTheDocument()
    expect(screen.getAllByText('已清空').length).toBeGreaterThan(0)
    expect(screen.getAllByText('今日完成').length).toBeGreaterThan(0)
    expect(screen.queryByText('背新词')).not.toBeInTheDocument()
    expect(screen.queryByText('练弱项')).not.toBeInTheDocument()
    expect(screen.queryByText('今天先处理这 3 件事')).not.toBeInTheDocument()
    expect(screen.queryByText('系统会根据今天的真实学习数据自动勾选，你不用手动处理。')).not.toBeInTheDocument()
    expect(screen.queryByText('你的词书')).not.toBeInTheDocument()
    expect(screen.queryByText('当前在学词书会排在最前，方便直接开始今天的主线。')).not.toBeInTheDocument()
    expect(screen.queryByText('不改待办逻辑，只把常用路径收成一排。')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '管理词书' })).not.toBeInTheDocument()
    expect(screen.getByText('打开速记复习队列，只处理到期这一组。')).toBeInTheDocument()
    expect(screen.getByText('先完成 6 词到期，每个词都要做到能立刻回想释义。')).toBeInTheDocument()
    expect(screen.getByText('完成标准：到期数量归零，回到首页后这一项才会自动勾选。')).toBeInTheDocument()
    expect(screen.getByText('只要某一项还没连续答对 4 次，这一项就还算“没清掉”。')).toBeInTheDocument()
    expect(screen.getByText('频次：1 天 / 1 天 / 4 天 / 7 天 / 14 天 / 30 天')).toBeInTheDocument()
    expect(screen.getByText('同一个词要按 1 天 / 1 天 / 4 天 / 7 天 / 14 天 / 30 天 这 6 轮节奏反复通过，才算把“认识它”这一步走完整。')).toBeInTheDocument()
    expect(screen.getByText('某一章显示这个模式已完成，意思是你已经把这一章在这个模式下完整练过一轮。')).toBeInTheDocument()
    expect(screen.getByText('现在还没有一场专门的“总检查”，去把速记模式、默写模式、听音选义、听写模式这四个模式维度一起复核一遍。')).toBeInTheDocument()
    expect(screen.queryByText(/history_wrong/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/nextReview/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/is_completed/i)).not.toBeInTheDocument()
    expect(screen.getByText('当前步骤')).toBeInTheDocument()
    expect(screen.getAllByText('待处理').length).toBeGreaterThan(0)
    expect(screen.getAllByText('已完成').length).toBeGreaterThan(0)
    expect(container.querySelectorAll('.study-guidance-card')).toHaveLength(4)
    expect(container.querySelectorAll('.study-todo-item')).toHaveLength(3)
    expect(container.querySelectorAll('.study-todo-card-head')).toHaveLength(3)
    expect(container.querySelector('.study-todo-summary')).toBeNull()
    expect(container.querySelectorAll('.study-todo-item.is-completed')).toHaveLength(2)
    expect(container.querySelector('.study-todo-head')).toBeNull()
    expect(container.querySelectorAll('.study-todo-card-head .study-todo-action')).toHaveLength(3)
    expect(container.querySelectorAll('.study-todo-progress')).toHaveLength(3)
    expect(container.querySelectorAll('.study-todo-progress.is-completed')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-footer')).toHaveLength(0)
    expect(container.querySelector('.study-quick-actions-panel')).toBeNull()
    expect(container.querySelectorAll('.study-todo-check[type=\"checkbox\"]')).toHaveLength(3)
    expect(container.querySelectorAll('.study-todo-check[type=\"checkbox\"]:checked')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-step-check[type=\"checkbox\"]')).toHaveLength(9)
    expect(container.querySelectorAll('.study-todo-step-check[type=\"checkbox\"]:checked')).toHaveLength(6)
    expect(container.querySelectorAll('.study-todo-step')).toHaveLength(9)
    expect(container.querySelectorAll('.study-todo-step-state.is-current')).toHaveLength(1)
    expect(container.querySelectorAll('.study-todo-step-state.is-pending')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-step-state.is-completed')).toHaveLength(6)
    expect(container.querySelector('.study-book-progress-fill')).toHaveStyle({ width: '20%' })

    expect(screen.queryByText('今天推荐这样学')).not.toBeInTheDocument()
    expect(screen.queryByText('系统推荐顺序')).not.toBeInTheDocument()
    expect(screen.queryByText('我现在想...')).not.toBeInTheDocument()
    expect(screen.queryByText('系统提醒')).not.toBeInTheDocument()
  })

  it('renders the book panel first in DOM order', () => {
    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    const sectionClasses = Array.from(container.querySelectorAll('.study-center-shell > section')).map(
      section => section.className,
    )

    expect(sectionClasses).toEqual([
      'study-guide-panel',
      'study-guidance-panel',
      'study-todo-panel',
    ])
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

  it('shows confusable books in groups on the home book card', () => {
    hooksState.vocabBooks.books = [
      {
        id: 'ielts_confusable_match',
        title: '雅思易混词辨析',
        word_count: 2031,
        group_count: 541,
        is_paid: false,
      },
    ]
    hooksState.allBookProgress.progressMap = {
      ielts_confusable_match: { current_index: 24 },
    }
    hooksState.myBooks.myBookIds = new Set(['ielts_confusable_match'])
    hooksState.learningStats.learnerProfile.daily_plan.focus_book = {
      book_id: 'ielts_confusable_match',
      title: '雅思易混词辨析',
      current_index: 24,
      total_words: 2031,
      progress_percent: 1,
      remaining_words: 2007,
      is_completed: false,
    }

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('6 / 541 组')).toBeInTheDocument()
    expect(screen.getByText('剩余 535 组')).toBeInTheDocument()
    expect(screen.queryByText('24 / 2031 词')).toBeNull()
  })
})
