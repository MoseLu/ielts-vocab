import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import type { AppSettings, Word } from './types'
import { STORAGE_KEYS } from '../../constants'
import { getQuickMemoryStorageKey } from '../../lib/quickMemory'
const apiFetchMock = vi.fn(() => Promise.resolve({}))
const showToastMock = vi.fn()
const logSessionMock = vi.fn()
const startSessionMock = vi.fn(() => Promise.resolve(1))
const cancelSessionMock = vi.fn(() => Promise.resolve())
const flushStudySessionOnPageHideMock = vi.fn()
const touchStudySessionActivityMock = vi.fn()
const updateStudySessionSnapshotMock = vi.fn(); const playWordAudioMock = vi.fn(() => Promise.resolve(true))
const prepareWordAudioPlaybackMock = vi.fn(() => Promise.resolve(true))
const preloadWordAudioMock = vi.fn(() => Promise.resolve(true))
const stopAudioMock = vi.fn()
vi.mock('./utils', () => ({
  playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
  prepareWordAudioPlayback: (...args: unknown[]) => prepareWordAudioPlaybackMock(...args),
  preloadWordAudio: (...args: unknown[]) => preloadWordAudioMock(...args),
  preloadWordAudioBatch: (...args: unknown[]) => preloadWordAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))
vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  prepareStudySessionForLearningAction: undefined,
  finalizeStudySessionSegment: undefined,
  isStudySessionActive: undefined,
  resolveStudySessionDurationSeconds: (data: { startedAt: number; endedAt?: number; durationSeconds?: number }) =>
    data.durationSeconds ?? Math.max(0, Math.round(((data.endedAt ?? Date.now()) - data.startedAt) / 1000)),
  logSession: (...args: unknown[]) => logSessionMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: (...args: unknown[]) => cancelSessionMock(...args),
  flushStudySessionOnPageHide: (...args: unknown[]) => flushStudySessionOnPageHideMock(...args),
  touchStudySessionActivity: (...args: unknown[]) => touchStudySessionActivityMock(...args),
  updateStudySessionSnapshot: (...args: unknown[]) => updateStudySessionSnapshotMock(...args),
}))
vi.mock('../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))
vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

async function clickKnown(user: ReturnType<typeof userEvent.setup>, container: HTMLElement) {
  await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
  await waitFor(() => {
    expect(container.querySelector('.qm-card--reveal')).not.toBeNull()
  })
}

async function clickNext(user: ReturnType<typeof userEvent.setup>, container: HTMLElement) {
  await waitFor(() => {
    expect(container.querySelector('.qm-btn-next')).not.toBeNull()
  })
  await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)
}

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
    flushStudySessionOnPageHideMock.mockClear()
    touchStudySessionActivityMock.mockClear()
    updateStudySessionSnapshotMock.mockClear()
    playWordAudioMock.mockClear()
    playWordAudioMock.mockImplementation(() => Promise.resolve(true))
    prepareWordAudioPlaybackMock.mockClear()
    prepareWordAudioPlaybackMock.mockImplementation(() => Promise.resolve(true))
    preloadWordAudioMock.mockClear()
    preloadWordAudioMock.mockImplementation(() => Promise.resolve(true))
    stopAudioMock.mockClear()
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 1 }))
  })
  afterEach(() => { vi.useRealTimers() })
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
    expect(screen.getByText('你认识这个单词吗？')).toBeInTheDocument()
    await clickKnown(user, container)
    expect(screen.getByText('✓ 认识')).toBeInTheDocument()
    expect(screen.getByText('fruit')).toBeInTheDocument()
    await clickNext(user, container)
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

  it('does not open or cancel a session when the user leaves before any learning action', async () => {
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

    unmount()
    expect(startSessionMock).not.toHaveBeenCalled()
    expect(cancelSessionMock).not.toHaveBeenCalled()
    expect(logSessionMock).not.toHaveBeenCalled()
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

    await clickKnown(user, container)
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

  it('resets to the latest requested resume index within the same chapter', async () => {
    const { rerender } = render(
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
        initialIndex={1}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('banana')).toBeInTheDocument()
    })

    rerender(
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
        initialIndex={0}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('apple')).toBeInTheDocument()
    })
  })

  it('logs a completed review session before unmounting', async () => {
    const user = userEvent.setup()
    const { container, unmount } = render(
      <QuickMemoryMode
        vocabulary={[
          { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
          { word: 'banana', phonetic: '/banana/', pos: 'n.', definition: 'fruit' },
        ]}
        queue={[0, 1]}
        settings={settings}
        bookId={null}
        chapterId={null}
        bookChapters={[]}
        reviewMode
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await clickKnown(user, container)
    await clickNext(user, container)
    await waitFor(() => {
      expect(screen.getByText('banana')).toBeInTheDocument()
    })
    await clickKnown(user, container)
    await clickNext(user, container)

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).not.toBeNull()
      expect(logSessionMock).toHaveBeenCalledWith(expect.objectContaining({
        mode: 'quickmemory',
        bookId: null,
        chapterId: null,
        wordsStudied: 2,
        correctCount: 2,
        wrongCount: 0,
        sessionId: 1,
      }))
    })

    unmount()
    expect(logSessionMock).toHaveBeenCalledTimes(1)
  })

  it('flushes the full session quick-memory batch after a review round completes', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <QuickMemoryMode
        vocabulary={[
          { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
          { word: 'banana', phonetic: '/banana/', pos: 'n.', definition: 'fruit' },
        ]}
        queue={[0, 1]}
        settings={settings}
        bookId={null}
        chapterId={null}
        bookChapters={[]}
        reviewMode
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await clickKnown(user, container)
    await clickNext(user, container)
    await waitFor(() => {
      expect(screen.getByText('banana')).toBeInTheDocument()
    })
    await clickKnown(user, container)
    await clickNext(user, container)

    await waitFor(() => {
      const syncedWords = apiFetchMock.mock.calls
        .filter(([url]) => url === '/api/ai/quick-memory/sync')
        .flatMap(([, options]) => {
          const body = JSON.parse(String((options as { body?: string })?.body ?? '{}'))
          return Array.isArray(body.records)
            ? body.records.map((record: { word?: string }) => record.word).filter(Boolean)
            : []
        })

      expect(syncedWords).toEqual(expect.arrayContaining(['apple', 'banana']))
    })
  })

  it('retries failed quick-memory record sync while the practice page stays open', async () => {
    vi.useFakeTimers()
    let syncAttempts = 0
    const pendingKey = `${getQuickMemoryStorageKey(1)}:pending_sync`
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory') return Promise.resolve({ records: [] })
      if (url !== '/api/ai/quick-memory/sync') return Promise.resolve({})
      syncAttempts += 1
      return syncAttempts === 1 ? Promise.reject(new Error('offline')) : Promise.resolve({})
    })

    const { container } = render(
      <QuickMemoryMode {...{
        vocabulary, queue: [0], settings, bookId: null, chapterId: null, bookChapters: [],
        onModeChange: () => {}, onNavigate: () => {}, onWrongWord: () => {},
      }} />,
    )

    await act(async () => {
      fireEvent.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
      await Promise.resolve()
    })
    expect(localStorage.getItem(pendingKey)).toContain('apple')

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })

    expect(syncAttempts).toBeGreaterThanOrEqual(2)
    expect(localStorage.getItem(pendingKey)).toBeNull()
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

    await clickKnown(user, container)
    await clickNext(user, container)

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).not.toBeNull()
    })

    const syncCall = apiFetchMock.mock.calls.find(([url]) => url === '/api/ai/quick-memory/sync')
    expect(syncCall).toBeTruthy()
    const syncBody = JSON.parse(String((syncCall?.[1] as { body?: string })?.body ?? '{}'))
    expect(syncBody.source).toBe('quickmemory')
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

  it('pushes newer local quick-memory records back to the backend after merging older server snapshots', async () => {
    localStorage.setItem(getQuickMemoryStorageKey(1), JSON.stringify({
      apple: {
        status: 'known',
        firstSeen: 1000,
        lastSeen: 5000,
        knownCount: 2,
        unknownCount: 0,
        nextReview: 9000,
        fuzzyCount: 0,
        bookId: 'book-1',
        chapterId: '1',
      },
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory') {
        return Promise.resolve({
          records: [{
            word: 'apple',
            status: 'known',
            firstSeen: 1000,
            lastSeen: 3000,
            knownCount: 1,
            unknownCount: 0,
            nextReview: 6000,
            fuzzyCount: 0,
            bookId: 'book-1',
            chapterId: '1',
          }],
        })
      }

      if (url === '/api/ai/quick-memory/sync') {
        return Promise.resolve({})
      }

      return Promise.resolve({})
    })

    render(
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
      const syncCall = apiFetchMock.mock.calls.find(([url, options]) => {
        if (url !== '/api/ai/quick-memory/sync') return false
        const body = JSON.parse(String((options as { body?: string })?.body ?? '{}'))
        return body.records?.[0]?.word === 'apple' && body.records?.[0]?.lastSeen === 5000
      })

      expect(syncCall).toBeTruthy()
    })
  })

  it('stores chapter completion without writing book-level completion for chapter sessions', async () => {
    const user = userEvent.setup()
    const { container } = render(
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

    await clickKnown(user, container)
    await clickNext(user, container)

    await waitFor(() => {
      expect(container.querySelector('.qm-summary')).not.toBeNull()
    })

    const urls = apiFetchMock.mock.calls.map(([url]) => url)
    expect(urls).not.toContain('/api/books/progress')
    expect(urls).toContain('/api/books/book-1/chapters/1/progress')
    expect(urls).toContain('/api/books/book-1/chapters/1/mode-progress')

    const storedProgress = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
    expect(storedProgress['book-1_1']).toMatchObject({
      current_index: 1,
      correct_count: 1,
      wrong_count: 0,
      words_learned: 1,
      is_completed: true,
    })
  })
})
