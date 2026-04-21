import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PracticePage from './PracticePage'
import { chooseSmartDimension } from '../../lib/smartMode'

const apiFetchMock = vi.fn()
const fetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const logSessionMock = vi.fn()
const playWordAudioMock = vi.fn()
const prepareWordAudioPlaybackMock = vi.fn(() => Promise.resolve(true))
const preloadWordAudioMock = vi.fn(() => Promise.resolve(true))
const stopAudioMock = vi.fn()
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
  buildSmartQueue: vi.fn((words: string[]) => words.map((_, index) => index)),
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
    playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
    prepareWordAudioPlayback: (...args: unknown[]) => prepareWordAudioPlaybackMock(...args),
    preloadWordAudio: (...args: unknown[]) => preloadWordAudioMock(...args),
    preloadWordAudioBatch: (...args: unknown[]) => preloadWordAudioMock(...args),
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

vi.mock('../settings/SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../ui', async () => {
  const actual = await vi.importActual<typeof import('../ui')>('../ui')
  return {
    ...actual,
    PageSkeleton: () => <div data-testid="page-skeleton" />,
  }
})

vi.mock('./OptionsMode', () => ({
  default: ({
    currentWord,
    mode,
    smartDimension,
    options,
    optionsLoading = false,
    correctIndex,
    onOptionSelect,
  }: {
    currentWord: { word: string }
    mode?: string
    smartDimension?: string
    options: Array<{ definition: string }>
    optionsLoading?: boolean
    correctIndex: number
    onOptionSelect: (idx: number) => void
  }) => (
    <div
      data-testid="options-mode"
      data-mode={mode ?? ''}
      data-smart-dimension={smartDimension ?? ''}
    >
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
    prepareWordAudioPlaybackMock.mockClear()
    preloadWordAudioMock.mockClear()
    stopAudioMock.mockClear()
    vi.mocked(chooseSmartDimension).mockReturnValue('meaning')
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

  it('falls back to meaning mode for custom-book chapters without listening presets', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))

    const onModeChange = vi.fn()
    const showToast = vi.fn()
    const chapterWords = [
      { word: 'ability', phonetic: '/əˈbɪləti/', pos: 'n.', definition: '能力' },
      { word: 'agility', phonetic: '/əˈdʒɪləti/', pos: 'n.', definition: '敏捷' },
      { word: 'facility', phonetic: '/fəˈsɪləti/', pos: 'n.', definition: '设施' },
      { word: 'liability', phonetic: '/ˌlaɪəˈbɪləti/', pos: 'n.', definition: '责任' },
    ]

    fetchMock.mockImplementation((url: string) => Promise.resolve({
      json: async () => (
        url === '/api/books/custom_1/chapters'
          ? {
              chapters: [
                { id: 'custom_1_1', title: '第1章' },
                { id: 'custom_1_2', title: '第2章' },
              ],
            }
          : { words: chapterWords }
      ),
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/books/custom_1/chapters/progress') return Promise.resolve({ chapter_progress: {} })
      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter initialEntries={['/practice?book=custom_1&chapter=custom_1_2']}>
        <PracticePage
          currentDay={1}
          mode="listening"
          showToast={showToast}
          onModeChange={onModeChange}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveAttribute('data-mode', 'meaning')
      expect(screen.getByTestId('options-state')).toHaveTextContent('loading:ability')
    })

    expect(onModeChange).toHaveBeenCalledWith('meaning')
    expect(showToast).toHaveBeenCalledWith('自定义词书当前章节没有听音题素材，已自动切换到词义模式。', 'info')
    expect(screen.queryByText('当前词表暂无可用听音辨析')).toBeNull()
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
    await flushRender()

    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide'])
    expect(playWordAudioMock).toHaveBeenCalledWith('guide', expect.anything(), undefined, { sourcePreference: 'buffer' })
    const stopCallsAfterFirstPlayback = stopAudioMock.mock.calls.length

    await act(async () => {
      resolveProfile?.({})
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['guide'])
    expect(stopAudioMock.mock.calls.length).toBe(stopCallsAfterFirstPlayback)
  })

  it('commits smart mode with the resolved dimension immediately', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))
    vi.mocked(chooseSmartDimension).mockReturnValue('listening')

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

    fetchMock.mockResolvedValue({
      json: async () => ({ vocabulary }),
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/progress') return Promise.resolve({})
      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="smart"
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveAttribute('data-mode', 'smart')
      expect(screen.getByTestId('options-mode')).toHaveAttribute('data-smart-dimension', 'listening')
    })
  })

  it('shows chapter completion summary with session duration after finishing a chapter', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-07T00:00:00.000Z'))
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))

    const vocabulary = [{
      word: 'guide',
      phonetic: '/gaid/',
      pos: 'n.',
      definition: '向导',
      listening_confusables: [
        { word: 'guy', phonetic: '/gai/', pos: 'n.', definition: '家伙' },
        { word: 'guise', phonetic: '/gaiz/', pos: 'n.', definition: '伪装' },
        { word: 'guile', phonetic: '/gail/', pos: 'n.', definition: '狡诈' },
      ],
    }]

    fetchMock.mockImplementation((url: string) => Promise.resolve({
      json: async () => (url === '/api/books/book-1/chapters'
        ? { chapters: [{ id: '1', title: 'Chapter 1' }] }
        : { words: vocabulary }),
    }))
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/progress') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/1/progress') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/1/mode-progress') return Promise.resolve({})
      throw new Error(`Unexpected url: ${url}`)
    })

    render(
      <MemoryRouter initialEntries={['/practice?book=book-1&chapter=1']}>
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
    vi.setSystemTime(new Date('2026-04-07T00:01:04.000Z'))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1300)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByText('本轮完成')).toBeInTheDocument()
    expect(screen.getByText('本章练习')).toBeInTheDocument()
    expect(screen.getByText('1分5秒')).toBeInTheDocument()
    expect(logSessionMock).toHaveBeenCalledWith(expect.objectContaining({
      chapterId: '1',
      durationSeconds: 65,
    }))
  })
})
