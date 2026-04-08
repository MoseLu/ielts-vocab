import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminDashboard from './AdminDashboard'

const { useAuthMock } = vi.hoisted(() => ({
  useAuthMock: vi.fn(() => ({ user: null })),
}))

const apiFetchMock = vi.fn()

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../../contexts', () => ({
  useAuth: () => useAuthMock(),
}))

describe('AdminDashboard admin identity', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    useAuthMock.mockReset()
    useAuthMock.mockReturnValue({
      user: { id: 7, avatar_url: 'https://example.com/admin.png' },
    })
  })

  it('uses the current admin avatar fallback and removes the admin badge', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') {
        return Promise.resolve({
          total_users: 1,
          active_users_today: 1,
          active_users_7d: 1,
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
          users: [{
            id: 7,
            username: 'admin',
            email: 'admin@example.com',
            avatar_url: null,
            is_admin: true,
            created_at: '2026-04-01T08:00:00',
            stats: {
              total_correct: 0,
              total_wrong: 0,
              accuracy: 0,
              books_in_progress: 0,
              books_completed: 0,
              total_study_seconds: 0,
              total_words_studied: 0,
              wrong_words_count: 0,
              session_count: 0,
              recent_sessions_7d: 0,
              last_active: null,
            },
          }],
          total: 1,
          pages: 1,
        })
      }

      if (url.startsWith('/api/admin/users/7')) {
        return Promise.resolve({
          user: {
            id: 7,
            username: 'admin',
            email: 'admin@example.com',
            avatar_url: null,
            is_admin: true,
            created_at: '2026-04-01T08:00:00',
            stats: {
              total_correct: 0,
              total_wrong: 0,
              accuracy: 0,
              books_in_progress: 0,
              books_completed: 0,
              total_study_seconds: 0,
              total_words_studied: 0,
              wrong_words_count: 0,
              session_count: 0,
              recent_sessions_7d: 0,
              last_active: null,
            },
          },
          book_progress: [],
          wrong_words: [],
          favorite_words: [],
          daily_study: [],
          chapter_daily: [],
          sessions: [],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    const { container } = render(<AdminDashboard />)

    fireEvent.click(screen.getByRole('tab', { name: /用户管理/i }))

    await waitFor(() => {
      expect(container.querySelector('.admin-user-name--admin')).not.toBeNull()
    })

    const rowAvatar = container.querySelector('.admin-avatar') as HTMLImageElement | null
    expect(rowAvatar?.getAttribute('src')).toBe('https://example.com/admin.png')
    expect(container.querySelector('.admin-badge')).toBeNull()

    fireEvent.click(await screen.findByText('admin'))

    await waitFor(() => {
      expect(container.querySelector('.admin-modal-username-hl--admin')).not.toBeNull()
    })

    const modalAvatar = container.querySelector('.admin-modal-avatar') as HTMLImageElement | null
    expect(modalAvatar?.getAttribute('src')).toBe('https://example.com/admin.png')
    expect(container.querySelector('.admin-badge')).toBeNull()
  })
})
