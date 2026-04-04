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

  it('renders matches, removes correct pairs, and shows a warning on wrong links', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/practice/confusable?book=ielts_confusable_match&chapter=1']}>
        <ConfusableMatchPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('site')).toBeInTheDocument()
      expect(screen.getByText('天气')).toBeInTheDocument()
    })

    vi.useFakeTimers()

    fireEvent.click(screen.getByText('site').closest('button')!)
    fireEvent.click(screen.getByText('位置；场所').closest('button')!)

    expect(container.querySelector('.confusable-line')).not.toBeNull()
    expect(container.querySelectorAll('.confusable-card.is-success')).toHaveLength(2)

    await act(async () => {
      vi.advanceTimersByTime(950)
    })

    expect(screen.queryByText('site')).toBeNull()
    expect(screen.queryByText('位置；场所')).toBeNull()
    expect(screen.getByText('成功 1')).toBeInTheDocument()

    fireEvent.click(screen.getByText('sight').closest('button')!)
    fireEvent.click(screen.getByText('天气').closest('button')!)

    expect(screen.getByText('配对错误')).toBeInTheDocument()
    expect(screen.getByText('“sight” 和当前中文不是一组')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(950)
    })

    expect(screen.queryByText('配对错误')).toBeNull()
    expect(screen.getByText('误连 1')).toBeInTheDocument()
  })
})
