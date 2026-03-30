import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import LearningJournalPage from './LearningJournalPage'

const apiFetchMock = vi.fn()

vi.mock('../lib', async () => {
  const actual = await vi.importActual<typeof import('../lib')>('../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('LearningJournalPage markdown rendering', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  it('renders the selected summary as markdown html without date filters', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({
          summaries: [
            {
              id: 1,
              date: '2026-03-26',
              content: '# Title --- ## 1. Overview | Item | Data | |------|------| | Mode | Radio | - First point',
              generated_at: '2026-03-26T14:28:00',
            },
          ],
        })
      }
      if (url.startsWith('/api/notes?')) {
        return Promise.resolve({
          notes: [],
          total: 0,
          per_page: 20,
          has_more: false,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    await waitFor(() => {
      expect(container.querySelector('.journal-doc-body table')).not.toBeNull()
    })

    expect(container.querySelector('.journal-doc-shell--summary .journal-doc-sidebar')).toBeNull()
    expect(container.querySelector('.journal-doc-body h1, .journal-doc-body h2')).not.toBeNull()
    expect(screen.queryByLabelText('开始日期')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('结束日期')).not.toBeInTheDocument()
    expect(screen.queryByText(/# Title/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '生成今日总结' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新生成' })).toBeInTheDocument()
  })

  it('renders note answers as markdown html in the history pane', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      if (url.startsWith('/api/notes?')) {
        return Promise.resolve({
          notes: [
            {
              id: 1,
              question: '这个词怎么记？',
              answer: '## 建议 - 分音节记忆 - 配合例句',
              word_context: 'attention',
              created_at: '2026-03-26T14:28:00',
            },
          ],
          total: 1,
          per_page: 20,
          has_more: false,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)
    await user.click(screen.getByRole('tab', { name: '问答历史' }))

    await waitFor(() => {
      expect(container.querySelector('.journal-note-detail-answer h2, .journal-note-detail-answer ul')).not.toBeNull()
    })

    expect(screen.getByLabelText('开始日期')).toBeInTheDocument()
    expect(screen.getByLabelText('结束日期')).toBeInTheDocument()
    expect(screen.queryByText(/## 建议/)).not.toBeInTheDocument()
  })

  it('shows generate action only when no summary exists', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      if (url.startsWith('/api/notes?')) {
        return Promise.resolve({
          notes: [],
          total: 0,
          per_page: 20,
          has_more: false,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(<LearningJournalPage />)

    expect(await screen.findByRole('button', { name: '生成今日总结' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '重新生成' })).not.toBeInTheDocument()
  })
})
