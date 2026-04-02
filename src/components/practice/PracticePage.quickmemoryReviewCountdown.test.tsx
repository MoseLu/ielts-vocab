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
const playWordAudioMock = vi.fn()
const stopAudioMock = vi.fn()

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
  logSession: (...args: unknown[]) => logSessionMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: (...args: unknown[]) => cancelSessionMock(...args),
  flushStudySessionOnPageHide: vi.fn(),
  touchStudySessionActivity: vi.fn(),
  updateStudySessionSnapshot: vi.fn(),
}))

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

vi.mock('../SettingsPanel', () => ({
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
    stopAudioMock.mockClear()
    localStorage.clear()

    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      shuffle: true,
      playbackSpeed: '1',
      volume: '100',
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') {
        return Promise.resolve({})
      }

      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0') {
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

      throw new Error(`Unexpected url: ${url}`)
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('keeps the first review word countdown running after switching into quickmemory review mode', async () => {
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
    expect(screen.getByText('4')).toBeInTheDocument()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
      await Promise.resolve()
    })

    expect(screen.getByText('3')).toBeInTheDocument()
  })
})
