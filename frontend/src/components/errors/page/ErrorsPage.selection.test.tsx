import React from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import ErrorsPage from './ErrorsPage'
import { getWrongWordsReviewSelectionStorageKey } from '../../../features/vocabulary/wrongWordsStore'

const navigateMock = vi.fn()
const apiFetchMock = vi.fn()

const hooksState = vi.hoisted(() => ({
  wrongWords: {
    loading: false,
    words: [
      {
        word: 'due',
        phonetic: '/dju:/',
        pos: 'adj.',
        definition: 'expected',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'demand',
        phonetic: '/demand/',
        pos: 'v.',
        definition: 'need',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
      },
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 8,
        first_wrong_at: '2026-04-07T05:00:00.000Z',
        listening_wrong: 4,
      },
    ],
    removeWord: vi.fn(),
    clearAll: vi.fn(),
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

describe('ErrorsPage selected filtered actions', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockResolvedValue({ words: [] })
    navigateMock.mockReset()
    localStorage.clear()
  })

  it('starts review from selected words inside the active prefix search', async () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '全选结果' }))
    expect(screen.getByRole('button', { name: '开始复习（3词）' })).toBeInTheDocument()

    fireEvent.change(screen.getByRole('searchbox', { name: '搜索错词' }), {
      target: { value: 'd' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '词头' }))
      await Promise.resolve()
    })

    expect(screen.getByText('词头匹配“d” · 2 个结果')).toBeInTheDocument()
    const reviewButton = screen.getByRole('button', { name: '开始复习（2词）' })
    fireEvent.click(reviewButton)

    const storedWords = JSON.parse(localStorage.getItem(getWrongWordsReviewSelectionStorageKey()) ?? '[]')
    expect(storedWords).toEqual(['due', 'demand'])
    expect(navigateMock).toHaveBeenCalledWith('/game?scope=pending&selection=manual&task=error-review')
  })
})
