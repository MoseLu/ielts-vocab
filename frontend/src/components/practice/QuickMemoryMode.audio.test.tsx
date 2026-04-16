import React from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import type { AppSettings, Word } from './types'
import { STORAGE_KEYS } from '../../constants'
import { PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT } from './page/practiceGlobalShortcutEvents'

const apiFetchMock = vi.fn(() => Promise.resolve({}))
const showToastMock = vi.fn()
const logSessionMock = vi.fn()
const startSessionMock = vi.fn(() => Promise.resolve(1))
const cancelSessionMock = vi.fn(() => Promise.resolve())
const flushStudySessionOnPageHideMock = vi.fn()
const touchStudySessionActivityMock = vi.fn()
const updateStudySessionSnapshotMock = vi.fn()
const playWordAudioMock = vi.fn(() => Promise.resolve(true))
const preloadWordAudioMock = vi.fn(() => Promise.resolve(true))
const stopAudioMock = vi.fn()

vi.mock('./utils', () => ({
  playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
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

const settings: AppSettings = {}
const vocabulary: Word[] = [
  { word: 'apple', phonetic: '/ˈæpəl/', pos: 'n.', definition: 'fruit' },
]

function renderQuickMemoryMode(customWord?: Word) {
  return render(
    <QuickMemoryMode
      vocabulary={customWord ? [customWord] : vocabulary}
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
}

describe('QuickMemoryMode audio behavior', () => {
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
    preloadWordAudioMock.mockClear()
    preloadWordAudioMock.mockImplementation(() => Promise.resolve(true))
    stopAudioMock.mockClear()
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 1 }))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not auto reveal after the countdown expires without an active learning segment', async () => {
    vi.useFakeTimers()

    renderQuickMemoryMode({ word: 'within', phonetic: '/wɪˈðɪn/', pos: 'prep.', definition: 'inside' })

    expect(playWordAudioMock).not.toHaveBeenCalled()
    expect(screen.getByText('4')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('3')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(3000)
    })
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.queryByText('✗ 不认识')).not.toBeInTheDocument()
    expect(playWordAudioMock).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(350)
    })
    expect(playWordAudioMock).not.toHaveBeenCalled()
  })

  it('starts the countdown immediately and only plays audio after the user answers', async () => {
    vi.useFakeTimers()

    renderQuickMemoryMode({ word: 'within', phonetic: '/wɪˈðɪn/', pos: 'prep.', definition: 'inside' })

    expect(playWordAudioMock).not.toHaveBeenCalled()
    expect(screen.getByText('4')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('3')).toBeInTheDocument()

    await act(async () => {
      screen.getByRole('button', { name: '认识' }).click()
    })
    expect(playWordAudioMock).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(350)
    })
    expect(playWordAudioMock).toHaveBeenCalledWith('within', settings, expect.any(Function))
  })

  it('replays the current word audio from the shared shortcut, the toolbar button, and the word itself', async () => {
    const user = userEvent.setup()
    renderQuickMemoryMode()

    stopAudioMock.mockClear()
    await act(async () => {
      window.dispatchEvent(new Event(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT))
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(playWordAudioMock).toHaveBeenCalledWith('apple', settings, expect.any(Function))
    })

    playWordAudioMock.mockClear()
    await user.click(screen.getByRole('button', { name: '重播发音' }))
    await waitFor(() => {
      expect(playWordAudioMock).toHaveBeenCalledWith('apple', settings, expect.any(Function))
    })

    playWordAudioMock.mockClear()
    await user.click(screen.getByRole('button', { name: 'apple' }))
    await waitFor(() => {
      expect(playWordAudioMock).toHaveBeenCalledWith('apple', settings, expect.any(Function))
    })

    expect(stopAudioMock).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '重播发音' })).toBeInTheDocument()
  })
})
