import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import LearningJournalPage from './LearningJournalPage'

const apiFetchMock = vi.fn()
const todayString = () => new Date().toISOString().slice(0, 10)

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
    vi.spyOn(window, 'alert').mockImplementation(() => {})
  })

  it('shows a page loading gate before the first summary payload resolves', async () => {
    let resolveSummaries: ((value: { summaries: never[] }) => void) | null = null

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return new Promise(resolve => {
          resolveSummaries = resolve
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    expect(container.querySelector('.page-skeleton--journal')).not.toBeNull()
    expect(container.querySelector('.journal-page')).toBeNull()

    resolveSummaries?.({ summaries: [] })

    await waitFor(() => {
      expect(container.querySelector('.journal-page')).not.toBeNull()
    })
  })

  it('renders the selected summary as markdown html without date filters', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({
          summaries: [
            {
              id: 1,
              date: '2026-03-26',
              content: '# Title\n\n## Overview\n\n| Item | Data |\n| --- | --- |\n| Mode | Radio |\n\n- First point',
              generated_at: '2026-03-26T14:28:00',
            },
          ],
        })
      }
      if (url === '/api/ai/learner-profile?date=2026-03-26') {
        return Promise.resolve({
          date: '2026-03-26',
          summary: {
            date: '2026-03-26',
            today_words: 20,
            today_accuracy: 85,
            today_duration_seconds: 1200,
            today_sessions: 2,
            streak_days: 5,
            weakest_mode: 'meaning',
            weakest_mode_label: '汉译英',
            weakest_mode_accuracy: 68,
            due_reviews: 3,
            trend_direction: 'improving',
          },
          dimensions: [
            {
              dimension: 'meaning',
              label: '汉译英（会想）',
              correct: 8,
              wrong: 4,
              attempts: 12,
              accuracy: 67,
              weakness: 0.3333,
            },
          ],
          focus_words: [
            {
              word: 'kind',
              definition: 'type',
              wrong_count: 3,
              dominant_dimension: 'meaning',
              dominant_dimension_label: '汉译英（会想）',
              dominant_wrong: 2,
              focus_score: 8,
            },
          ],
          repeated_topics: [
            {
              title: 'kind of vs a kind of',
              count: 2,
              word_context: 'kind',
              latest_answer: '...',
              latest_at: '2026-03-26T14:28:00',
            },
          ],
          next_actions: ['优先复习 3 个已到期的速记单词。'],
          memory_system: {},
          mode_breakdown: [],
          activity_summary: {
            total_events: 0,
            study_sessions: 0,
            quick_memory_reviews: 0,
            wrong_word_records: 0,
            assistant_questions: 0,
            chapter_updates: 0,
            books_touched: 0,
            chapters_touched: 0,
            words_touched: 0,
            total_duration_seconds: 0,
            correct_count: 0,
            wrong_count: 0,
          },
          activity_source_breakdown: [],
          recent_activity: [],
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    await waitFor(() => {
      expect(container.querySelector('.journal-doc-body h1, .journal-doc-body h2, .journal-doc-body ul')).not.toBeNull()
    })

    expect(container.querySelector('.journal-doc-shell--summary .journal-doc-sidebar')).toBeNull()
    expect(container.querySelector('.journal-doc-body h1, .journal-doc-body h2')).not.toBeNull()
    expect(container.querySelector('#journal-start-date')).toBeNull()
    expect(container.querySelector('#journal-end-date')).toBeNull()
    expect(screen.queryByText(/# Title/)).not.toBeInTheDocument()
    expect(container.querySelector('.journal-generate-btn')).toBeNull()
    expect(container.querySelector('.journal-regen-btn')).not.toBeNull()
    expect(await screen.findByText('统一学习画像')).toBeInTheDocument()
    expect(await screen.findByText('kind of vs a kind of')).toBeInTheDocument()
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
              question: 'How should I remember attention?',
              answer: '## Tips\n\n- Break it into syllables\n- Review it in a sentence',
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
    const tabs = await screen.findAllByRole('tab')
    await user.click(tabs[1])

    await waitFor(() => {
      expect(container.querySelector('.journal-note-detail-answer h2, .journal-note-detail-answer ul')).not.toBeNull()
    })

    expect(container.querySelector('#journal-start-date')).not.toBeNull()
    expect(container.querySelector('#journal-end-date')).not.toBeNull()
    expect(screen.queryByText(/## Tips/)).not.toBeInTheDocument()
  })

  it('shows generate action only when no summary exists', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    await waitFor(() => {
      expect(container.querySelector('.journal-generate-btn')).not.toBeNull()
    })
    expect(container.querySelector('.journal-regen-btn')).toBeNull()
  })

  it('renders summary generation progress from the dedicated job api', async () => {
    const user = userEvent.setup()
    const jobDate = todayString()

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      if (url === '/api/notes/summaries/generate-jobs') {
        return Promise.resolve({
          job_id: 'job-1',
          date: jobDate,
          status: 'queued',
          progress: 4,
          message: 'Preparing summary...',
          estimated_chars: 800,
          generated_chars: 0,
          summary: null,
          error: null,
        })
      }
      if (url === '/api/notes/summaries/generate-jobs/job-1') {
        return Promise.resolve({
          job_id: 'job-1',
          date: jobDate,
          status: 'running',
          progress: 42,
          message: 'Generating body...',
          estimated_chars: 800,
          generated_chars: 336,
          summary: null,
          error: null,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    const generateButton = await waitFor(() => {
      const button = container.querySelector<HTMLButtonElement>('.journal-generate-btn')
      expect(button).not.toBeNull()
      return button
    })
    await user.click(generateButton!)

    await waitFor(() => {
      const headerProgress = container.querySelector('.journal-summary-progress')
      const panelProgress = container.querySelector('.journal-summary-progress-panel')

      expect(headerProgress?.textContent).toContain('42%')
      expect(headerProgress?.textContent).toContain('Generating body...')
      expect(panelProgress?.textContent).toContain('42%')
      expect(panelProgress?.textContent).toContain('Generating body...')
    })
  })

  it('applies completed summaries returned by the job api', async () => {
    const user = userEvent.setup()
    const jobDate = todayString()

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      if (url === '/api/notes/summaries/generate-jobs') {
        return Promise.resolve({
          job_id: 'job-complete',
          date: jobDate,
          status: 'queued',
          progress: 5,
          message: 'Preparing summary...',
          estimated_chars: 800,
          generated_chars: 0,
          summary: null,
          error: null,
        })
      }
      if (url === '/api/notes/summaries/generate-jobs/job-complete') {
        return Promise.resolve({
          job_id: 'job-complete',
          date: jobDate,
          status: 'completed',
          progress: 100,
          message: 'Completed',
          estimated_chars: 800,
          generated_chars: 812,
          summary: {
            id: 5,
            date: jobDate,
            content: '# Summary',
            generated_at: '2026-03-30T12:30:00',
          },
          error: null,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    const generateButton = await waitFor(() => {
      const button = container.querySelector<HTMLButtonElement>('.journal-generate-btn')
      expect(button).not.toBeNull()
      return button
    })
    await user.click(generateButton!)

    await waitFor(() => {
      expect(container.querySelector('.journal-doc-title')?.textContent).toContain(jobDate)
    })
  })

  it('surfaces job polling errors in the page instead of using alert', async () => {
    const user = userEvent.setup()
    const alertSpy = vi.spyOn(window, 'alert')
    const jobDate = todayString()

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/summaries') {
        return Promise.resolve({ summaries: [] })
      }
      if (url === '/api/notes/summaries/generate-jobs') {
        return Promise.resolve({
          job_id: 'job-2',
          date: jobDate,
          status: 'queued',
          progress: 3,
          message: 'Preparing summary...',
          estimated_chars: 800,
          generated_chars: 0,
          summary: null,
          error: null,
        })
      }
      if (url === '/api/notes/summaries/generate-jobs/job-2') {
        return Promise.resolve({
          job_id: 'job-2',
          date: jobDate,
          status: 'failed',
          progress: 45,
          message: 'Generation failed.',
          estimated_chars: 800,
          generated_chars: 250,
          summary: null,
          error: 'Try again in 5 minutes',
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    const generateButton = await waitFor(() => {
      const button = container.querySelector<HTMLButtonElement>('.journal-generate-btn')
      expect(button).not.toBeNull()
      return button
    })
    await user.click(generateButton!)

    await screen.findByText('Try again in 5 minutes')
    expect(alertSpy).not.toHaveBeenCalled()
  })
})
