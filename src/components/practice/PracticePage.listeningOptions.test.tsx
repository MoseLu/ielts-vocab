import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const fetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const logSessionMock = vi.fn()
const playWordAudioMock = vi.fn()
const stopAudioMock = vi.fn()

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
  logSession: (...args: unknown[]) => logSessionMock(...args),
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
    stopAudio: (...args: unknown[]) => stopAudioMock(...args),
  }
})

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

vi.mock('./QuickMemoryMode', () => ({
  default: () => null,
}))

vi.mock('../SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../ui', () => ({
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

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
        {optionsLoading
          ? `loading:${currentWord.word}`
          : `ready:${currentWord.word}:${options.map(option => option.definition).join('|')}`}
      </div>
      <button type="button" onClick={() => onOptionSelect(correctIndex)}>
        answer-correct
      </button>
    </div>
  ),
}))

describe('PracticePage listening options loading', () => {
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
    logSessionMock.mockClear()
    playWordAudioMock.mockClear()
    stopAudioMock.mockClear()
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('uses preloaded listening confusables instead of fetching similar words per question', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))

    const vocabulary = [
      {
        word: 'unsupported',
        phonetic: '/ˌʌnsəˈpɔːtɪd/',
        pos: 'adj.',
        definition: '未预设干扰组',
      },
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
      {
        word: 'guy',
        phonetic: '/gai/',
        pos: 'n.',
        definition: '家伙',
        listening_confusables: [
          { word: 'guide', phonetic: '/gaid/', pos: 'n.', definition: '向导' },
          { word: 'guise', phonetic: '/gaiz/', pos: 'n.', definition: '伪装' },
          { word: 'guile', phonetic: '/gail/', pos: 'n.', definition: '狡诈' },
        ],
      },
      { word: 'guise', phonetic: '/gaiz/', pos: 'n.', definition: '伪装' },
      { word: 'guile', phonetic: '/gail/', pos: 'n.', definition: '狡诈' },
      { word: 'guild', phonetic: '/gild/', pos: 'n.', definition: '协会' },
    ]

    fetchMock.mockResolvedValue({
      json: async () => ({ vocabulary }),
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') {
        return Promise.resolve({})
      }

      if (url === '/api/progress') {
        return Promise.resolve({})
      }

      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="listening"
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await flushRender()
    expect(screen.getByTestId('options-state')).toHaveTextContent('ready:guide:')

    fireEvent.click(screen.getByRole('button', { name: 'answer-correct' }))

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 1300))
    })

    await waitFor(() => {
      expect(screen.getByTestId('options-state')).toHaveTextContent('ready:guy:')
    })

    expect(
      apiFetchMock.mock.calls.every(([url]) => !String(url).includes('/api/ai/similar-words')),
    ).toBe(true)
  })

  it('does not interrupt auto-play when learner profile resolves after playback starts', async () => {
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

    let resolveProfile: ((value: unknown) => void) | null = null
    const profilePromise = new Promise(resolve => {
      resolveProfile = resolve
    })

    fetchMock.mockResolvedValue({
      json: async () => ({ vocabulary }),
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') {
        return profilePromise
      }

      if (url === '/api/progress') {
        return Promise.resolve({})
      }

      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="listening"
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await flushRender()
    expect(screen.getByTestId('options-state')).toHaveTextContent('ready:guide:')

    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide'])
    const stopCallsAfterFirstPlayback = stopAudioMock.mock.calls.length

    await act(async () => {
      resolveProfile?.({})
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide'])
    expect(stopAudioMock.mock.calls.length).toBe(stopCallsAfterFirstPlayback)
  })
})
