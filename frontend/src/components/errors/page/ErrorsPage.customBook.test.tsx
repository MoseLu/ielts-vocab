import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ErrorsPage from './ErrorsPage'

const navigateMock = vi.fn()
const apiFetchMock = vi.fn()

const hooksState = vi.hoisted(() => ({
  wrongWords: {
    loading: false,
    words: [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: '阿尔法',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: '贝塔',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
      },
    ],
  },
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useWrongWords: () => hooksState.wrongWords,
}))

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe('ErrorsPage custom book export', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    navigateMock.mockReset()
    localStorage.clear()
    hooksState.wrongWords.words = [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: '阿尔法',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: '贝塔',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
      },
    ]
    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith('/api/ai/wrong-words?')) return Promise.resolve({ words: [] })
      if (url === '/api/books/custom-books') {
        return Promise.resolve({
          books: [{ id: 'custom_1', title: '固定搭配词书', word_count: 0 }],
        })
      }
      if (url === '/api/books/custom-books/custom_1/chapters') {
        return Promise.resolve({
          bookId: 'custom_1',
          created_chapters: [{ id: 'custom_1_2', title: '以 al 开头' }],
          rejected_words: [],
        })
      }
      return Promise.resolve({})
    })
  })

  it('appends selected wrong words to an existing custom book and opens quick memory', async () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByRole('searchbox', { name: '搜索错词' }), {
      target: { value: 'al' },
    })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '词头' }))
      await Promise.resolve()
    })

    fireEvent.click(screen.getByLabelText('选择 alpha'))
    fireEvent.click(screen.getByRole('button', { name: '保存到自定义词书' }))
    fireEvent.click(await screen.findByLabelText('固定搭配词书'))
    fireEvent.click(screen.getByRole('button', { name: '保存为章节' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/custom-books/custom_1/chapters',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            chapters: [{ id: 'wrong-word-export', title: '以 al 开头' }],
            words: [{
              chapterId: 'wrong-word-export',
              word: 'alpha',
              phonetic: '/a/',
              pos: 'n.',
              definition: '阿尔法',
            }],
          }),
        }),
      )
    })

    fireEvent.click(await screen.findByRole('button', { name: '前往快速记忆' }))

    expect(navigateMock).toHaveBeenCalledWith('/practice?book=custom_1&chapter=custom_1_2&mode=quickmemory&restart=1')
  })

  it('splits exported wrong words by the customized review limit', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewLimit: '2',
      reviewLimitCustomized: true,
    }))
    hooksState.wrongWords.words = Array.from({ length: 5 }, (_, index) => ({
      word: `delta-${index + 1}`,
      phonetic: `/d${index + 1}/`,
      pos: 'n.',
      definition: `定义${index + 1}`,
      wrong_count: 5,
      first_wrong_at: '2026-04-07T04:00:00.000Z',
      meaning_wrong: 2,
    }))

    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '全选结果' }))
    fireEvent.click(screen.getByRole('button', { name: '保存到自定义词书' }))
    fireEvent.click(await screen.findByLabelText('固定搭配词书'))
    fireEvent.click(screen.getByRole('button', { name: '保存为章节' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/custom-books/custom_1/chapters',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            chapters: [
              { id: 'wrong-word-export-1', title: '错词本精选（1/3）' },
              { id: 'wrong-word-export-2', title: '错词本精选（2/3）' },
              { id: 'wrong-word-export-3', title: '错词本精选（3/3）' },
            ],
            words: [
              { chapterId: 'wrong-word-export-1', word: 'delta-1', phonetic: '/d1/', pos: 'n.', definition: '定义1' },
              { chapterId: 'wrong-word-export-1', word: 'delta-2', phonetic: '/d2/', pos: 'n.', definition: '定义2' },
              { chapterId: 'wrong-word-export-2', word: 'delta-3', phonetic: '/d3/', pos: 'n.', definition: '定义3' },
              { chapterId: 'wrong-word-export-2', word: 'delta-4', phonetic: '/d4/', pos: 'n.', definition: '定义4' },
              { chapterId: 'wrong-word-export-3', word: 'delta-5', phonetic: '/d5/', pos: 'n.', definition: '定义5' },
            ],
          }),
        }),
      )
    })
    expect(await screen.findByText('已生成 3 个章节，每章最多 2 个词。')).toBeInTheDocument()
  })
})
