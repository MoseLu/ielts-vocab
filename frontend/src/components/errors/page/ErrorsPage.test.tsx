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

vi.mock('../../../features/vocabulary/hooks', () => ({
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
    localStorage.clear()
  })

  it('explains the difference between pending and accumulated wrong words', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(/一个词只要答错过，就会进入“累计错词”/)
    ).toBeInTheDocument()
  })

  it('uses action-oriented labels for problem-type filters and explains overlap clearly', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('tab', { name: /看词认义/ })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /中文想英文/ })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /听音辨义/ })).toBeInTheDocument()

    expect(
      screen.getByText(/一个词可能同时属于多类问题，所以这里的标签数量会重复计算。当前 3 个待清错词对应了 6 个问题标签，其中 3 个词同时落在多个问题类型里，这些数字不是互斥拆分。/)
    ).toBeInTheDocument()
  })

  it('keeps wrong words in the list and lets learners select them for review', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByTitle('移出未过错词')).not.toBeInTheDocument()
    expect(screen.getByLabelText('选择 alpha')).toBeInTheDocument()
    expect(screen.getAllByText('加入复习')).toHaveLength(1)
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
    fireEvent.click(screen.getByLabelText('选择 alpha'))

    const reviewButton = screen.getByRole('button', { name: '复习已选（1词）' })
    expect(reviewButton).toBeInTheDocument()

    fireEvent.click(reviewButton)

    expect(navigateMock).toHaveBeenCalledWith(
      '/practice?mode=errors&scope=pending&startDate=2026-03-31&endDate=2026-03-31&minWrong=6&maxWrong=10&selection=manual',
    )
  })
})
