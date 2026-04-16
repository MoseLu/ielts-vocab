import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GlobalWordSearchDetailPanel from './GlobalWordSearchDetailPanel'

const apiFetchMock = vi.fn()
const playWordAudioMock = vi.fn()
const playExampleAudioMock = vi.fn()
const stopAudioMock = vi.fn()
const toggleFavoriteMock = vi.fn()

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('../../../contexts', () => ({
  useAuth: () => ({ user: { id: 1, username: 'admin' } }),
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useFavoriteWords: () => ({
    isFavorite: () => false,
    isPending: () => false,
    toggleFavorite: toggleFavoriteMock,
  }),
}))

vi.mock('../../practice/utils', () => ({
  playExampleAudio: (...args: unknown[]) => playExampleAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))

vi.mock('../../practice/utils.audio', () => ({
  playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
}))

describe('GlobalWordSearchDetailPanel audio interactions', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    playWordAudioMock.mockReset()
    playExampleAudioMock.mockReset()
    stopAudioMock.mockReset()
    toggleFavoriteMock.mockReset()
    localStorage.clear()
  })

  it('replays the current word when clicking the heading or switching tabs', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ playbackSpeed: '1.25', volume: '80' }))
    apiFetchMock.mockResolvedValue({
      word: 'quit',
      phonetic: '/kwɪt/',
      pos: 'v.',
      definition: '停止；离开',
      root: {
        word: 'quit',
        normalized_word: 'quit',
        segments: [{ kind: '词根', text: 'quit', meaning: '当前词形本身就是核心记忆单元' }],
        summary: '当前没有命中常见前后缀，可以直接把 quit 作为核心词形记忆。',
        source: 'generated',
        updated_at: null,
      },
      english: {
        word: 'quit',
        normalized_word: 'quit',
        entries: [{ pos: 'v.', definition: 'to stop doing something' }],
        source: 'llm',
        updated_at: null,
      },
      examples: [{ en: 'She decided to quit her job before the exam season.', zh: '她决定在考试季前辞职。', source: 'llm', sort_order: 0 }],
      derivatives: [],
      note: { word: 'quit', content: '', updated_at: null },
    })

    render(
      <GlobalWordSearchDetailPanel
        query="quit"
        result={{
          word: 'quit',
          phonetic: '/kwɪt/',
          pos: 'v.',
          definition: '停止；离开',
          book_id: 'book-a',
          book_title: 'Book A',
          match_type: 'exact',
          examples: [{ en: 'She decided to quit her job before the exam season.', zh: '她决定在考试季前辞职。' }],
        }}
        onPickWord={() => {}}
      />,
    )

    await screen.findByText('她决定在考试季前辞职。')

    fireEvent.click(screen.getByRole('button', { name: '播放 quit 发音' }))
    expect(playWordAudioMock).toHaveBeenLastCalledWith('quit', { playbackSpeed: '1.25', volume: '80' })

    fireEvent.click(screen.getByRole('tab', { name: '英义' }))
    expect(playWordAudioMock).toHaveBeenLastCalledWith('quit', { playbackSpeed: '1.25', volume: '80' })
  })
})
