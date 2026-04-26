import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { HomeTodoItem, HomeTodoResponse } from '../../../lib/schemas/home-todo'
import HomePage from './HomePage'

const helpRegistryState = vi.hoisted(() => ({
  setPlanHelpFaqItems: vi.fn(),
  clearPlanHelpFaqItems: vi.fn(),
}))

const navigationState = vi.hoisted(() => ({
  navigate: vi.fn(),
}))

type TaskOverrides = Omit<Partial<HomeTodoItem>, 'action'> & Pick<HomeTodoItem, 'id' | 'kind' | 'title' | 'description' | 'badge'> & {
  action?: Partial<HomeTodoItem['action']>
}

const makeTask = (overrides: TaskOverrides): HomeTodoItem => ({
  task_key: overrides.id,
  status: 'pending',
  completion_source: null,
  steps: [
    { id: `${overrides.id}-1`, label: '确认任务目标', status: 'current' },
    { id: `${overrides.id}-2`, label: '完成一轮练习', status: 'pending' },
    { id: `${overrides.id}-3`, label: '等待系统自动判定', status: 'pending' },
  ],
  carry_over_count: 0,
  ...overrides,
  action: {
    kind: overrides.action?.kind ?? overrides.kind,
    cta_label: overrides.action?.cta_label ?? '去完成',
    task: overrides.action?.task ?? overrides.kind,
    mode: overrides.action?.mode ?? null,
    book_id: overrides.action?.book_id ?? null,
    chapter_id: overrides.action?.chapter_id ?? null,
    dimension: overrides.action?.dimension ?? null,
  },
})

const makeCompletedTask = (task: HomeTodoItem, completionSource: HomeTodoItem['completion_source']) => ({
  ...task,
  status: 'completed' as const,
  completion_source: completionSource,
  steps: task.steps.map(step => ({ ...step, status: 'completed' as const })),
})

const cloneTasks = (tasks: HomeTodoItem[]) => tasks.map(task => ({
  ...task,
  action: { ...task.action },
  steps: task.steps.map(step => ({ ...step })),
}))

const baseTasks = {
  dueReview: makeTask({
    id: 'due-review',
    kind: 'due-review',
    title: '到期复习',
    description: '还有 6 个到期词需要先回顾。',
    badge: '6 词到期',
    action: { cta_label: '去复习' },
  }),
  errorReview: makeCompletedTask(makeTask({
    id: 'error-review',
    kind: 'error-review',
    title: '清错词',
    description: '当前没有待清理的错词。',
    badge: '已清空',
    action: { cta_label: '去清错词', dimension: 'meaning' },
  }), 'already_clear'),
  continueBook: makeCompletedTask(makeTask({
    id: 'focus-book',
    kind: 'continue-book',
    title: '推进词书',
    description: '继续《测试词书》，还剩 80 词。',
    badge: '20% 已完成',
    action: { cta_label: '继续词书', book_id: 'book-1', chapter_id: '2' },
  }), 'completed_today'),
  speaking: makeTask({
    id: 'speaking',
    kind: 'speaking',
    title: '口语任务',
    description: '完成一次发音检查和一句英文表达。',
    badge: '开始练口语',
    action: { cta_label: '去口语' },
  }),
}

const makeHomeTodoData = (
  primaryItems = cloneTasks([baseTasks.dueReview, baseTasks.continueBook, baseTasks.speaking, baseTasks.errorReview]),
  overflowItems: HomeTodoItem[] = [],
): HomeTodoResponse => ({
  date: '2026-04-04',
  summary: {
    pending_count: primaryItems.filter(task => task.status === 'pending').length,
    completed_count: primaryItems.filter(task => task.status === 'completed').length,
    carry_over_count: 0,
    last_generated_at: '2026-04-04T09:00:00',
  },
  primary_items: primaryItems,
  overflow_items: overflowItems,
})

