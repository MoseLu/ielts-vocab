import React from 'react'
import { render, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import type { AppSettings, Word } from './types'

const apiFetchMock = vi.fn(() => Promise.resolve({}))
const showToastMock = vi.fn()
const logSessionMock = vi.fn()
const startSessionMock = vi.fn(() => Promise.resolve(1))
const cancelSessionMock = vi.fn(() => Promise.resolve())

vi.mock('./utils', () => ({
  playWordAudio: vi.fn(),
  stopAudio: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  logSession: (...args: unknown[]) => logSessionMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: (...args: unknown[]) => cancelSessionMock(...args),
}))

vi.mock('../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

describe('QuickMemoryMode', () => {
  const vocabulary: Word[] = [
    { word: 'apple', phonetic: '/ˈæpəl/', pos: 'n.', definition: 'fruit' },
  ]
  const settings: AppSettings = {}

  beforeEach(() => {
    apiFetchMock.mockClear()
    showToastMock.mockClear()
    logSessionMock.mockClear()
    startSessionMock.mockClear()
    cancelSessionMock.mockClear()
    localStorage.clear()
  })

  it('resets out of the summary screen when chapter context changes', async () => {
    const user = userEvent.setup()
    const { container, rerender } = render(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId="book-1"
        chapterId="1"
        bookChapters={[
          { id: '1', title: 'Chapter 1' },
          { id: '2', title: 'Chapter 2' },
        ]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).not.toBeNull()
    })

    rerender(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId="book-1"
        chapterId="2"
        bookChapters={[
          { id: '1', title: 'Chapter 1' },
          { id: '2', title: 'Chapter 2' },
        ]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).toBeNull()
      expect(container.querySelector('.qm-card')).not.toBeNull()
    })
  })

  it('cancels empty sessions when the user leaves before answering a word', async () => {
    const { unmount } = render(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await waitFor(() => {
      expect(startSessionMock).toHaveBeenCalled()
    })
    unmount()

    await waitFor(() => {
      expect(cancelSessionMock).toHaveBeenCalledWith(1)
      expect(logSessionMock).not.toHaveBeenCalled()
    })
  })

  it('logs a partial session when the user answered at least one word before leaving', async () => {
    const user = userEvent.setup()
    const { container, unmount } = render(
      <QuickMemoryMode
        vocabulary={[
          { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
          { word: 'banana', phonetic: '/banana/', pos: 'n.', definition: 'fruit' },
        ]}
        queue={[0, 1]}
        settings={settings}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    unmount()

    await waitFor(() => {
      expect(logSessionMock).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'quickmemory',
        wordsStudied: 1,
        correctCount: 1,
        wrongCount: 0,
        sessionId: 1,
      }))
    })
  })

  it('keeps review-mode context for sync without overwriting full chapter progress', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        reviewMode
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).not.toBeNull()
    })

    const syncCall = apiFetchMock.mock.calls.find(([url]) => url === '/api/ai/quick-memory/sync')
    expect(syncCall).toBeTruthy()
    const syncBody = JSON.parse(String((syncCall?.[1] as { body?: string })?.body ?? '{}'))
    expect(syncBody.records[0]).toMatchObject({
      word: 'apple',
      bookId: 'book-1',
      chapterId: '1',
    })

    const urls = apiFetchMock.mock.calls.map(([url]) => url)
    expect(urls).not.toContain('/api/books/progress')
    expect(urls).not.toContain('/api/books/book-1/chapters/1/progress')
    expect(urls).not.toContain('/api/books/book-1/chapters/1/mode-progress')
  })
})
