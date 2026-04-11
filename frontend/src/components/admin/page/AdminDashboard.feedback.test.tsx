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

const buildOverview = () => ({
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

const buildUserPage = () => ({
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

describe('AdminDashboard feedback tab', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    useAuthMock.mockReset()
    useAuthMock.mockReturnValue({ user: null })
  })

  it('loads the word feedback tab as a dedicated admin module', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') {
        return Promise.resolve(buildOverview())
      }

      if (url.startsWith('/api/admin/users?')) {
        return Promise.resolve(buildUserPage())
      }

      if (url === '/api/admin/word-feedback?limit=50') {
        return Promise.resolve({
          total: 1,
          items: [{
            id: 1,
            user_id: 7,
            username: 'learner',
            email: 'learner@example.com',
            word: 'quit',
            phonetic: '/kwɪt/',
            pos: 'v.',
            definition: '停止；离开',
            example_en: 'He decided to quit last year.',
            example_zh: '他去年决定辞职。',
            source_book_id: 'ielts_listening_premium',
            source_book_title: '雅思听力精讲',
            source_chapter_id: '2',
            source_chapter_title: '第2章',
            feedback_types: ['translation'],
            feedback_type_labels: ['翻译不准'],
            source: 'global_search',
            status: 'open',
            comment: '',
            created_at: '2026-04-11T12:30:00+00:00',
            updated_at: '2026-04-11T12:30:00+00:00',
          }],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<AdminDashboard />)

    fireEvent.click(screen.getByRole('tab', { name: /问题反馈/i }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/admin/word-feedback?limit=50')
    })

    expect(await screen.findByText('最近单词卡片反馈')).toBeInTheDocument()
    expect(screen.getByText('翻译不准')).toBeInTheDocument()
    expect(screen.getByText('单词搜索卡片')).toBeInTheDocument()
    expect(screen.getByText('He decided to quit last year.')).toBeInTheDocument()
  })
})
