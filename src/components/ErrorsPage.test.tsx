import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import ErrorsPage from './ErrorsPage'

const navigateMock = vi.fn()

const hooksState = vi.hoisted(() => ({
  wrongWords: {
    words: [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 6,
        first_wrong_at: '2026-03-31T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: 'beta definition',
        wrong_count: 3,
        first_wrong_at: '2026-03-31T04:00:00.000Z',
        meaning_wrong: 2,
      },
      {
        word: 'gamma',
        phonetic: '/g/',
        pos: 'n.',
        definition: 'gamma definition',
        wrong_count: 8,
        first_wrong_at: '2026-03-28T05:00:00.000Z',
        listening_wrong: 4,
      },
    ],
    removeWord: vi.fn(),
    clearAll: vi.fn(),
  },
}))

vi.mock('../features/vocabulary/hooks', () => ({
  useWrongWords: () => hooksState.wrongWords,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe('ErrorsPage', () => {
  beforeEach(() => {
    navigateMock.mockReset()
  })

  it('explains that pending wrong words clear after four consecutive passes in the same dimension', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(/同一维度连续答对 4 次后，从未过错词移出/)
    ).toBeInTheDocument()
  })

  it('builds a targeted review route from the selected date and wrong-count range', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText('起始日期'), {
      target: { value: '2026-03-31' },
    })
    fireEvent.change(screen.getByLabelText('结束日期'), {
      target: { value: '2026-03-31' },
    })
    fireEvent.change(screen.getByLabelText('错次区间'), {
      target: { value: '6-10' },
    })

    const reviewButton = screen.getByRole('button', { name: '复习（1词）' })
    expect(reviewButton).toBeInTheDocument()

    fireEvent.click(reviewButton)

    expect(navigateMock).toHaveBeenCalledWith(
      '/practice?mode=errors&scope=pending&startDate=2026-03-31&endDate=2026-03-31&minWrong=6&maxWrong=10',
    )
  })
})
