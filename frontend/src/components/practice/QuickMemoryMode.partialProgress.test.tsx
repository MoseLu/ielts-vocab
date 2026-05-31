import React from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import { STORAGE_KEYS } from '../../constants'

const apiFetchMock = vi.fn(() => Promise.resolve({}))

vi.mock('./utils', () => ({
  playSlowWordAudio: vi.fn(() => Promise.resolve(true)),
  playWordAudio: vi.fn(() => Promise.resolve(true)),
  prepareWordAudioPlayback: vi.fn(() => Promise.resolve(true)),
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
          mode: 'quickmemory',
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

  it('does not repost the same partial snapshot across incidental rerenders', async () => {
    const user = userEvent.setup()
    const vocabulary = [
      { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
      { word: 'banana', phonetic: '/banana/', pos: 'n.', definition: 'fruit' },
    ]
    const progressUrl = '/api/books/book-1/chapters/1/progress'
    const progressCalls = () => apiFetchMock.mock.calls.filter(([url]) => url === progressUrl)
    const renderSubject = (favoriteSlot?: React.ReactNode) => (
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0, 1]}
        settings={{}}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        favoriteSlot={favoriteSlot}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />
    )

    const { container, rerender } = render(renderSubject())

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    await waitFor(() => expect(container.querySelector('.qm-btn-next')).not.toBeNull())
    await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await waitFor(() => {
      expect(progressCalls()).toHaveLength(1)
    })

    await act(async () => {
      rerender(renderSubject(<span>saved</span>))
    })

    expect(progressCalls()).toHaveLength(1)
  })

  it('keeps grouped chapter progress open after a quick-memory batch completes', async () => {
    const user = userEvent.setup()
    const onContinueChapterGroup = vi.fn()
    const vocabulary = [
      { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
      { word: 'banana', phonetic: '/banana/', pos: 'n.', definition: 'fruit' },
      { word: 'cherry', phonetic: '/cherry/', pos: 'n.', definition: 'fruit' },
    ]
    const { container } = render(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={{}}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }, { id: '2', title: 'Chapter 2' }]}
        chapterGroup={{ start: 0, end: 1, total: 3, groupSize: 1 }}
        chapterQueueWords={['apple', 'banana', 'cherry']}
        onContinueChapterGroup={onContinueChapterGroup}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    await waitFor(() => expect(container.querySelector('.qm-btn-next')).not.toBeNull())
    await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).not.toBeNull()
      expect(screen.getByText('当前分组已完成，还可以继续练习 2 个本章单词。')).toBeInTheDocument()
    })

    const progressCall = apiFetchMock.mock.calls.find(([url]) => url === '/api/books/book-1/chapters/1/progress')
    const progressBody = JSON.parse(String((progressCall?.[1] as { body?: string })?.body ?? '{}'))
    expect(progressBody).toMatchObject({
      mode: 'quickmemory',
      current_index: 1,
      correct_count: 1,
      wrong_count: 0,
      words_learned: 1,
      is_completed: false,
      queue_words: ['apple', 'banana', 'cherry'],
    })

    const modeProgressCall = apiFetchMock.mock.calls.find(([url]) => url === '/api/books/book-1/chapters/1/mode-progress')
    const modeProgressBody = JSON.parse(String((modeProgressCall?.[1] as { body?: string })?.body ?? '{}'))
    expect(modeProgressBody).toMatchObject({
      mode: 'quickmemory',
      correct_count: 1,
      wrong_count: 0,
      is_completed: false,
    })

    await user.click(screen.getByRole('button', { name: /继续下一组/ }))
    expect(onContinueChapterGroup).toHaveBeenCalledTimes(1)
  })

  it('does not sync an empty partial snapshot when resuming at a saved index', async () => {
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
        initialIndex={1}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await waitFor(() => {
      expect(container.querySelector('.qm-progress-label')).toHaveTextContent('2 / 2')
    })

    expect(apiFetchMock).not.toHaveBeenCalledWith('/api/books/book-1/chapters/1/progress', {
      method: 'POST',
      body: JSON.stringify({
        mode: 'quickmemory',
        current_index: 1,
        correct_count: 0,
        wrong_count: 0,
        words_learned: 1,
        is_completed: false,
        queue_words: ['apple', 'banana'],
      }),
    })
  })
})
