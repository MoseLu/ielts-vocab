import { describe, expect, it } from 'vitest'
import { buildStudyBookCards } from './homePageModels'
import type { Book, BookProgress } from '../../../types'

describe('buildStudyBookCards', () => {
  it('sorts study books by completion from high to low', () => {
    const books: Book[] = [
      { id: 'low-newer', title: 'Low newer', word_count: 100 },
      { id: 'complete-old', title: 'Complete old', word_count: 100 },
      { id: 'middle-newest', title: 'Middle newest', word_count: 100 },
      { id: 'high-older', title: 'High older', word_count: 100 },
    ]
    const progressMap: Record<string, BookProgress> = {
      'low-newer': { book_id: 'low-newer', current_index: 10, updatedAt: '2026-04-04T12:00:00Z' },
      'complete-old': { book_id: 'complete-old', current_index: 100, updatedAt: '2026-04-01T12:00:00Z' },
      'middle-newest': { book_id: 'middle-newest', current_index: 40, updatedAt: '2026-04-05T12:00:00Z' },
      'high-older': { book_id: 'high-older', current_index: 80, updatedAt: '2026-04-02T12:00:00Z' },
    }

    const cards = buildStudyBookCards(books, new Set(books.map(book => book.id)), progressMap)

    expect(cards.map(card => card.book.id)).toEqual([
      'complete-old',
      'high-older',
      'middle-newest',
      'low-newer',
    ])
  })
})
