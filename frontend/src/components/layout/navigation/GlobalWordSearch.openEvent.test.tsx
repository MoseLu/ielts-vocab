import { act, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GlobalWordSearch from './GlobalWordSearch'
import { openGlobalWordSearch } from './globalWordSearchEvents'

const { useAuthMock, useFavoriteWordsMock, useToastMock } = vi.hoisted(() => ({
  useAuthMock: vi.fn(() => ({ user: { id: 1, username: 'admin' } })),
  useFavoriteWordsMock: vi.fn(() => ({
    isFavorite: () => false,
    isPending: () => false,
    toggleFavorite: vi.fn(),
  })),
  useToastMock: vi.fn(() => ({ showToast: vi.fn() })),
}))

const apiFetchMock = vi.fn()
const playExampleAudioMock = vi.fn()
const stopAudioMock = vi.fn()

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('../../../contexts', () => ({
  useAuth: () => useAuthMock(),
  useToast: () => useToastMock(),
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useFavoriteWords: (...args: unknown[]) => useFavoriteWordsMock(...args),
}))

vi.mock('../../practice/utils', () => ({
  playExampleAudio: (...args: unknown[]) => playExampleAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))

const quietSearchResult = {
  query: 'quiet',
  total: 1,
  results: [{
    word: 'quiet',
    phonetic: '/ˈkwaɪət/',
    pos: 'adj.',
    definition: '安静的',
    book_id: 'book-a',
    book_title: 'Book A',
    chapter_id: 2,
    chapter_title: 'Chapter 2',
    match_type: 'exact' as const,
  }],
}

const quietWordDetails = {
  word: 'quiet',
  phonetic: '/ˈkwaɪət/',
  pos: 'adj.',
  definition: '安静的',
  root: {
    word: 'quiet',
    normalized_word: 'quiet',
    segments: [{ kind: '词根' as const, text: 'qui', meaning: '静' }],
    summary: 'quiet 可以直接按词形记忆。',
    source: 'generated',
    updated_at: null,
  },
  english: {
    word: 'quiet',
    normalized_word: 'quiet',
    entries: [{ pos: 'adj.', definition: 'making very little noise' }],
    source: 'llm',
    updated_at: null,
  },
  examples: [],
  derivatives: [],
  note: {
    word: 'quiet',
    content: '',
    updated_at: null,
  },
}

describe('GlobalWordSearch open event', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    playExampleAudioMock.mockReset()
    stopAudioMock.mockReset()
    useAuthMock.mockReset()
    useFavoriteWordsMock.mockReset()
    useToastMock.mockReset()
    useAuthMock.mockReturnValue({ user: { id: 1, username: 'admin' } })
    useToastMock.mockReturnValue({ showToast: vi.fn() })
    useFavoriteWordsMock.mockReturnValue({
      isFavorite: () => false,
      isPending: () => false,
      toggleFavorite: vi.fn(),
    })
  })

  it('prefills the query without auto-submitting by default', async () => {
    render(<GlobalWordSearch />)

    await act(async () => {
      openGlobalWordSearch({ query: 'quiet' })
    })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    expect(input).toHaveValue('quiet')
    expect(apiFetchMock).not.toHaveBeenCalled()
  })

  it('auto-submits when the open event requests it', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quiet&limit=12') {
        return Promise.resolve(quietSearchResult)
      }
      if (url === '/api/books/word-details?word=quiet') {
        return Promise.resolve(quietWordDetails)
      }
      throw new Error(`Unexpected request: ${url}`)
    })

    render(<GlobalWordSearch />)

    await act(async () => {
      openGlobalWordSearch({ query: 'quiet', autoSubmit: true })
    })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/search?q=quiet&limit=12',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      )
    })

    await screen.findByText('安静的')
    expect(screen.getByText('adj.')).toBeInTheDocument()
    expect(screen.queryByRole('searchbox', { name: '全局单词搜索' })).not.toBeInTheDocument()
  })
})
