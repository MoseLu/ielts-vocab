import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LearningJournalPage from './LearningJournalPage'

const apiFetchMock = vi.fn()

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('@tiptap/react', () => ({
  EditorContent: ({ className }: { className?: string }) => (
    <div className={className}>
      <div className="journal-editor-content" />
    </div>
  ),
  useEditor: (config: { content?: string }) => ({
    commands: { setContent: vi.fn() },
    getHTML: () => config.content || '<p></p>',
    view: {
      dom: {
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    },
  }),
}))

describe('LearningJournalPage history notebook', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  it('opens a historical diary entry from the notebook list', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({ entry: null })
      }
      if (url.startsWith('/api/notes/journal?')) {
        return Promise.resolve({
          entries: [
            {
              id: 2,
              date: '2026-06-02',
              content: '## 昨日复盘\n\n- 复习 kind of',
              polished_content: null,
              created_at: '2026-06-02T10:00:00',
              updated_at: '2026-06-02T10:30:00',
            },
          ],
          has_more: false,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)
    await user.click(await screen.findByRole('tab', { name: '历史笔记' }))
    await user.click(await screen.findByText('2026-06-02'))

    expect(screen.getByRole('button', { name: '返回列表' })).toBeInTheDocument()
    expect(container.querySelector('.journal-doc-title')?.textContent).toContain('2026-06-02 笔记')
    expect(container.querySelector('.journal-doc-body h2')?.textContent).toContain('昨日复盘')
  })
})
