import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import ConfusableMatchPage from './ConfusableMatchPage'

const apiFetchMock = vi.fn()

vi.mock('../../contexts', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('../ui/Popover', () => ({
  default: ({
    trigger,
    children,
  }: {
    trigger: React.ReactNode
    children: React.ReactNode
  }) => (
    <div>
      {trigger}
      <div>{children}</div>
    </div>
  ),
}))

vi.mock('../ui/Scrollbar', () => ({
  Scrollbar: ({
    children,
    className,
  }: {
    children: React.ReactNode
    className?: string
  }) => <div className={className}>{children}</div>,
}))

describe('ConfusableMatchPage', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1280,
    })
    Object.defineProperty(window, 'innerHeight', {
      configurable: true,
      writable: true,
      value: 900,
    })

    vi.mocked(global.fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/books/ielts_confusable_match/chapters/1')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            chapter: { id: 1, title: '音近词辨析', word_count: 4 },
            words: [
              { word: 'site', phonetic: '/saɪt/', pos: 'n.', definition: '位置；场所' },
              { word: 'sight', phonetic: '/saɪt/', pos: 'n.', definition: '看见；景象；视力' },
              { word: 'whether', phonetic: '/ˈweðə(r)/', pos: 'conj.', definition: '是否；不管；无论；' },
              { word: 'weather', phonetic: '/ˈweðə(r)/', pos: 'n.', definition: '天气' },
            ],
          }),
        } as Response)
      }

      if (url.includes('/api/books/ielts_confusable_match/chapters')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            chapters: [{ id: 1, title: '音近词辨析', word_count: 4 }],
          }),
        } as Response)
      }

      return Promise.reject(new Error(`Unhandled fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes('/api/books/ielts_confusable_match/chapters/progress')) {
        return Promise.resolve({ chapter_progress: {} })
      }
      if (url.includes('/mode-progress') || url.includes('/progress')) {
        return Promise.resolve({})
      }
      return Promise.reject(new Error(`Unhandled apiFetch: ${url}`))
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('focuses one confusable group at a time and advances after showing the insight card', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/practice/confusable?book=ielts_confusable_match&chapter=1']}>
        <ConfusableMatchPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /site/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /位置；场所/i })).toBeInTheDocument()
    })

    expect(screen.queryByRole('button', { name: /whether/i })).toBeNull()
    expect(container.querySelector('.practice-mode-label')?.textContent).toBe('音近词辨析')
    expect(screen.getByText('词族 1 / 2')).toBeInTheDocument()
    expect(screen.getByText('/ 2 组')).toBeInTheDocument()
    expect(screen.getByText('下一组')).toBeInTheDocument()
    expect(screen.getAllByText(/whether \/ weather/i).length).toBeGreaterThan(0)

    vi.useFakeTimers()

    fireEvent.click(screen.getByRole('button', { name: /site/i }))
    fireEvent.click(screen.getAllByText('看见；景象；视力')[0].closest('button')!)

    expect(screen.getByText('配对错误')).toBeInTheDocument()
    expect(screen.getByText('“site” 和当前中文不是一组')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(950)
    })

    fireEvent.click(screen.getByRole('button', { name: /site/i }))
    fireEvent.click(screen.getAllByText('位置；场所')[0].closest('button')!)

    await act(async () => {
      vi.advanceTimersByTime(950)
    })

    expect(screen.getByRole('button', { name: /sight/i })).toBeInTheDocument()
    expect(container.querySelector('.confusable-progress-ring__core strong')?.textContent).toBe('0')

    fireEvent.click(screen.getByRole('button', { name: /sight/i }))
    fireEvent.click(screen.getAllByText('看见；景象；视力')[0].closest('button')!)

    await act(async () => {
      vi.advanceTimersByTime(950)
    })

    expect(screen.getByText('本组辨析')).toBeInTheDocument()
    expect(screen.getAllByText(/site \/ sight/i).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /whether/i })).toBeNull()

    await act(async () => {
      vi.advanceTimersByTime(1850)
    })

    expect(screen.getByRole('button', { name: /whether/i })).toBeInTheDocument()
    expect(container.querySelector('.confusable-progress-ring__core strong')?.textContent).toBe('1')
    expect(screen.getByText('词族 2 / 2')).toBeInTheDocument()
  })

  it('shows the edit action for custom chapters and opens the editor', async () => {
    vi.mocked(global.fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)

      if (url.includes('/api/books/ielts_confusable_match/chapters/1001')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            chapter: { id: 1001, title: '自定义易混组 01 · site / sight', word_count: 2, is_custom: true },
            words: [
              { word: 'site', phonetic: '/saɪt/', pos: 'n.', definition: '位置；场所', group_key: 'custom-1001' },
              { word: 'sight', phonetic: '/saɪt/', pos: 'n.', definition: '看见；景象；视力', group_key: 'custom-1001' },
            ],
          }),
        } as Response)
      }

      if (url.includes('/api/books/ielts_confusable_match/chapters')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            chapters: [{ id: 1001, title: '自定义易混组 01 · site / sight', word_count: 2, group_count: 1, is_custom: true }],
          }),
        } as Response)
      }

      return Promise.reject(new Error(`Unhandled fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes('/api/books/ielts_confusable_match/chapters/progress')) {
        return Promise.resolve({ chapter_progress: {} })
      }
      if (url.includes('/mode-progress') || url.includes('/progress')) {
        return Promise.resolve({})
      }
      return Promise.reject(new Error(`Unhandled apiFetch: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice/confusable?book=ielts_confusable_match&chapter=1001']}>
        <ConfusableMatchPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '编辑当前组' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: '编辑当前组' }))

    expect(screen.getByText('编辑当前易混组')).toBeInTheDocument()
    expect(screen.getByDisplayValue('site, sight')).toBeInTheDocument()
  })
})
