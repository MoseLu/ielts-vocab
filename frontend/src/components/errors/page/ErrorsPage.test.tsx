import React from 'react'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import ErrorsPage from './ErrorsPage'

const navigateMock = vi.fn()
const apiFetchMock = vi.fn()

const hooksState = vi.hoisted(() => ({
  wrongWords: {
    words: [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
        meaning_pass_streak: 2,
        recognition_pass_streak: 1,
        ebbinghaus_streak: 1,
        ebbinghaus_target: 5,
        dimension_states: {
          recognition: {
            history_wrong: 3,
            pass_streak: 1,
            last_pass_at: '2026-04-07T07:00:00.000Z',
          },
          meaning: {
            history_wrong: 3,
            pass_streak: 2,
            last_pass_at: '2026-04-07T06:00:00.000Z',
          },
        },
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: 'beta definition',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
        dictation_wrong: 1,
        meaning_pass_streak: 4,
        dictation_pass_streak: 1,
        recognition_pass_streak: 4,
        ebbinghaus_streak: 2,
        ebbinghaus_target: 5,
        dimension_states: {
          recognition: {
            history_wrong: 2,
            pass_streak: 4,
            last_pass_at: '2026-04-07T05:30:00.000Z',
          },
          meaning: {
            history_wrong: 2,
            pass_streak: 4,
            last_pass_at: '2026-04-07T05:00:00.000Z',
          },
          dictation: {
            history_wrong: 1,
            pass_streak: 1,
            last_pass_at: '2026-04-07T05:45:00.000Z',
          },
        },
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

describe('ErrorsPage', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockResolvedValue({ words: [] })
    navigateMock.mockReset()
    localStorage.clear()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-07T08:00:00.000Z'))
    hooksState.wrongWords.words = [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
        meaning_pass_streak: 2,
        recognition_pass_streak: 1,
        ebbinghaus_streak: 1,
        ebbinghaus_target: 5,
        dimension_states: {
          recognition: {
            history_wrong: 3,
            pass_streak: 1,
            last_pass_at: '2026-04-07T07:00:00.000Z',
          },
          meaning: {
            history_wrong: 3,
            pass_streak: 2,
            last_pass_at: '2026-04-07T06:00:00.000Z',
          },
        },
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: 'beta definition',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
        dictation_wrong: 1,
        meaning_pass_streak: 4,
        dictation_pass_streak: 1,
        recognition_pass_streak: 4,
        ebbinghaus_streak: 2,
        ebbinghaus_target: 5,
        dimension_states: {
          recognition: {
            history_wrong: 2,
            pass_streak: 4,
            last_pass_at: '2026-04-07T05:30:00.000Z',
          },
          meaning: {
            history_wrong: 2,
            pass_streak: 4,
            last_pass_at: '2026-04-07T05:00:00.000Z',
          },
          dictation: {
            history_wrong: 1,
            pass_streak: 1,
            last_pass_at: '2026-04-07T05:45:00.000Z',
          },
        },
      },
      {
        word: 'gamma',
        phonetic: '/g/',
        pos: 'n.',
        definition: 'gamma definition',
        wrong_count: 8,
        first_wrong_at: '2026-03-28T05:00:00.000Z',
        listening_wrong: 4,
        listening_pass_streak: 0,
        recognition_pass_streak: 0,
        ebbinghaus_streak: 0,
        ebbinghaus_target: 5,
      },
    ]
  })

  afterEach(() => {
    vi.useRealTimers()
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
    expect(screen.getByText('现在每个错词走到哪一步')).toBeInTheDocument()
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
      screen.getByText(/一个词可能同时属于多类问题，所以这里的标签数量会重复计算。当前 3 个待清错词对应了 5 个问题标签，其中 2 个词同时落在多个问题类型里，这些数字不是互斥拆分。/)
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
    expect(screen.getAllByText('错词本进度').length).toBeGreaterThan(0)
    expect(screen.getAllByText('长期复习').length).toBeGreaterThan(0)
    expect(screen.getByText('今天移出 2 项')).toBeInTheDocument()
  })

  it('offers quick date filters so learners can focus on today’s new wrong words', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '只看今天新错词' }))

    expect(screen.getByText('当前筛选命中 2 个待清错词')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 alpha')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 beta')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 gamma')).not.toBeInTheDocument()
  })

  it('moves wrong-count and reset controls into the filter header and supports searching wrong words', async () => {
    apiFetchMock.mockResolvedValue({
      words: [
        {
          word: 'alpha',
          phonetic: '/a/',
          pos: 'n.',
          definition: 'alpha definition',
          wrong_count: 6,
        },
      ],
    })

    const { container } = render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    const filterMain = container.querySelector('.errors-filter-panel-main')
    const filterActions = container.querySelector('.errors-filter-panel-actions')
    const dimShell = container.querySelector('.errors-dim-filter-shell')
    expect(filterMain).not.toBeNull()
    expect(filterActions).not.toBeNull()
    expect(dimShell).not.toBeNull()
    expect(within(filterMain as HTMLElement).getByLabelText('错次区间')).toBeInTheDocument()
    expect(within(filterActions as HTMLElement).getByRole('button', { name: '重置筛选' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '只看今天新错词' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '最近 7 天' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('searchbox', { name: '搜索错词' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '执行搜索' })).toBeInTheDocument()

    fireEvent.change(screen.getByRole('searchbox', { name: '搜索错词' }), {
      target: { value: 'alp' },
    })
    await act(async () => {
      fireEvent.submit(container.querySelector('.errors-search-form') as HTMLFormElement)
      await Promise.resolve()
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/wrong-words?details=compact&search=alp')
    expect(screen.getByText('当前筛选命中 1 个待清错词，搜索“alp”')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 alpha')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 beta')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('选择 gamma')).not.toBeInTheDocument()
  })

  it('builds a targeted review route from the selected date and wrong-count range', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText('起始日期'), {
      target: { value: '2026-04-07' },
    })
    fireEvent.change(screen.getByLabelText('结束日期'), {
      target: { value: '2026-04-07' },
    })
    fireEvent.change(screen.getByLabelText('错次区间'), {
      target: { value: '6-10' },
    })
    fireEvent.click(screen.getByLabelText('选择 alpha'))

    const reviewButton = screen.getByRole('button', { name: '复习已选（1词）' })
    expect(reviewButton).toBeInTheDocument()

    fireEvent.click(reviewButton)

    expect(navigateMock).toHaveBeenCalledWith(
      '/practice?mode=errors&scope=pending&startDate=2026-04-07&endDate=2026-04-07&minWrong=6&maxWrong=10&selection=manual',
    )
  })

  it('paginates large wrong-word lists instead of rendering everything at once', () => {
    hooksState.wrongWords.words = Array.from({ length: 105 }, (_, index) => ({
      word: `word-${index + 1}`,
      phonetic: `/w${index + 1}/`,
      pos: 'n.',
      definition: `definition-${index + 1}`,
      wrong_count: 5,
      first_wrong_at: '2026-04-07T02:00:00.000Z',
      meaning_wrong: 5,
    }))

    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('当前显示第 1-100 条，共 105 条')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 word-101')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下一页' }))

    expect(screen.getByText('当前显示第 101-105 条，共 105 条')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 word-101')).toBeInTheDocument()
  })
})
