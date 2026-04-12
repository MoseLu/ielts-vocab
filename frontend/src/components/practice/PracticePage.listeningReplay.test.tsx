import React from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const fetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const playWordAudioMock = vi.fn()
const prepareWordAudioPlaybackMock = vi.fn(() => Promise.resolve(true))
const preloadWordAudioMock = vi.fn(() => Promise.resolve(true))

vi.stubGlobal('fetch', fetchMock)

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
  buildSmartQueue: vi.fn((words: string[]) => words.map((_, index) => index)),
  syncSmartStatsToBackend: vi.fn(),
  loadSmartStatsFromBackend: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  recordModeAnswer: vi.fn(),
  resolveStudySessionDurationSeconds: (data: { startedAt: number; endedAt?: number; durationSeconds?: number }) =>
    data.durationSeconds ?? Math.max(0, Math.round(((data.endedAt ?? Date.now()) - data.startedAt) / 1000)),
  logSession: vi.fn(),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: vi.fn(),
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
    prepareWordAudioPlayback: (...args: unknown[]) => prepareWordAudioPlaybackMock(...args),
    preloadWordAudio: (...args: unknown[]) => preloadWordAudioMock(...args),
    preloadWordAudioBatch: (...args: unknown[]) => preloadWordAudioMock(...args),
    stopAudio: vi.fn(),
  }
})

vi.mock('./PracticeControlBar', () => ({ default: () => <div data-testid="practice-control-bar" /> }))
vi.mock('./WordListPanel', () => ({ default: () => null }))
vi.mock('./RadioMode', () => ({ default: () => null }))
vi.mock('./DictationMode', () => ({ default: () => null }))
vi.mock('./QuickMemoryMode', () => ({ default: () => null }))
vi.mock('../settings/SettingsPanel', () => ({ default: () => null }))
vi.mock('../ui', () => ({ PageSkeleton: () => <div data-testid="page-skeleton" /> }))

vi.mock('./OptionsMode', () => ({
  default: ({
    currentWord,
    options,
    optionsLoading = false,
    correctIndex,
    onOptionSelect,
  }: {
    currentWord: { word: string }
    options: Array<{ definition: string }>
    optionsLoading?: boolean
    correctIndex: number
    onOptionSelect: (idx: number) => void
  }) => (
    <div data-testid="options-mode">
      <div data-testid="options-state">
        {optionsLoading ? `loading:${currentWord.word}` : `ready:${currentWord.word}:${options.length}`}
      </div>
      <button type="button" data-testid="answer-wrong-1" onClick={() => onOptionSelect(correctIndex === 0 ? 1 : 0)}>
        answer-wrong-1
      </button>
      <button type="button" data-testid="answer-wrong-2" onClick={() => onOptionSelect(correctIndex <= 1 ? 2 : 1)}>
        answer-wrong-2
      </button>
    </div>
  ),
}))

describe('PracticePage listening replay', () => {
  async function flushRender() {
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
      await Promise.resolve()
    })
  }

  beforeEach(() => {
    apiFetchMock.mockReset()
    fetchMock.mockReset()
    startSessionMock.mockClear()
    playWordAudioMock.mockClear()
    prepareWordAudioPlaybackMock.mockClear()
    preloadWordAudioMock.mockClear()
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('replays word audio after each distinct wrong listening choice', async () => {
    vi.useFakeTimers()
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))

    const vocabulary = [
      {
        word: 'guide',
        phonetic: '/gaid/',
        pos: 'n.',
        definition: '向导',
        listening_confusables: [
          { word: 'guy', phonetic: '/gai/', pos: 'n.', definition: '家伙' },
          { word: 'guise', phonetic: '/gaiz/', pos: 'n.', definition: '伪装' },
          { word: 'guile', phonetic: '/gail/', pos: 'n.', definition: '狡诈' },
        ],
      },
      { word: 'guy', phonetic: '/gai/', pos: 'n.', definition: '家伙' },
      { word: 'guise', phonetic: '/gaiz/', pos: 'n.', definition: '伪装' },
      { word: 'guile', phonetic: '/gail/', pos: 'n.', definition: '狡诈' },
    ]

    fetchMock.mockResolvedValue({ json: async () => ({ vocabulary }) })
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/progress') return Promise.resolve({})
      if (url === '/api/ai/wrong-words/sync') return Promise.resolve({})
      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter>
        <PracticePage currentDay={1} mode="listening" onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await flushRender()
    expect(screen.getByTestId('options-state')).toHaveTextContent('ready:guide:4')

    act(() => {
      vi.advanceTimersByTime(300)
    })
    await flushRender()
    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide'])

    fireEvent.click(screen.getByTestId('answer-wrong-1'))
    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide', 'guide'])

    fireEvent.click(screen.getByTestId('answer-wrong-2'))
    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide', 'guide', 'guide'])
  })
})
