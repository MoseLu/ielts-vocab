import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminDashboardFavoriteWordsPanel } from './AdminDashboardFavoriteWordsPanel'

const favoriteWords = [
  {
    word: 'compile',
    normalized_word: 'compile',
    phonetic: '/kəmˈpaɪl/',
    pos: 'v.',
    definition: 'to collect information',
    source_book_id: 'ielts_reading_premium',
    source_book_title: '雅思阅读精讲',
    source_chapter_id: '3',
    source_chapter_title: '第3章',
    created_at: '2026-04-07T08:00:00+00:00',
    updated_at: '2026-04-07T08:00:00+00:00',
  },
  {
    word: 'abandon',
    normalized_word: 'abandon',
    phonetic: '/əˈbændən/',
    pos: 'v.',
    definition: 'to leave behind',
    source_book_id: 'ielts_listening_premium',
    source_book_title: '雅思听力精讲',
    source_chapter_id: '12',
    source_chapter_title: '第12章',
    created_at: '2026-04-06T08:00:00+00:00',
    updated_at: '2026-04-06T08:00:00+00:00',
  },
]

describe('AdminDashboardFavoriteWordsPanel', () => {
  const createObjectURLMock = vi.fn(() => 'blob:test')
  const revokeObjectURLMock = vi.fn()
  let anchorClickSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    createObjectURLMock.mockClear()
    revokeObjectURLMock.mockClear()
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURLMock, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: revokeObjectURLMock, writable: true })
    anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  afterEach(() => {
    anchorClickSpy.mockRestore()
  })

  it('renders favorite words with source book metadata', () => {
    render(<AdminDashboardFavoriteWordsPanel favoriteWords={favoriteWords} username="learner" />)

    expect(screen.getByText(/共 2 个收藏词/)).toBeInTheDocument()
    expect(screen.getByText('compile')).toBeInTheDocument()
    expect(screen.getByText('雅思阅读精讲')).toBeInTheDocument()
    expect(screen.getByText('第12章')).toBeInTheDocument()
  })

  it('exports favorite words as csv, txt, and json', () => {
    render(<AdminDashboardFavoriteWordsPanel favoriteWords={favoriteWords} username="learner" />)

    fireEvent.click(screen.getByRole('button', { name: '导出 CSV' }))
    fireEvent.click(screen.getByRole('button', { name: '导出 TXT' }))
    fireEvent.click(screen.getByRole('button', { name: '导出 JSON' }))

    expect(createObjectURLMock).toHaveBeenCalledTimes(3)
    expect(revokeObjectURLMock).toHaveBeenCalledTimes(3)
    expect(anchorClickSpy).toHaveBeenCalledTimes(3)
  })
})
