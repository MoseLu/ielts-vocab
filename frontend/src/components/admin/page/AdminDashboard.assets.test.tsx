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

const overview = {
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
}

const userPage = {
  users: [],
  total: 0,
  pages: 1,
}

const assetPage = {
  items: [{
    id: 'asset:accommodation',
    book_id: 'ielts_reading_premium',
    book_title: '雅思阅读高频词汇',
    source_book_ids: ['ielts_reading_premium', 'ielts_listening_premium'],
    source_book_titles: ['雅思阅读高频词汇', '雅思听力高频词汇'],
    chapter_id: '1',
    chapter_title: '150次及以上',
    word: 'accommodation',
    normalized_word: 'accommodation',
    phonetic: '/əˌkɒməˈdeɪʃn/',
    pos: 'n.',
    definition: '住处；住宿安排',
    memory_badge: '词根词缀',
    memory_text: 'accommodate 是“容纳/提供住宿”，accommodation 就是住处或住宿安排。',
    memory_source: 'premium_word_mnemonics',
    memory_updated_at: '2026-04-30T00:00:00+08:00',
    has_mnemonic: true,
  }],
  total: 21,
  pages: 2,
  summary: {
    total_words: 5493,
    with_mnemonic: 5493,
    missing_mnemonic: 0,
  },
}

describe('AdminDashboard assets tab', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    useAuthMock.mockReset()
    useAuthMock.mockReturnValue({ user: null })
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/admin/overview') return Promise.resolve(overview)
      if (url.startsWith('/api/admin/users?')) return Promise.resolve(userPage)
      if (url.startsWith('/api/admin/assets/words?')) return Promise.resolve(assetPage)
      throw new Error(`Unexpected request: ${url}`)
    })
  })

  it('loads paid-book word assets and applies filters through the admin API', async () => {
    render(<AdminDashboard />)

    fireEvent.click(screen.getByRole('tab', { name: /资产管理/i }))

    expect(await screen.findByText('accommodation')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: '助记类型' })).toBeInTheDocument()
    expect(screen.getByText('accommodate 是“容纳/提供住宿”，accommodation 就是住处或住宿安排。')).toBeInTheDocument()
    expect(screen.queryByText('150次及以上')).not.toBeInTheDocument()
    expect(apiFetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/admin/assets/words?page=1'))

    fireEvent.change(screen.getByPlaceholderText('搜索单词、释义或助记...'), {
      target: { value: 'demo' },
    })
    fireEvent.click(screen.getByRole('button', { name: '搜索' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(expect.stringContaining('search=demo'))
    })

    const [bookSelect, mnemonicSelect] = screen.getAllByRole('combobox')
    fireEvent.change(bookSelect, { target: { value: 'ielts_reading_premium' } })
    fireEvent.change(mnemonicSelect, { target: { value: 'missing_mnemonic' } })
    fireEvent.click(screen.getByRole('button', { name: '下一页' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(expect.stringContaining('book_id=ielts_reading_premium'))
      expect(apiFetchMock).toHaveBeenCalledWith(expect.stringContaining('mnemonic_status=missing_mnemonic'))
      expect(apiFetchMock).toHaveBeenCalledWith(expect.stringContaining('page=2'))
    })
  })
})
