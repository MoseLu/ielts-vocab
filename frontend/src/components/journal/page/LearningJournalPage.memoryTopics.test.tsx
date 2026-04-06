import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import LearningJournalPage from './LearningJournalPage'

const apiFetchMock = vi.fn()

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('LearningJournalPage memory topics', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  it('uses backend memory topics to render note memory cues beyond the current page', async () => {
    const user = userEvent.setup()

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      if (url.startsWith('/api/notes?')) {
        return Promise.resolve({
          notes: [
            {
              id: 2,
              question: 'kind of 和 a kind of 还是分不清',
              answer: '## Tips\n\n- 看句法位置',
              word_context: 'kind',
              created_at: '2026-03-30T10:00:00',
            },
          ],
          total: 3,
          per_page: 20,
          has_more: false,
          memory_topics: [
            {
              key: 'word:kind',
              title: 'kind of 和 a kind of',
              count: 3,
              word_context: 'kind',
              latest_answer: '第三次解释',
              latest_at: '2026-03-30T10:00:00',
              note_ids: [1, 2, 3],
              follow_up_hint: '这个问题已经重复出现，AI 应主动追问是否还需要进一步辨析。',
              related_notes: [
                {
                  id: 1,
                  question: 'Earlier memory question',
                  answer: '第一次解释',
                  word_context: 'kind',
                  created_at: '2026-03-29T10:00:00',
                },
                {
                  id: 3,
                  question: 'Another older question',
                  answer: '第二次解释',
                  word_context: 'kind',
                  created_at: '2026-03-28T10:00:00',
                },
              ],
            },
          ],
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)
    const tabs = await screen.findAllByRole('tab')
    await user.click(tabs[1])

    await waitFor(() => {
      expect(container.querySelector('.journal-note-detail-answer')).not.toBeNull()
    })

    expect(screen.getByText('当前主题已追问 3 次')).toBeInTheDocument()
    expect(screen.getByText('Earlier memory question')).toBeInTheDocument()
  })
})