const hooksState = vi.hoisted(() => {
  return {
    vocabBooks: {
      books: [{ id: 'book-1', title: '测试词书', word_count: 100, is_paid: false }],
      loading: false,
    },
    allBookProgress: {
      progressMap: { 'book-1': { current_index: 20 } },
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
      },
    },
    homeTodos: {
      data: {
        date: '',
        summary: {
          pending_count: 0,
          completed_count: 0,
          carry_over_count: 0,
          last_generated_at: null,
        },
        primary_items: [],
        overflow_items: [],
      },
      primaryItems: [],
      overflowItems: [],
      summary: {
        pending_count: 0,
        completed_count: 0,
        carry_over_count: 0,
        last_generated_at: null,
      },
      loading: false,
      error: null as string | null,
    },
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigationState.navigate,
  }
})

vi.mock('../../../features/vocabulary/hooks', () => ({
  useVocabBooks: () => hooksState.vocabBooks,
  useAllBookProgress: () => hooksState.allBookProgress,
  useMyBooks: () => hooksState.myBooks,
  useLearningStats: () => hooksState.learningStats,
}))

vi.mock('../../../features/home/hooks/useHomeTodos', () => ({
  useHomeTodos: () => hooksState.homeTodos,
}))

vi.mock('../../books/dialogs/PlanModal', () => ({
  default: () => <div data-testid="home-plan-modal" />,
}))

vi.mock('../../books/dialogs/ChapterModal', () => ({
  default: () => <div data-testid="home-chapter-modal" />,
}))

vi.mock('../../layout/navigation/helpContentRegistry', () => ({
  setPlanHelpFaqItems: (...args: unknown[]) => helpRegistryState.setPlanHelpFaqItems(...args),
  clearPlanHelpFaqItems: (...args: unknown[]) => helpRegistryState.clearPlanHelpFaqItems(...args),
}))

function resetHomeTodos(primaryItems?: HomeTodoItem[], overflowItems: HomeTodoItem[] = []) {
  const data = makeHomeTodoData(primaryItems, overflowItems)
  hooksState.homeTodos.data = data
  hooksState.homeTodos.primaryItems = data.primary_items
  hooksState.homeTodos.overflowItems = data.overflow_items
  hooksState.homeTodos.summary = data.summary
  hooksState.homeTodos.loading = false
  hooksState.homeTodos.error = null
}

