import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AdminDashboard from './AdminDashboard'

const apiFetchMock = vi.fn()

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

describe('AdminDashboard', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  it('shows a stats page skeleton while overview data is still loading', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') {
        return new Promise(() => {})
      }

      if (url.startsWith('/api/admin/users?')) {
        return Promise.resolve({
          users: [],
          total: 0,
          pages: 1,
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    const { container } = render(<AdminDashboard />)

    await waitFor(() => {
      expect(container.querySelector('.page-skeleton--admin')).not.toBeNull()
    })

    expect(container.querySelectorAll('.page-skeleton--admin .page-skeleton-card--metric')).toHaveLength(4)
    expect(container.querySelector('.admin-loading')).toBeNull()
  })

  it('shows a table skeleton while user rows are still loading', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') {
        return Promise.resolve({
          total_users: 0,
          active_users_today: 0,
          active_users_7d: 0,
          new_users_today: 0,
          new_users_7d: 0,
          total_sessions: 0,
          total_study_seconds: 0,
          total_words_studied: 0,
          avg_accuracy: 0,
          daily_activity: [],
          mode_stats: [],
          top_books: [],
        })
      }

      if (url.startsWith('/api/admin/users?')) {
        return new Promise(() => {})
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    const { container } = render(<AdminDashboard />)

    fireEvent.click(screen.getByRole('tab', { name: /用户管理/i }))

    await waitFor(() => {
      expect(container.querySelector('.admin-table-skeleton')).not.toBeNull()
    })

    expect(container.querySelector('.admin-loading-cell')).toBeNull()
  })

  it('shows card skeletons while tts books are still loading', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') {
        return Promise.resolve({
          total_users: 0,
          active_users_today: 0,
          active_users_7d: 0,
          new_users_today: 0,
          new_users_7d: 0,
          total_sessions: 0,
          total_study_seconds: 0,
          total_words_studied: 0,
          avg_accuracy: 0,
          daily_activity: [],
          mode_stats: [],
          top_books: [],
        })
      }

      if (url.startsWith('/api/admin/users?')) {
        return Promise.resolve({
          users: [],
          total: 0,
          pages: 1,
        })
      }

      if (url === '/api/tts/books-summary') {
        return new Promise(() => {})
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    const { container } = render(<AdminDashboard />)

    fireEvent.click(screen.getByRole('tab', { name: /词书音频/i }))

    await waitFor(() => {
      expect(container.querySelector('.admin-tts-skeleton')).not.toBeNull()
    })

    expect(container.querySelector('.loading-spinner')).toBeNull()
  })

  it('shows session detail with time range, content summary, and total duration', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') {
        return Promise.resolve({
          total_users: 1,
          active_users_today: 1,
          active_users_7d: 1,
          new_users_today: 1,
          new_users_7d: 1,
          total_sessions: 1,
          total_study_seconds: 900,
          total_words_studied: 12,
          avg_accuracy: 75,
          daily_activity: [],
          mode_stats: [],
          top_books: [],
        })
      }

      if (url.startsWith('/api/admin/users?')) {
        return Promise.resolve({
          users: [{
            id: 1,
            username: 'learner',
            email: 'learner@example.com',
            avatar_url: null,
            is_admin: false,
            created_at: '2026-04-01T08:00:00',
            stats: {
              total_correct: 9,
              total_wrong: 3,
              accuracy: 75,
              books_in_progress: 1,
              books_completed: 0,
              total_study_seconds: 900,
              total_words_studied: 12,
              wrong_words_count: 3,
              session_count: 1,
              recent_sessions_7d: 1,
              last_active: '2026-04-01T09:15:00',
            },
          }],
          total: 1,
          pages: 1,
        })
      }

      if (url === '/api/admin/users/1') {
        return Promise.resolve({
          user: {
            id: 1,
            username: 'learner',
            email: 'learner@example.com',
            avatar_url: null,
            is_admin: false,
            created_at: '2026-04-01T08:00:00',
            stats: {
              total_correct: 9,
              total_wrong: 3,
              accuracy: 75,
              books_in_progress: 1,
              books_completed: 0,
              total_study_seconds: 900,
              total_words_studied: 12,
              wrong_words_count: 3,
              session_count: 1,
              recent_sessions_7d: 1,
              last_active: '2026-04-01T09:15:00',
            },
          },
          book_progress: [],
          wrong_words: [],
          daily_study: [],
          chapter_daily: [],
          sessions: [{
            id: 101,
            mode: 'quickmemory',
            book_id: 'ielts_listening_premium',
            chapter_id: '44',
            words_studied: 12,
            correct_count: 9,
            wrong_count: 3,
            accuracy: 75,
            duration_seconds: 900,
            started_at: '2026-04-01T09:00:00',
            ended_at: '2026-04-01T09:15:00',
            studied_words: ['campaign', 'engine', 'satellite'],
            studied_words_total: 3,
          }],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<AdminDashboard />)

    fireEvent.click(screen.getByRole('tab', { name: /用户管理/i }))
    fireEvent.click(await screen.findByText('learner'))
    fireEvent.click(await screen.findByText('学习明细'))

    await waitFor(() => {
      expect(screen.getByText('09:00 - 09:15')).toBeInTheDocument()
    })

    const sessionRow = screen.getByText('09:00 - 09:15').closest('tr')
    expect(sessionRow).not.toBeNull()
    expect(sessionRow).toHaveTextContent('15分钟')
    expect(screen.getByText('雅思听力精讲 · 第44章 · 速记模式')).toBeInTheDocument()
    expect(screen.getByText('共练习 12 词')).toBeInTheDocument()
    expect(screen.getByText('campaign、engine、satellite')).toBeInTheDocument()
  })
})
