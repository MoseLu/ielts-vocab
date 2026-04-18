import React from 'react'
import { render, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import { STORAGE_KEYS } from '../../constants'

const apiFetchMock = vi.fn(() => Promise.resolve({}))

vi.mock('./utils', () => ({
  playSlowWordAudio: vi.fn(() => Promise.resolve(true)),
  playWordAudio: vi.fn(() => Promise.resolve(true)),
  preloadWordAudio: vi.fn(() => Promise.resolve(true)),
  preloadWordAudioBatch: vi.fn(() => Promise.resolve(true)),
  stopAudio: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  prepareStudySessionForLearningAction: undefined,
  finalizeStudySessionSegment: undefined,
  isStudySessionActive: undefined,
  resolveStudySessionDurationSeconds: () => 0,
  logSession: vi.fn(),
  startSession: vi.fn(() => Promise.resolve(1)),
  cancelSession: vi.fn(),
  flushStudySessionOnPageHide: vi.fn(),
  touchStudySessionActivity: vi.fn(),
  updateStudySessionSnapshot: vi.fn(),
}))

vi.mock('../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

describe('QuickMemoryMode partial chapter progress', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockResolvedValue({})
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 1 }))
  })

  it('syncs partial chapter progress to the backend before the round completes', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <QuickMemoryMode
        vocabulary={[
          { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
          { word: 'banana', phonetic: '/banana/', pos: 'n.', definition: 'fruit' },
        ]}
        queue={[0, 1]}
        settings={{}}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    await waitFor(() => expect(container.querySelector('.qm-btn-next')).not.toBeNull())
    await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/books/book-1/chapters/1/progress', {
        method: 'POST',
        body: JSON.stringify({
          current_index: 1,
          correct_count: 1,
          wrong_count: 0,
          words_learned: 1,
          is_completed: false,
          queue_words: ['apple', 'banana'],
        }),
      })
    })
  })
})
