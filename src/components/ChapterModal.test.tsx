import React from 'react'
import { render, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import ChapterModal from './ChapterModal'

const apiFetchMock = vi.fn()

vi.mock('../contexts', () => ({
  useAuth: () => ({ user: { id: 1 } }),
}))

vi.mock('../lib', async () => {
  const actual = await vi.importActual<typeof import('../lib')>('../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('./ui/Scrollbar', () => ({
  Scrollbar: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}))

describe('ChapterModal', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
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
})
