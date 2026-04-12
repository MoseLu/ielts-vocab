import React from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const fetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const generateOptionsMock = vi.fn()
const useFavoriteWordsMock = vi.fn(() => ({
  isFavorite: () => false,
  isPending: () => false,
  toggleFavorite: vi.fn(),
}))

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
  buildSmartQueue: vi.fn((words: string[]) => words.map((_word, index) => index)),
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

vi.mock('../../features/vocabulary/hooks', async () => {
  const actual = await vi.importActual<typeof import('../../features/vocabulary/hooks')>('../../features/vocabulary/hooks')
  return {
    ...actual,
    useFavoriteWords: (...args: unknown[]) => useFavoriteWordsMock(...args),
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
    generateOptions: (...args: unknown[]) => generateOptionsMock(...args),
    playWordAudio: vi.fn(),
    prepareWordAudioPlayback: vi.fn(() => Promise.resolve(true)),
    preloadWordAudio: vi.fn(() => Promise.resolve(true)),
    preloadWordAudioBatch: vi.fn(() => Promise.resolve(true)),
    stopAudio: vi.fn(),
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

vi.mock('../settings/SettingsPanel', () => ({
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
  }: {
    currentWord: { word: string }
    options: Array<{ definition: string }>
    optionsLoading?: boolean
  }) => (
    <div data-testid="options-mode">
      <div data-testid="options-state">
        {optionsLoading
          ? `loading:${currentWord.word}`
          : `ready:${currentWord.word}:${options.map(option => option.definition).join('|')}`}
      </div>
    </div>
  ),
}))

describe('PracticePage listening mode switch', () => {
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
    generateOptionsMock.mockReset()
    localStorage.clear()
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))
    generateOptionsMock.mockImplementation((currentWord: { word: string; definition: string; pos: string }, allWords: Array<{ word: string; definition: string; pos: string }>) => ({
      options: allWords.slice(0, 4).map(word => ({
        word: word.word,
        definition: word.definition,
        pos: word.pos,
      })),
      correctIndex: 0,
    }))
  })

  it('does not regenerate the first listening question when the mode data reload finishes', async () => {
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

    let resolveSecondFetch: ((value: { json: () => Promise<{ vocabulary: typeof vocabulary }> }) => void) | null = null
    let fetchCount = 0

    fetchMock.mockImplementation(() => {
      fetchCount += 1
      if (fetchCount === 1) {
        return Promise.resolve({ json: async () => ({ vocabulary }) })
      }
      return new Promise(resolve => {
        resolveSecondFetch = resolve
      })
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/progress') return Promise.resolve({})
      throw new Error(`Unexpected url: ${url}`)
    })

    const { rerender } = render(
      <React.StrictMode>
        <MemoryRouter>
          <PracticePage currentDay={1} mode="meaning" onModeChange={() => {}} onDayChange={() => {}} />
        </MemoryRouter>
      </React.StrictMode>,
    )

    await flushRender()

    rerender(
      <React.StrictMode>
        <MemoryRouter>
          <PracticePage currentDay={1} mode="listening" onModeChange={() => {}} onDayChange={() => {}} />
        </MemoryRouter>
      </React.StrictMode>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-state')).toHaveTextContent('ready:guide:')
    })
    const firstRenderState = screen.getByTestId('options-state').textContent

    await act(async () => {
      resolveSecondFetch?.({ json: async () => ({ vocabulary }) })
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByTestId('options-state').textContent).toBe(firstRenderState)
    expect(generateOptionsMock).not.toHaveBeenCalled()
  })

  it('allows the reload pass to top up listening options when the first pass only has three choices', async () => {
    const limitedVocabulary = [
      {
        word: 'ban',
        phonetic: '/bæn/',
        pos: 'v.',
        definition: '禁止',
        listening_confusables: [
          { word: 'fee', phonetic: '/fiː/', pos: 'n.', definition: '费用' },
          { word: 'feelings', phonetic: '/ˈfiːlɪŋz/', pos: 'n.', definition: '情感；感觉；“feeling”的复数' },
        ],
      },
      { word: 'fee', phonetic: '/fiː/', pos: 'n.', definition: '费用' },
      { word: 'feelings', phonetic: '/ˈfiːlɪŋz/', pos: 'n.', definition: '情感；感觉；“feeling”的复数' },
    ]
    const expandedVocabulary = [
      {
        ...limitedVocabulary[0],
        listening_confusables: [
          ...limitedVocabulary[0].listening_confusables,
          { word: 'feed', phonetic: '/fiːd/', pos: 'v.', definition: '吃；喂；“feed”的现在分词；饲养；给食；' },
        ],
      },
      ...limitedVocabulary.slice(1),
      { word: 'feed', phonetic: '/fiːd/', pos: 'v.', definition: '吃；喂；“feed”的现在分词；饲养；给食；' },
    ]

    generateOptionsMock
      .mockReset()
      .mockImplementationOnce(() => ({
        options: limitedVocabulary.map(word => ({
          word: word.word,
          definition: word.definition,
          pos: word.pos,
        })),
        correctIndex: 0,
      }))
      .mockImplementation(() => ({
        options: expandedVocabulary.map(word => ({
          word: word.word,
          definition: word.definition,
          pos: word.pos,
        })),
        correctIndex: 0,
      }))

    let resolveSecondFetch: ((value: { json: () => Promise<{ vocabulary: typeof expandedVocabulary }> }) => void) | null = null
    let fetchCount = 0

    fetchMock.mockImplementation(() => {
      fetchCount += 1
      if (fetchCount === 1) {
        return Promise.resolve({ json: async () => ({ vocabulary: limitedVocabulary }) })
      }
      return new Promise(resolve => {
        resolveSecondFetch = resolve
      })
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/progress') return Promise.resolve({})
      throw new Error(`Unexpected url: ${url}`)
    })

    const { rerender } = render(
      <React.StrictMode>
        <MemoryRouter>
          <PracticePage currentDay={1} mode="meaning" onModeChange={() => {}} onDayChange={() => {}} />
        </MemoryRouter>
      </React.StrictMode>,
    )

    await flushRender()

    rerender(
      <React.StrictMode>
        <MemoryRouter>
          <PracticePage currentDay={1} mode="listening" onModeChange={() => {}} onDayChange={() => {}} />
        </MemoryRouter>
      </React.StrictMode>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-state')).toHaveTextContent('ready:ban:禁止|费用|情感；感觉；“feeling”的复数')
    })

    await act(async () => {
      resolveSecondFetch?.({ json: async () => ({ vocabulary: expandedVocabulary }) })
      await Promise.resolve()
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByTestId('options-state')).toHaveTextContent(
        'ready:ban:禁止|费用|情感；感觉；“feeling”的复数|吃；喂；“feed”的现在分词；饲养；给食；',
      )
    })
    expect(generateOptionsMock).toHaveBeenCalledTimes(2)
  })
})
