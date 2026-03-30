import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AdminDashboard from './AdminDashboard'

const apiFetchMock = vi.fn()

vi.mock('../lib', () => ({
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
})
