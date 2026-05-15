import React from 'react'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
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
        definition: 'alpha definition',
        wrong_count: 8,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        listening_wrong: 1,
        meaning_wrong: 1,
        listening_pass_streak: 1,
        meaning_pass_streak: 1,
        recognition_pass_streak: 0,
        ebbinghaus_streak: 1,
        ebbinghaus_target: 5,
        dimension_states: {
          recognition: {
            history_wrong: 6,
            pass_streak: 0,
          },
          meaning: {
            history_wrong: 1,
            pass_streak: 1,
            last_pass_at: '2026-04-07T06:00:00.000Z',
          },
          listening: {
            history_wrong: 1,
            pass_streak: 1,
            last_pass_at: '2026-04-07T07:00:00.000Z',
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
    hooksState.wrongWords.loading = false
    hooksState.wrongWords.words = [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 8,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        listening_wrong: 1,
        meaning_wrong: 1,
        listening_pass_streak: 1,
        meaning_pass_streak: 1,
        recognition_pass_streak: 0,
        ebbinghaus_streak: 1,
        ebbinghaus_target: 5,
        dimension_states: {
          recognition: {
            history_wrong: 6,
            pass_streak: 0,
          },
          meaning: {
            history_wrong: 1,
            pass_streak: 1,
            last_pass_at: '2026-04-07T06:00:00.000Z',
          },
          listening: {
            history_wrong: 1,
            pass_streak: 1,
            last_pass_at: '2026-04-07T07:00:00.000Z',
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

  it('keeps the FAQ guidance without rendering the removed top overview module', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('错词按这个顺序推进')).not.toBeInTheDocument()
    expect(screen.queryByText('当前查看：待清错词')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /待清错词和累计错词有什么区别/ }))

    expect(screen.getByText(/答错过就会留在累计错词里/)).toBeInTheDocument()
  })

  it('shows a skeleton instead of a fake empty state while wrong words are still loading', () => {
    hooksState.wrongWords.loading = true
    hooksState.wrongWords.words = []

    const { container } = render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton')).not.toBeNull()
    expect(screen.queryByText('暂无错词')).not.toBeInTheDocument()
  })

  it('uses a dropdown with action-oriented labels for problem-type filters', () => {
    hooksState.wrongWords.words = hooksState.wrongWords.words.map(word => word.word === 'gamma' ? { ...word, first_wrong_at: '2026-04-07T05:00:00.000Z' } : word)
    render(<MemoryRouter><ErrorsPage /></MemoryRouter>)

    const modeSelect = screen.getByRole('combobox', { name: '错词模式筛选' })
    expect(modeSelect).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /速记模式/ })).not.toBeInTheDocument()
    fireEvent.click(modeSelect)
    expect(screen.getByRole('option', { name: /速记模式/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /默写模式/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /听音选义/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('option', { name: /听音选义/ }))

    expect(screen.getByLabelText('选择 gamma')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 alpha')).not.toBeInTheDocument()
  })

  it('keeps wrong words in the list and lets learners select them for review', () => {
    const { container } = render(<MemoryRouter><ErrorsPage /></MemoryRouter>)

    expect(screen.queryByTitle('移出未过错词')).not.toBeInTheDocument()
    expect(screen.getByLabelText('选择 alpha')).toBeInTheDocument()
    expect(screen.queryByText('加入复习')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '词头' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: '词尾' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.queryByText('TODO')).not.toBeInTheDocument()
    expect(screen.queryByText(/还需处理/)).not.toBeInTheDocument()
    expect(screen.queryByText(/先做/)).not.toBeInTheDocument()
    expect(screen.queryByText('需答对 1 次')).not.toBeInTheDocument()
    expect(screen.queryByText(/已处理 \d+ 项/)).not.toBeInTheDocument()
    expect(screen.getAllByText('速记模式').length).toBeGreaterThan(0)
    expect(screen.getAllByText('错6').length).toBeGreaterThan(0)
    expect(screen.queryByText('连对 0/4')).not.toBeInTheDocument()
    expect(screen.queryByText('清错推进中')).not.toBeInTheDocument()
    expect(screen.queryByText(/待清完成/)).not.toBeInTheDocument()
    expect(container.querySelector('.errors-stage-pill')).toBeNull()
  })

  it('defaults date filters to today so learners start on today’s wrong words', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('textbox', { name: '起始日期' })).toHaveValue('2026-04-07')
    expect(screen.getByRole('textbox', { name: '结束日期' })).toHaveValue('2026-04-07')
    expect(screen.getByLabelText('选择 alpha')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 beta')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('选择 gamma')).not.toBeInTheDocument()
  })

  it('moves wrong-count and reset controls into the filter header and supports prefix/suffix word search', async () => {
    hooksState.wrongWords.words = [
      {
        word: 'start',
        phonetic: '/stɑːt/',
        pos: 'v.',
        definition: 'begin',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'mist',
        phonetic: '/mɪst/',
        pos: 'n.',
        definition: 'fine drops',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
      },
      {
        word: 'toast',
        phonetic: '/təʊst/',
        pos: 'n.',
        definition: 'bread',
        wrong_count: 8,
        first_wrong_at: '2026-04-07T05:00:00.000Z',
        listening_wrong: 4,
      },
    ]
    apiFetchMock.mockResolvedValue({ words: [] })

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
    expect(within(filterMain as HTMLElement).getByRole('combobox', { name: '错词模式筛选' })).toBeInTheDocument()
    expect(within(filterMain as HTMLElement).getByLabelText('错次区间')).toBeInTheDocument()
    expect(within(filterActions as HTMLElement).getByRole('button', { name: '只看今天新错词' })).toBeInTheDocument()
    expect(within(filterActions as HTMLElement).getByRole('button', { name: '最近 7 天' })).toBeInTheDocument()
    expect(within(filterActions as HTMLElement).getByRole('button', { name: '重置筛选' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('searchbox', { name: '搜索错词' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '执行搜索' })).toBeInTheDocument()
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '词头' })).toHaveAttribute('aria-pressed', 'false')
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '词尾' })).toHaveAttribute('aria-pressed', 'false')
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '词头' })).toBeDisabled()
    expect(within(dimShell as HTMLElement).getByRole('button', { name: '词尾' })).toBeDisabled()

    fireEvent.change(screen.getByRole('searchbox', { name: '搜索错词' }), {
      target: { value: 'st' },
    })

    expect(screen.getByRole('button', { name: '词头' })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: '词尾' })).not.toBeDisabled()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '词头' }))
      await Promise.resolve()
    })

    expect(apiFetchMock).toHaveBeenLastCalledWith('/api/ai/wrong-words?details=compact&search=st')
    expect(container.querySelector('.errors-search-results')).not.toBeNull()
    expect(screen.getByText('词头匹配“st” · 1 个结果')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '词头' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '词尾' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByLabelText('选择 start')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 mist')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('选择 toast')).not.toBeInTheDocument()
    expect(screen.queryByText('错词按这个顺序推进')).not.toBeInTheDocument()
    expect(screen.queryByText('TODO')).not.toBeInTheDocument()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '词尾' }))
      await Promise.resolve()
    })

    expect(screen.getByText('词尾匹配“st” · 2 个结果')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '词头' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: '词尾' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByLabelText('选择 mist')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 toast')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 start')).not.toBeInTheDocument()
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
    fireEvent.click(screen.getByRole('combobox', { name: '错次区间' }))
    fireEvent.click(screen.getByRole('option', { name: '6~10 次' }))
    fireEvent.click(screen.getByLabelText('选择 alpha'))

    const reviewButton = screen.getByRole('button', { name: '开始复习（1词）' })
    expect(reviewButton).toBeInTheDocument()

    fireEvent.click(reviewButton)

    expect(navigateMock).toHaveBeenCalledWith(
      '/practice?mode=errors&scope=pending&startDate=2026-04-07&endDate=2026-04-07&minWrong=6&maxWrong=10&selection=manual',
    )
  })

  it('adds a current-page bulk-select button without replacing the full-results selection', () => {
    hooksState.wrongWords.words = Array.from({ length: 15 }, (_, index) => ({
      word: `word-${index + 1}`,
      phonetic: `/w${index + 1}/`,
      pos: 'n.',
      definition: `definition-${index + 1}`,
      wrong_count: 5,
      first_wrong_at: '2026-04-07T02:00:00.000Z',
      meaning_wrong: 5,
    }))

    const { container } = render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: '全选结果' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '全选当前页' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '全选当前页' }))

    expect(screen.getByRole('button', { name: '开始复习（10词）' })).toBeInTheDocument()

    const scopeRow = container.querySelector('.errors-scope-row')
    fireEvent.click(within(scopeRow as HTMLElement).getByRole('button', { name: '下一页' }))
    fireEvent.click(screen.getByRole('button', { name: '全选当前页' }))

    expect(screen.getByRole('button', { name: '开始复习（15词）' })).toBeInTheDocument()
  })

  it('uses the customized review limit as the wrong-word page size', () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewLimit: '50',
      reviewLimitCustomized: true,
    }))
    hooksState.wrongWords.words = Array.from({ length: 55 }, (_, index) => ({
      word: `word-${index + 1}`,
      phonetic: `/w${index + 1}/`,
      pos: 'n.',
      definition: `definition-${index + 1}`,
      wrong_count: 5,
      first_wrong_at: '2026-04-07T02:00:00.000Z',
      meaning_wrong: 5,
    }))

    const { container } = render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    const scopeRow = container.querySelector('.errors-scope-row')
    expect(scopeRow).not.toBeNull()
    expect(within(scopeRow as HTMLElement).getByText('1-50/55')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 word-50')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 word-51')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '全选当前页' }))

    expect(screen.getByRole('button', { name: '开始复习（50词）' })).toBeInTheDocument()
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

    const { container } = render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    const scopeRow = container.querySelector('.errors-scope-row')
    expect(scopeRow).not.toBeNull()
    expect(container.querySelector('.errors-pagination')).toBeNull()
    expect(within(scopeRow as HTMLElement).getByText('1-10/105')).toBeInTheDocument()
    expect(screen.queryByLabelText('选择 word-11')).not.toBeInTheDocument()

    fireEvent.click(within(scopeRow as HTMLElement).getByRole('button', { name: '下一页' }))

    expect(within(scopeRow as HTMLElement).getByText('11-20/105')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 word-11')).toBeInTheDocument()
  })
})
