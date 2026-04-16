import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import WordListDetailPanel from './WordListDetailPanel'
import { apiFetch } from '../../lib'
import type { Word } from './types'

vi.mock('../layout/navigation/GlobalWordSearchDetailPanel', () => ({
  default: ({
    query,
    result,
    onPickWord,
  }: {
    query: string
    result: { word: string; definition: string; book_title?: string }
    onPickWord: (word: string) => void
  }) => (
    <div data-testid="global-word-search-detail">
      <div>{`${query}|${result.word}|${result.definition}|${result.book_title ?? ''}`}</div>
      <button type="button" onClick={() => onPickWord('beta')}>pick beta</button>
      <button type="button" onClick={() => onPickWord('gamma')}>pick gamma</button>
    </div>
  ),
}))

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: vi.fn(),
  }
})

const apiFetchMock = vi.mocked(apiFetch)

const visibleWords: Word[] = [
  { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha local', book_id: 'local-book', book_title: 'Local Book' },
  { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta local', book_id: 'local-book', book_title: 'Local Book' },
]

describe('WordListDetailPanel', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  it('shows the selected word immediately and then enriches it with global search data', async () => {
    apiFetchMock.mockResolvedValueOnce({
      query: 'alpha',
      total: 1,
      results: [
        {
          word: 'alpha',
          phonetic: '/al-fa/',
          pos: 'n.',
          definition: 'alpha search',
          book_id: 'search-book',
          book_title: 'Search Book',
          match_type: 'exact',
        },
      ],
    })

    render(
      <WordListDetailPanel
        open
        selectedWord={visibleWords[0]}
        visibleWords={visibleWords}
        onClose={() => {}}
        onPickLocalWord={() => {}}
      />,
    )

    expect(screen.getByRole('dialog', { name: '单词详情' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '单词详情' })).toBeNull()

    await waitFor(() => {
      expect(screen.getByTestId('global-word-search-detail')).toHaveTextContent('alpha|alpha|alpha local|Local Book')
    })

    await waitFor(() => {
      expect(screen.getByTestId('global-word-search-detail')).toHaveTextContent('alpha|alpha|alpha search|Search Book')
    })
  })

  it('delegates local word picks back to the parent selection handler', async () => {
    const onPickLocalWord = vi.fn()
    apiFetchMock.mockResolvedValueOnce({ query: 'alpha', total: 0, results: [] })

    render(
      <WordListDetailPanel
        open
        selectedWord={visibleWords[0]}
        visibleWords={visibleWords}
        onClose={() => {}}
        onPickLocalWord={onPickLocalWord}
      />,
    )

    await screen.findByRole('button', { name: 'pick beta' })
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(1))

    await userEvent.setup().click(screen.getByRole('button', { name: 'pick beta' }))

    expect(onPickLocalWord).toHaveBeenCalledWith('beta')
    expect(apiFetchMock).toHaveBeenCalledTimes(1)
  })

  it('falls back locally and then resolves external picks through the search endpoint', async () => {
    let resolveGammaSearch: ((value: unknown) => void) | null = null
    apiFetchMock
      .mockResolvedValueOnce({ query: 'alpha', total: 0, results: [] })
      .mockImplementationOnce(
        () =>
          new Promise(resolve => {
            resolveGammaSearch = resolve
          }),
      )

    render(
      <WordListDetailPanel
        open
        selectedWord={visibleWords[0]}
        visibleWords={visibleWords}
        onClose={() => {}}
        onPickLocalWord={() => {}}
      />,
    )

    await screen.findByRole('button', { name: 'pick gamma' })
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(1))

    await userEvent.setup().click(screen.getByRole('button', { name: 'pick gamma' }))

    expect(screen.getByTestId('global-word-search-detail')).toHaveTextContent('gamma|gamma||')

    resolveGammaSearch?.({
      query: 'gamma',
      total: 1,
      results: [
        {
          word: 'gamma',
          phonetic: '/ga-ma/',
          pos: 'n.',
          definition: 'gamma search',
          book_id: 'search-book',
          book_title: 'Gamma Book',
          match_type: 'exact',
        },
      ],
    })

    await waitFor(() => {
      expect(screen.getByTestId('global-word-search-detail')).toHaveTextContent('gamma|gamma|gamma search|Gamma Book')
    })
  })
})
