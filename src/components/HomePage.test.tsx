import React from 'react'
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
}))

vi.mock('../features/vocabulary/hooks', () => ({
  useVocabBooks: () => hooksState.vocabBooks,
  useAllBookProgress: () => hooksState.allBookProgress,
  useMyBooks: () => hooksState.myBooks,
  useWrongWords: () => hooksState.wrongWords,
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
    expect(container.querySelector('.study-center-grid')).toBeNull()
  })

  it('renders the study grid without the top banner or a standalone continue card', () => {
    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.study-banner')).toBeNull()
    expect(container.querySelector('.study-center-grid')).not.toBeNull()
    expect(container.querySelector('.study-book-card-cta')).toBeNull()
    expect(container.querySelector('.study-book-state--active')).not.toBeNull()
    expect(screen.getAllByText('测试词书').length).toBeGreaterThan(0)
  })
})

