import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import VocabBookPage from './VocabBookPage'

const hooksState = vi.hoisted(() => ({
  vocabBooks: {
    books: [
      {
        id: 'book-1',
        title: '词书 A',
        word_count: 100,
        study_type: 'ielts',
        category: 'reading',
        level: 'beginner',
      },
    ],
    loading: false,
    error: null,
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
  },
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useVocabBooks: () => hooksState.vocabBooks,
  useAllBookProgress: () => hooksState.allBookProgress,
  useMyBooks: () => hooksState.myBooks,
}))

vi.mock('../dialogs/PlanModal', () => ({
  default: () => null,
}))

vi.mock('../dialogs/ChapterModal', () => ({
  default: () => null,
}))

describe('VocabBookPage', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1800,
    })

    hooksState.vocabBooks.books = [
      {
        id: 'book-1',
        title: '词书 A',
        word_count: 100,
        study_type: 'ielts',
        category: 'reading',
        level: 'beginner',
      },
    ]
    hooksState.vocabBooks.loading = false
    hooksState.vocabBooks.error = null
    hooksState.allBookProgress.progressMap = { 'book-1': { current_index: 20 } }
    hooksState.allBookProgress.loading = false
    hooksState.myBooks.myBookIds = new Set(['book-1'])
    hooksState.myBooks.loading = false
    hooksState.myBooks.addBook.mockReset()
  })

  it('keeps the page in loading state until books, progress, and my books resolve', () => {
    hooksState.vocabBooks.books = []
    hooksState.vocabBooks.loading = true
    hooksState.allBookProgress.progressMap = {}
    hooksState.allBookProgress.loading = true
    hooksState.myBooks.myBookIds = new Set()
    hooksState.myBooks.loading = true

    const { container } = render(
      <MemoryRouter>
        <VocabBookPage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton--books')).not.toBeNull()
    expect(container.querySelectorAll('.page-skeleton-card--book')).toHaveLength(7)
    expect(container.querySelector('.vb-grid')).toBeNull()
  })

  it('renders the book grid after data resolves', () => {
    const { container } = render(
      <MemoryRouter>
        <VocabBookPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('词书 A')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '创建词书' })).toBeNull()
    expect(container.querySelector('.vb-card-progress-fill')).toHaveStyle({ width: '20%' })
  })

  it('renders compact filter tabs instead of stretched buttons', () => {
    render(
      <MemoryRouter>
        <VocabBookPage />
      </MemoryRouter>,
    )

    const filterRows = document.querySelectorAll('.vb-filter-row')
    const filterButtons = document.querySelectorAll('.vb-filter-btn')

    expect(filterRows.length).toBeGreaterThan(0)
    expect(filterButtons.length).toBeGreaterThan(0)

    filterRows.forEach((row) => {
      expect(row).toHaveClass('vb-filter-row--compact')
    })

    filterButtons.forEach((button) => {
      expect(button).toHaveClass('vb-filter-btn--compact')
    })
  })

  it('shows confusable books in groups instead of words', () => {
    hooksState.vocabBooks.books = [
      {
        id: 'ielts_confusable_match',
        title: '雅思易混词辨析',
        word_count: 2026,
        group_count: 540,
        study_type: 'ielts',
        category: 'confusable',
        level: 'advanced',
      },
    ]
    hooksState.allBookProgress.progressMap = {}
    hooksState.myBooks.myBookIds = new Set()

    render(
      <MemoryRouter>
        <VocabBookPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('540 组')).toBeInTheDocument()
    expect(screen.queryByText('2026 词')).toBeNull()
  })
})