describe('HomePage', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1800,
    })

    hooksState.vocabBooks.books = [{ id: 'book-1', title: '测试词书', word_count: 100, is_paid: false }]
    hooksState.vocabBooks.loading = false
    hooksState.allBookProgress.progressMap = { 'book-1': { current_index: 20 } }
    hooksState.allBookProgress.loading = false
    hooksState.myBooks.myBookIds = new Set(['book-1'])
    hooksState.myBooks.loading = false
    hooksState.myBooks.addBook.mockReset()
    hooksState.myBooks.removeBook.mockReset()
    hooksState.learningStats.loading = false
    helpRegistryState.setPlanHelpFaqItems.mockReset()
    helpRegistryState.clearPlanHelpFaqItems.mockReset()
    navigationState.navigate.mockReset()
    resetHomeTodos()
  })

  it('renders a page loading gate before profile, book, and todo data are ready', () => {
    hooksState.vocabBooks.books = []
    hooksState.vocabBooks.loading = true
    hooksState.allBookProgress.progressMap = {}
    hooksState.allBookProgress.loading = true
    hooksState.myBooks.myBookIds = new Set()
    hooksState.myBooks.loading = true
    hooksState.learningStats.loading = true
    hooksState.homeTodos.loading = true

    const { container } = render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(container.querySelector('.page-skeleton--books')).not.toBeNull()
    expect(container.querySelectorAll('.page-skeleton-card--book')).toHaveLength(6)
    expect(container.querySelector('.study-center-shell')).toBeNull()
  })

  it('renders the compact homepage from the independent todo API', () => {
    const { container } = render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.queryByText('今日待办')).not.toBeInTheDocument()
    expect(screen.queryByText('指标怎么达成')).not.toBeInTheDocument()
    expect(screen.getByText('到期复习')).toBeInTheDocument()
    expect(screen.getAllByText('清错词').length).toBeGreaterThan(0)
    expect(screen.getByText('推进词书')).toBeInTheDocument()
    expect(screen.getAllByText('测试词书').length).toBeGreaterThan(0)
    expect(screen.getAllByText('待完成').length).toBeGreaterThan(0)
    expect(screen.getAllByText('已清空').length).toBeGreaterThan(0)
    expect(screen.getAllByText('今日完成').length).toBeGreaterThan(0)
    expect(screen.queryByText('今天先处理这 3 件事')).not.toBeInTheDocument()
    expect(screen.queryByText('系统会根据今天的真实学习数据自动勾选，你不用手动处理。')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '管理词书' })).not.toBeInTheDocument()
    expect(screen.getAllByText('当前步骤').length).toBeGreaterThan(0)
    expect(screen.getAllByText('待处理').length).toBeGreaterThan(0)
    expect(screen.getAllByText('已完成').length).toBeGreaterThan(0)
    expect(container.querySelectorAll('.study-guidance-card')).toHaveLength(0)
    expect(screen.getByText('口语任务')).toBeInTheDocument()
    expect(container.querySelectorAll('.study-todo-item')).toHaveLength(4)
    expect(container.querySelectorAll('.study-todo-card-head')).toHaveLength(4)
    expect(container.querySelector('.study-todo-summary')).toBeNull()
    expect(container.querySelectorAll('.study-todo-item.is-completed')).toHaveLength(2)
    expect(container.querySelector('.study-todo-head')).toBeNull()
    expect(container.querySelectorAll('.study-todo-card-head .study-todo-action')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-progress')).toHaveLength(4)
    expect(container.querySelectorAll('.study-todo-progress.is-completed')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-footer')).toHaveLength(0)
    expect(container.querySelectorAll('.study-todo-check[type="checkbox"]')).toHaveLength(4)
    expect(container.querySelectorAll('.study-todo-check[type="checkbox"]:checked')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-step-check[type="checkbox"]')).toHaveLength(12)
    expect(container.querySelectorAll('.study-todo-step-check[type="checkbox"]:checked')).toHaveLength(6)
    expect(container.querySelectorAll('.study-todo-step')).toHaveLength(12)
    expect(container.querySelectorAll('.study-todo-step-state.is-current')).toHaveLength(2)
    expect(container.querySelectorAll('.study-todo-step-state.is-pending')).toHaveLength(4)
    expect(container.querySelectorAll('.study-todo-step-state.is-completed')).toHaveLength(6)
    expect(container.querySelector('.study-book-progress-fill')).toHaveStyle({ '--progress-percent': '20%' })
    expect(helpRegistryState.setPlanHelpFaqItems).toHaveBeenCalledTimes(1)
    expect(helpRegistryState.setPlanHelpFaqItems.mock.calls[0][0]).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ title: '错词怎么减少' }),
        expect.objectContaining({ title: '复习怎样算完成' }),
        expect.objectContaining({ title: '每个维度看什么' }),
        expect.objectContaining({ title: '系统还缺哪一关' }),
      ]),
    )
  })

  it('shows all fixed todo modules without an expand section', () => {
    resetHomeTodos(
      cloneTasks([baseTasks.dueReview, baseTasks.continueBook, baseTasks.speaking]),
      cloneTasks([baseTasks.errorReview]),
    )

    const { container } = render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.queryByRole('button', { name: /展开其余/ })).not.toBeInTheDocument()
    expect(screen.queryByText('收起其余待办')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('其余待办列表')).not.toBeInTheDocument()
    expect(container.querySelectorAll('.study-todo-item')).toHaveLength(4)
    expect(screen.getByText('到期复习')).toBeInTheDocument()
    expect(screen.getByText('推进词书')).toBeInTheDocument()
    expect(screen.getByText('口语任务')).toBeInTheDocument()
    expect(screen.getByText('清错词')).toBeInTheDocument()
  })

  it('routes due review todos into the five-dimension game task', async () => {
    const user = userEvent.setup()
    resetHomeTodos(cloneTasks([baseTasks.dueReview]))

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    await user.click(screen.getByRole('button', { name: '去复习' }))

    expect(navigationState.navigate).toHaveBeenCalledWith('/game?task=due-review')
  })

  it('routes error review todos with the recommended weak dimension', async () => {
    const user = userEvent.setup()
    resetHomeTodos([makeTask({
      id: 'error-review',
      kind: 'error-review',
      title: '清错词',
      description: '优先处理「默写模式」，还有 8 个词未过。',
      badge: '8 个待清',
      action: { cta_label: '去清错词', dimension: 'meaning' },
    })])

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    await user.click(screen.getByRole('button', { name: '去清错词' }))

    expect(navigationState.navigate).toHaveBeenCalledWith('/game?task=error-review&dimension=meaning')
  })

  it('routes continue-book todos with book and chapter scope', async () => {
    const user = userEvent.setup()
    resetHomeTodos([makeTask({
      id: 'focus-book',
      kind: 'continue-book',
      title: '推进词书',
      description: '继续《测试词书》，今天目标 20 个新词。',
      badge: '0/20 今日新词',
      action: { cta_label: '继续词书', book_id: 'book-1', chapter_id: '2' },
    })])

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    await user.click(screen.getByRole('button', { name: '继续词书' }))

    expect(navigationState.navigate).toHaveBeenCalledWith('/game?task=continue-book&book=book-1&chapter=2')
  })

  it('shows an explicit fallback when home todos fail instead of using learner profile tasks', () => {
    resetHomeTodos([])
    hooksState.homeTodos.error = '接口失败'
    ;(hooksState.learningStats.learnerProfile as Record<string, unknown>).daily_plan = {
      tasks: [{ title: '旧画像待办' }],
    }

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.getByRole('status')).toHaveTextContent('待办暂时不可用，先从词书开始。')
    expect(screen.queryByText('旧画像待办')).not.toBeInTheDocument()
  })

  it('renders the book panel first in DOM order', () => {
    const { container } = render(<MemoryRouter><HomePage /></MemoryRouter>)
    const sectionClasses = Array.from(container.querySelectorAll('.study-center-shell > section'))
      .map(section => section.className)

    expect(sectionClasses).toEqual(['study-guide-panel', 'study-todo-panel'])
  })

  it('clears the registered homepage help content on unmount', () => {
    const { unmount } = render(<MemoryRouter><HomePage /></MemoryRouter>)

    unmount()

    expect(helpRegistryState.clearPlanHelpFaqItems).toHaveBeenCalledTimes(1)
  })

  it('shows add-book when no focus book is available', () => {
    hooksState.myBooks.myBookIds = new Set()
    resetHomeTodos(cloneTasks([
      baseTasks.dueReview,
      baseTasks.errorReview,
      makeTask({
        id: 'add-book',
        kind: 'add-book',
        title: '添加词书',
        description: '先加入一本词书，首页才会生成今天的新词主线。',
        badge: '缺少词书',
        action: { cta_label: '去选词书' },
      }),
    ]))

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.getByText('添加词书')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '去选词书' })).toBeInTheDocument()
  })

  it('shows confusable books in groups on the home book card', () => {
    hooksState.vocabBooks.books = [{
      id: 'ielts_confusable_match',
      title: '雅思易混词辨析',
      word_count: 2031,
      group_count: 541,
      is_paid: false,
    }]
    hooksState.allBookProgress.progressMap = { ielts_confusable_match: { current_index: 24 } }
    hooksState.myBooks.myBookIds = new Set(['ielts_confusable_match'])

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.getByText('6 / 541 组')).toBeInTheDocument()
    expect(screen.getByText('剩余 535 组')).toBeInTheDocument()
    expect(screen.queryByText('24 / 2031 词')).toBeNull()
  })

  it('shows purchased books with the purchased badge copy on the home card', () => {
    hooksState.vocabBooks.books = [{ id: 'book-1', title: '测试词书', word_count: 100, is_paid: true }]
    hooksState.myBooks.myBookIds = new Set(['book-1'])

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    expect(screen.getByText('已购')).toBeInTheDocument()
    expect(screen.queryByText('付费')).not.toBeInTheDocument()
  })

  it('opens the chapter modal for custom books instead of the plan modal', async () => {
    const user = userEvent.setup()
    hooksState.vocabBooks.books = [{
      id: 'custom_1',
      title: '我的自定义词书',
      word_count: 60,
      is_paid: false,
      is_custom_book: true,
    }]
    hooksState.myBooks.myBookIds = new Set(['custom_1'])

    render(<MemoryRouter><HomePage /></MemoryRouter>)

    await user.click(screen.getByText('我的自定义词书'))

    expect(screen.getByTestId('home-chapter-modal')).toBeInTheDocument()
    expect(screen.queryByTestId('home-plan-modal')).not.toBeInTheDocument()
  })
})
