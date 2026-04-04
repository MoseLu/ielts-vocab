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
  wrongWords: {
    words: [],
  },
  learningStats: {
    alltime: {
      ebbinghaus_due_total: 0,
      streak_days: 4,
      weakest_mode: 'meaning',
      weakest_mode_accuracy: 68,
    },
    learnerProfile: {
      summary: {
        due_reviews: 0,
        streak_days: 4,
        weakest_mode: 'meaning',
        weakest_mode_label: '汉译英',
      },
      next_actions: ['主线任务已清空，可以做一轮专项巩固。'],
    },
  },
}))

vi.mock('../features/vocabulary/hooks', () => ({
  useVocabBooks: () => hooksState.vocabBooks,
  useAllBookProgress: () => hooksState.allBookProgress,
  useMyBooks: () => hooksState.myBooks,
  useWrongWords: () => hooksState.wrongWords,
  useLearningStats: () => hooksState.learningStats,
}))

vi.mock('./PlanModal', () => ({
  default: () => null,
}))

vi.mock('./ChapterModal', () => ({
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
    hooksState.wrongWords.words = []
    hooksState.learningStats.alltime = {
      ebbinghaus_due_total: 0,
      streak_days: 4,
      weakest_mode: 'meaning',
      weakest_mode_accuracy: 68,
    }
    hooksState.learningStats.learnerProfile = {
      summary: {
        due_reviews: 0,
        streak_days: 4,
        weakest_mode: 'meaning',
        weakest_mode_label: '汉译英',
      },
      next_actions: ['主线任务已清空，可以做一轮专项巩固。'],
    }
  })

  it('renders a page loading gate before book data is ready', () => {
    hooksState.vocabBooks.books = []
    hooksState.vocabBooks.loading = true
    hooksState.allBookProgress.progressMap = {}
    hooksState.allBookProgress.loading = true
    hooksState.myBooks.myBookIds = new Set()
    hooksState.myBooks.loading = true

    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton--books')).not.toBeNull()
    expect(container.querySelectorAll('.page-skeleton-card--book')).toHaveLength(6)
    expect(container.querySelector('.study-center-shell')).toBeNull()
  })

  it('renders a guided homepage with a primary next-step CTA and book progress', () => {
    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('今天推荐这样学')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '继续当前词书' })).toBeInTheDocument()
    expect(screen.getByText('系统推荐顺序')).toBeInTheDocument()
    expect(screen.getByText('我现在想...')).toBeInTheDocument()
    expect(screen.getByText('先背新词')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '我想自己选' })).toBeInTheDocument()
    expect(screen.getByText('你的词书')).toBeInTheDocument()
    expect(screen.getByText('测试词书')).toBeInTheDocument()
    expect(container.querySelector('.study-book-progress-fill')).toHaveStyle({ width: '20%' })
    expect(screen.getByText('主线任务已清空，可以做一轮专项巩固。')).toBeInTheDocument()
  })

  it('prioritizes due review as the main action when reviews are pending', () => {
    hooksState.learningStats.alltime = {
      ebbinghaus_due_total: 6,
      streak_days: 4,
      weakest_mode: 'meaning',
      weakest_mode_accuracy: 68,
    }
    hooksState.learningStats.learnerProfile = {
      summary: {
        due_reviews: 6,
        streak_days: 4,
        weakest_mode: 'meaning',
        weakest_mode_label: '汉译英',
      },
      next_actions: ['先复习到期词。'],
    }

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: '开始到期复习' })).toBeInTheDocument()
    expect(screen.getAllByText('6 词到期').length).toBeGreaterThan(0)
    expect(screen.getByText('先复习到期词')).toBeInTheDocument()
  })
})
