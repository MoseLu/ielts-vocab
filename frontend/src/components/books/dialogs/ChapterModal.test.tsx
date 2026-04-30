import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ChapterModal from './ChapterModal'

const apiFetchMock = vi.fn()
const navigateMock = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('../../../contexts', () => ({
  useAuth: () => ({ user: { id: 1 } }),
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('../../ui/Scrollbar', () => ({
  Scrollbar: ({
    children,
    className,
    wrapClassName,
  }: {
    children: React.ReactNode
    className?: string
    wrapClassName?: string
  }) => (
    <div className={className}>
      <div className={wrapClassName}>{children}</div>
    </div>
  ),
}))

describe('ChapterModal', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1440,
    })
    Object.defineProperty(window, 'innerHeight', {
      configurable: true,
      writable: true,
      value: 900,
    })

    apiFetchMock.mockReset()
    navigateMock.mockReset()
    vi.mocked(global.fetch).mockReset()
  })

  it('keeps chapter word count visible when mode badges exist', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        chapters: [{ id: 1, title: 'Unit 1', word_count: 30 }],
      }),
    } as Response)

    apiFetchMock.mockResolvedValue({
      chapter_progress: {
        1: {
          is_completed: false,
          words_learned: 12,
          accuracy: 80,
          modes: {
            quickmemory: {
              mode: 'quickmemory',
              correct_count: 8,
              wrong_count: 2,
              accuracy: 80,
              is_completed: true,
            },
          },
        },
      },
    })

    const { container } = render(
      <ChapterModal
        book={{ id: 'book-1', title: 'Test Book', word_count: 30 }}
        progress={{ current_index: 12 }}
        onClose={() => {}}
        onSelectChapter={() => {}}
      />,
    )

    await waitFor(() => {
      expect(container.querySelector('.chapter-card-count')?.textContent).toContain('30')
    })
  })

  it('uses a full-height skeleton inside the modal body while chapters are loading', () => {
    vi.mocked(global.fetch).mockImplementation(() => new Promise(() => {}))

    const { container } = render(
      <ChapterModal
        book={{ id: 'book-1', title: 'Test Book', word_count: 30 }}
        progress={{ current_index: 12 }}
        onClose={() => {}}
        onSelectChapter={() => {}}
      />,
    )

    expect(container.querySelector('.chapter-modal-scroll-wrap')).not.toBeNull()
    expect(container.querySelector('.chapter-skeleton')).not.toBeNull()
    expect(container.querySelector('.chapter-loading--centered')).not.toBeNull()
    expect(container.querySelectorAll('.chapter-skeleton-card')).toHaveLength(12)
    expect(container.querySelector('.loading-spinner')).toBeNull()
  })

  it('shows confusable chapters in groups instead of words', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        chapters: [
          { id: 1, title: '音近词辨析 01', word_count: 120, group_count: 60 },
          { id: 2, title: '音近词辨析 02', word_count: 120, group_count: 60 },
        ],
      }),
    } as Response)

    apiFetchMock.mockResolvedValue({ chapter_progress: {} })

    render(
      <ChapterModal
        book={{ id: 'ielts_confusable_match', title: '雅思易混词辨析', word_count: 2026, group_count: 540 }}
        progress={{ current_index: 0 }}
        onClose={() => {}}
        onSelectChapter={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('2 章节 · 120 组')).toBeInTheDocument()
    })

    expect(screen.getAllByText('60 组')).toHaveLength(2)
    expect(screen.queryByText('120 词')).toBeNull()
  })

  it('reports the independent game entry when the user switches to 游戏闯关', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        chapters: [{ id: 1, title: 'Unit 1', word_count: 30 }],
      }),
    } as Response)

    apiFetchMock.mockResolvedValue({ chapter_progress: {} })
    const onSelectChapter = vi.fn()
    const user = userEvent.setup()

    render(
      <ChapterModal
        book={{ id: 'book-1', title: 'Test Book', word_count: 30 }}
        progress={{ current_index: 0 }}
        onClose={() => {}}
        onSelectChapter={onSelectChapter}
      />,
    )

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '游戏闯关' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('tab', { name: '游戏闯关' }))
    await user.click(screen.getByText('Unit 1'))

    expect(onSelectChapter).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1, title: 'Unit 1' }),
      0,
      'game',
    )
  })

  it('offers an edit entry for existing custom books', async () => {
    const user = userEvent.setup()
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        chapters: [{ id: 'custom_1_1', title: '第1章', word_count: 20 }],
      }),
    } as Response)
    apiFetchMock.mockResolvedValue({ chapter_progress: {} })

    render(
      <ChapterModal
        book={{ id: 'custom_1', title: '我的词书', word_count: 20, is_custom_book: true }}
        progress={{ current_index: 0 }}
        onClose={() => {}}
        onSelectChapter={() => {}}
      />,
    )

    await user.click(screen.getByRole('button', { name: '编辑词书' }))

    expect(navigateMock).toHaveBeenCalledWith('/books/create?bookId=custom_1')
  })
})
