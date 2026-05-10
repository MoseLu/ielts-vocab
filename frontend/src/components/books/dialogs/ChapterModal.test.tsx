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

function mockChapterResponses(chapters: unknown[], chapterProgress: Record<string, unknown> = {}) {
  apiFetchMock.mockImplementation((url: unknown) => Promise.resolve(
    typeof url === 'string' && url.endsWith('/chapters/progress')
      ? { chapter_progress: chapterProgress }
      : { chapters },
  ))
}

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
  })

  it('prioritizes chapter completion and vertical mode accuracy comparison', async () => {
    mockChapterResponses(
      [{ id: 1, title: 'Unit 1', word_count: 30 }],
      {
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
              is_completed: false,
            },
            meaning: {
              mode: 'meaning',
              correct_count: 0,
              wrong_count: 0,
              accuracy: 0,
              is_completed: false,
            },
            dictation: {
              mode: 'dictation',
              correct_count: 0,
              wrong_count: 3,
              accuracy: 0,
              is_completed: false,
            },
          },
        },
      },
    )

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
    expect(screen.getByRole('img', { name: '章节完成率 40%，模式正确率：速记模式 80%，听写模式 0%' })).toBeInTheDocument()
    expect(screen.getByText('完成率')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
    expect(container.querySelectorAll('.chapter-mode-table-row')).toHaveLength(3)
    expect(container.querySelector('.chapter-mode-table-section')?.textContent).toBe('模式正确率')
    expect(screen.getByTitle('速记模式正确率 80%')).toBeInTheDocument()
    expect(screen.getByTitle('听写模式正确率 0%')).toBeInTheDocument()
    expect(screen.queryByText('记 10词')).toBeNull()
    expect(screen.queryByText('未覆盖 17词')).toBeNull()
    expect(screen.getAllByText('学习中')).toHaveLength(1)
    expect(screen.queryByText('已学 40%')).toBeNull()
    expect(screen.queryByTitle('默写模式正确率 0%')).toBeNull()
  })

  it('marks a chapter complete when learned coverage reaches the chapter total', async () => {
    mockChapterResponses(
      [{ id: 1, title: 'Unit 1', word_count: 50 }],
      {
        1: {
          is_completed: false,
          words_learned: 50,
          accuracy: 92,
          modes: {
            quickmemory: {
              mode: 'quickmemory',
              correct_count: 46,
              wrong_count: 4,
              accuracy: 92,
              is_completed: false,
            },
          },
        },
      },
    )

    render(
      <ChapterModal
        book={{ id: 'book-1', title: 'Test Book', word_count: 50 }}
        progress={{ current_index: 50 }}
        onClose={() => {}}
        onSelectChapter={() => {}}
      />,
    )

    expect(await screen.findAllByText('已完成')).toHaveLength(1)
    expect(screen.queryByText('已学 100%')).toBeNull()
    expect(screen.queryByText('学习中')).toBeNull()
  })

  it('uses a full-height skeleton inside the modal body while chapters are loading', () => {
    apiFetchMock.mockImplementation(() => new Promise(() => {}))

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
    mockChapterResponses([
      { id: 1, title: '音近词辨析 01', word_count: 120, group_count: 60 },
      { id: 2, title: '音近词辨析 02', word_count: 120, group_count: 60 },
    ])

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
    mockChapterResponses([{ id: 1, title: 'Unit 1', word_count: 30 }])
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
    await user.click(await screen.findByText('Unit 1'))

    expect(onSelectChapter).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1, title: 'Unit 1' }),
      0,
      'game',
    )
  })

  it('offers an edit entry for existing custom books', async () => {
    const user = userEvent.setup()
    mockChapterResponses([{ id: 'custom_1_1', title: '第1章', word_count: 20 }])

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

  it('uses the server distinct total for custom book subtitles', async () => {
    mockChapterResponses([
      { id: 'wrong_words_1_a', title: 'A', word_count: 20 },
      { id: 'wrong_words_1_manual', title: 'STR', word_count: 5 },
    ])

    render(
      <ChapterModal
        book={{ id: 'wrong_words_1', title: '错词本', word_count: 20, is_custom_book: true }}
        progress={{ current_index: 0 }}
        onClose={() => {}}
        onSelectChapter={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('2 章节 · 20 词')).toBeInTheDocument()
    })
  })
})
