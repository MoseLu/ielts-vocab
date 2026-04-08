import { act, fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import type { AppSettings, Word } from './types'
import { STORAGE_KEYS } from '../../constants'

const apiFetchMock = vi.fn(() => Promise.resolve({}))
const showToastMock = vi.fn()
const logSessionMock = vi.fn()
const startSessionMock = vi.fn(() => Promise.resolve(1))
const cancelSessionMock = vi.fn(() => Promise.resolve())
const flushStudySessionOnPageHideMock = vi.fn()
const touchStudySessionActivityMock = vi.fn()
const updateStudySessionSnapshotMock = vi.fn()
const playWordAudioMock = vi.fn(() => Promise.resolve(true))
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

describe('QuickMemoryMode session duration summary', () => {
  const vocabulary: Word[] = [
    { word: 'apple', phonetic: '/ˈæpəl/', pos: 'n.', definition: 'fruit' },
  ]
  const settings: AppSettings = {}

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-07T00:00:00.000Z'))
    apiFetchMock.mockClear()
    showToastMock.mockClear()
    logSessionMock.mockClear()
    startSessionMock.mockClear()
    cancelSessionMock.mockClear()
    flushStudySessionOnPageHideMock.mockClear()
    touchStudySessionActivityMock.mockClear()
    updateStudySessionSnapshotMock.mockClear()
    playWordAudioMock.mockClear()
    prepareWordAudioPlaybackMock.mockClear()
    preloadWordAudioMock.mockClear()
    stopAudioMock.mockClear()
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 1 }))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows session duration after a chapter quick-memory round completes', async () => {
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

    fireEvent.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    vi.setSystemTime(new Date('2026-04-07T00:01:05.000Z'))
    fireEvent.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('本次用时')).toBeInTheDocument()
    expect(screen.getByText('1分5秒')).toBeInTheDocument()
    expect(logSessionMock).toHaveBeenCalledWith(expect.objectContaining({
      bookId: 'book-1',
      chapterId: '1',
      durationSeconds: 65,
    }))
  })

  it('shows session duration in chapter-scoped review summary', async () => {
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

    fireEvent.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    vi.setSystemTime(new Date('2026-04-07T00:00:45.000Z'))
    fireEvent.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('本轮完成')).toBeInTheDocument()
    expect(screen.getByText('本次用时')).toBeInTheDocument()
    expect(screen.getByText('45秒')).toBeInTheDocument()
  })

  it('shows session duration for non-chapter error review summary', async () => {
    const { container } = render(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId={null}
        chapterId={null}
        bookChapters={[]}
        errorMode
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    fireEvent.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    vi.setSystemTime(new Date('2026-04-07T00:00:45.000Z'))
    fireEvent.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('本轮完成')).toBeInTheDocument()
    expect(screen.getByText('本次用时')).toBeInTheDocument()
    expect(screen.getByText('45秒')).toBeInTheDocument()
  })
})
