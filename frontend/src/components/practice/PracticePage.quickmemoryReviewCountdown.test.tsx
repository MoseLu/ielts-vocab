import React from 'react'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const showToastMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const logSessionMock = vi.fn()
const cancelSessionMock = vi.fn()
const playWordAudioMock = vi.fn((...args: unknown[]) => {
  const onEnd = typeof args[2] === 'function' ? (args[2] as (() => void)) : undefined
  onEnd?.()
  return Promise.resolve(true)
})
const prepareWordAudioPlaybackMock = vi.fn().mockResolvedValue(true)
const preloadWordAudioMock = vi.fn().mockResolvedValue(true)
const stopAudioMock = vi.fn()
const useFavoriteWordsMock = vi.fn(() => ({
  isFavorite: () => false,
  isPending: () => false,
  toggleFavorite: vi.fn(),
}))
const useFamiliarWordsMock = vi.fn(() => ({
  isFamiliar: () => false,
  isPending: () => false,
  toggleFamiliar: vi.fn(),
}))

vi.mock('../../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: () => ({
    isConnected: false,
    isRecording: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}))

vi.mock('../../contexts/AIChatContext', () => ({
  setGlobalLearningContext: vi.fn(),
}))

vi.mock('../../lib/smartMode', () => ({
  loadSmartStats: vi.fn(() => ({})),
  recordWordResult: vi.fn(),
  chooseSmartDimension: vi.fn(() => 'meaning'),
  buildSmartQueue: vi.fn(() => []),
  syncSmartStatsToBackend: vi.fn(),
  loadSmartStatsFromBackend: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  recordModeAnswer: vi.fn(),
  resolveStudySessionDurationSeconds: (data: { startedAt: number; endedAt?: number; durationSeconds?: number }) =>
    data.durationSeconds ?? Math.max(0, Math.round(((data.endedAt ?? Date.now()) - data.startedAt) / 1000)),
  logSession: (...args: unknown[]) => logSessionMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: (...args: unknown[]) => cancelSessionMock(...args),
  flushStudySessionOnPageHide: vi.fn(),
  touchStudySessionActivity: vi.fn(),
  updateStudySessionSnapshot: vi.fn(),
}))

vi.mock('../../features/vocabulary/hooks', async () => {
  const actual = await vi.importActual<typeof import('../../features/vocabulary/hooks')>('../../features/vocabulary/hooks')
  return {
    ...actual,
    useFavoriteWords: (...args: unknown[]) => useFavoriteWordsMock(...args),
    useFamiliarWords: (...args: unknown[]) => useFamiliarWordsMock(...args),
  }
})

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    buildApiUrl: (path: string) => path,
  }
})

vi.mock('./utils', async () => {
  const actual = await vi.importActual<typeof import('./utils')>('./utils')
  return {
    ...actual,
    playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
    prepareWordAudioPlayback: (...args: unknown[]) => prepareWordAudioPlaybackMock(...args),
    preloadWordAudio: (...args: unknown[]) => preloadWordAudioMock(...args),
    preloadWordAudioBatch: (...args: unknown[]) => preloadWordAudioMock(...args),
    stopAudio: (...args: unknown[]) => stopAudioMock(...args),
  }
})

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('./PracticeControlBar', () => ({
  default: () => <div data-testid="practice-control-bar" />,
}))

vi.mock('./WordListPanel', () => ({
  default: () => null,
}))

vi.mock('./RadioMode', () => ({
  default: () => null,
}))

vi.mock('./DictationMode', () => ({
  default: () => null,
}))

vi.mock('./OptionsMode', () => ({
  default: () => null,
}))

vi.mock('../settings/SettingsPanel', () => ({
  default: () => null,
}))

describe('PracticePage quick-memory review countdown', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiFetchMock.mockReset()
    showToastMock.mockReset()
    startSessionMock.mockClear()
    logSessionMock.mockClear()
    cancelSessionMock.mockClear()
    playWordAudioMock.mockClear()
    playWordAudioMock.mockImplementation((...args: unknown[]) => {
      const onEnd = typeof args[2] === 'function' ? (args[2] as (() => void)) : undefined
      onEnd?.()
      return Promise.resolve(true)
    })
    prepareWordAudioPlaybackMock.mockClear()
    prepareWordAudioPlaybackMock.mockResolvedValue(true)
    preloadWordAudioMock.mockClear()
    preloadWordAudioMock.mockResolvedValue(true)
    stopAudioMock.mockClear()
    localStorage.clear()

    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      reviewLimitCustomized: true,
      shuffle: true,
      playbackSpeed: '1',
      volume: '100',
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') {
        return Promise.resolve({})
      }

      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
          ],
          summary: {
            due_count: 1,
            upcoming_count: 0,
            returned_count: 1,
            review_window_days: 3,
            offset: 0,
            limit: 10,
            total_count: 1,
            has_more: false,
            next_offset: null,
          },
        })
      }

      if (url === '/api/ai/quick-memory') {
        return Promise.resolve({ records: [] })
      }

      if (url === '/api/ai/quick-memory/sync') {
        return Promise.resolve({})
      }

      if (url === '/api/ai/wrong-words/sync') {
        return Promise.resolve({})
      }

      throw new Error(`Unexpected url: ${url}`)
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not auto reveal the first due-review word before any learning action', async () => {
    const { rerender } = render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage
          user={{ id: 42 }}
          currentDay={1}
          mode="listening"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    rerender(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage
          user={{ id: 42 }}
          currentDay={1}
          mode="quickmemory"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('alpha')).toBeInTheDocument()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
      await Promise.resolve()
    })
    expect(screen.getByText('3')).toBeInTheDocument()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
      await Promise.resolve()
    })
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.queryByText('✗ 不认识')).not.toBeInTheDocument()
    expect(playWordAudioMock).not.toHaveBeenCalled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(350)
      await Promise.resolve()
    })

    expect(playWordAudioMock).not.toHaveBeenCalled()
    expect(startSessionMock).not.toHaveBeenCalled()
  })

  it('skips lookahead audio preloading on the first due-review word', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
            { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
          ],
          summary: {
            due_count: 2,
            upcoming_count: 0,
            returned_count: 2,
            review_window_days: 3,
            offset: 0,
            limit: 10,
            total_count: 2,
            has_more: false,
            next_offset: null,
          },
        })
      }

      if (url === '/api/ai/quick-memory') {
        return Promise.resolve({ records: [] })
      }

      if (url === '/api/ai/quick-memory/sync') {
        return Promise.resolve({})
      }

      if (url === '/api/ai/wrong-words/sync') {
        return Promise.resolve({})
      }

      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage
          user={{ id: 42 }}
          currentDay={1}
          mode="quickmemory"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('alpha')).toBeInTheDocument()
    expect(preloadWordAudioMock).not.toHaveBeenCalled()
  })
})
