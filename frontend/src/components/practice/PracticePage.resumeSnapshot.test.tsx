import React from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const sessionHookValue = {
  settings: { shuffle: false },
  radioQuickSettings: { playbackSpeed: '1', playbackCount: '1', loopMode: false, interval: '2' },
  handleRadioSettingChange: vi.fn(),
  sessionCorrectRef: { current: 0 },
  sessionWrongRef: { current: 0 },
  correctCountRef: { current: 0 },
  wrongCountRef: { current: 0 },
  completedSessionDurationSecondsRef: { current: null },
  wordsLearnedBaselineRef: { current: 0 },
  uniqueAnsweredRef: { current: new Set<string>() },
  beginSession: vi.fn(),
  prepareSessionForLearningAction: vi.fn(async () => {}),
  completeCurrentSession: vi.fn(async () => 0),
  computeChapterWordsLearned: vi.fn(() => 0),
  registerAnsweredWord: vi.fn(),
  markRadioSessionInteraction: vi.fn(async () => {}),
  handleRadioProgressChange: vi.fn(),
  syncCurrentSessionSnapshot: vi.fn(),
  isCurrentSessionActive: vi.fn(() => true),
}
const controlsHookValue = {
  saveProgress: vi.fn(),
  resetChapterProgress: vi.fn(async () => {}),
  startRecording: vi.fn(async () => {}),
  stopRecording: vi.fn(),
  playWord: vi.fn(),
  handleContinueReview: vi.fn(),
  buildChapterPath: vi.fn(() => '/practice?book=book-1&chapter=1'),
  handleContinueErrorReview: vi.fn(),
}

vi.stubGlobal('fetch', vi.fn())

vi.mock('../../lib/smartMode', () => ({
  loadSmartStats: vi.fn(() => ({})),
  loadSmartStatsFromBackend: vi.fn(),
  buildSmartQueue: vi.fn(() => []),
}))

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    buildApiUrl: (path: string) => path,
  }
})

vi.mock('../../composables/practice/page/usePracticePageSession', () => ({
  usePracticePageSession: () => sessionHookValue,
}))

vi.mock('../../composables/practice/page/usePracticePageEffects', () => ({
  usePracticePageEffects: () => ({
    speechConnected: false,
    speechRecording: false,
    startSpeechRecording: vi.fn(async () => {}),
    stopSpeechRecording: vi.fn(),
    choiceOptionsReady: true,
  }),
}))

vi.mock('../../composables/practice/page/usePracticePageControls', () => ({
  usePracticePageControls: () => controlsHookValue,
}))

vi.mock('../../composables/practice/page/usePracticePageActions', () => ({
  usePracticePageActions: () => ({
    saveWrongWord: vi.fn(),
    handleQuickMemoryRecordChange: vi.fn(),
    goBack: vi.fn(),
    handleOptionSelect: vi.fn(),
    handleSpellingSubmit: vi.fn(),
    handleMeaningRecallSubmit: vi.fn(),
    handleSkip: vi.fn(),
  }),
}))

vi.mock('../../composables/practice/page/usePracticePageKeyboardShortcuts', () => ({
  usePracticePageKeyboardShortcuts: () => {},
}))

vi.mock('../../composables/practice/page/usePracticePageWordActions', () => ({
  usePracticePageWordActions: () => ({
    favoriteActive: false,
    favoriteBusy: false,
    handleFavoriteToggle: vi.fn(),
    wordListActionControls: undefined,
  }),
}))

vi.mock('./page/PracticePageContent', () => ({
  PracticePageContent: ({
    currentWord,
    queueIndex,
  }: {
    currentWord: { word: string }
    queueIndex: number
  }) => (
    <div>
      <div data-testid="current-word">{currentWord.word}</div>
      <div data-testid="queue-index">{queueIndex}</div>
    </div>
  ),
}))

describe('PracticePage remote resume snapshot', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    controlsHookValue.saveProgress.mockReset()
    controlsHookValue.resetChapterProgress.mockReset()
    sessionHookValue.beginSession.mockReset()
    sessionHookValue.settings = { shuffle: false }
    vi.mocked(fetch).mockReset()
    localStorage.clear()
  })

  it('restores chapter queue position from the server snapshot when local cache is empty', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/books/book-1/chapters') {
        return Promise.resolve({ ok: true, json: async () => ({ chapters: [{ id: 1, title: 'Chapter 1' }] }) } as Response)
      }
      if (url === '/api/books/book-1/chapters/1') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            words: [
              { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha' },
              { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta' },
              { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma' },
            ],
          }),
        } as Response)
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/progress') {
        return Promise.resolve({
          chapter_progress: {
            1: {
              current_index: 1,
              correct_count: 1,
              wrong_count: 0,
              is_completed: false,
              words_learned: 1,
              answered_words: ['alpha'],
              queue_words: ['alpha', 'beta', 'gamma'],
            },
          },
        })
      }
      return Promise.resolve({})
    })

    render(
      <MemoryRouter initialEntries={['/practice?book=book-1&chapter=1']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-word')).toHaveTextContent('beta')
      expect(screen.getByTestId('queue-index')).toHaveTextContent('1')
    })
    expect(screen.getByText('上次有未完成的释义练习，要从中断位置继续吗？')).toBeInTheDocument()
    expect(screen.getByText('重新开始')).toBeInTheDocument()
    expect(screen.getByText('继续练习')).toBeInTheDocument()
  })

  it('lets the user restart from the first word after an interrupted chapter session', async () => {
    const user = userEvent.setup()

    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/books/book-1/chapters') {
        return Promise.resolve({ ok: true, json: async () => ({ chapters: [{ id: 1, title: 'Chapter 1' }] }) } as Response)
      }
      if (url === '/api/books/book-1/chapters/1') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            words: [
              { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha' },
              { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta' },
              { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma' },
            ],
          }),
        } as Response)
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/progress') {
        return Promise.resolve({
          chapter_progress: {
            1: {
              current_index: 1,
              correct_count: 1,
              wrong_count: 0,
              is_completed: false,
              words_learned: 1,
              answered_words: ['alpha'],
              queue_words: ['alpha', 'beta', 'gamma'],
            },
          },
        })
      }
      return Promise.resolve({})
    })

    render(
      <MemoryRouter initialEntries={['/practice?book=book-1&chapter=1']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await screen.findByText('重新开始')
    await user.click(screen.getByText('重新开始'))

    await waitFor(() => {
      expect(screen.getByTestId('current-word')).toHaveTextContent('alpha')
      expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
    })
    expect(controlsHookValue.resetChapterProgress).toHaveBeenCalled()
  })

  it('ignores stale StrictMode practice loads so the first word does not jump after refresh', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false }))

    const staleWords = [
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha' },
    ]
    const freshWords = [
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta' },
    ]

    let practiceFetchCount = 0
    let resolveStaleFetch: (() => void) | null = null
    let resolveFreshFetch: (() => void) | null = null

    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/vocabulary/day/1') {
        practiceFetchCount += 1
        if (practiceFetchCount === 1) {
          return new Promise(resolve => {
            resolveStaleFetch = () => resolve({
              ok: true,
              json: async () => ({ vocabulary: staleWords }),
            } as Response)
          })
        }
        if (practiceFetchCount === 2) {
          return new Promise(resolve => {
            resolveFreshFetch = () => resolve({
              ok: true,
              json: async () => ({ vocabulary: freshWords }),
            } as Response)
          })
        }
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/progress') return Promise.resolve({})
      return Promise.resolve({})
    })

    render(
      <React.StrictMode>
        <MemoryRouter initialEntries={['/practice']}>
          <PracticePage user={{ id: 42 }} currentDay={1} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
        </MemoryRouter>
      </React.StrictMode>,
    )

    await waitFor(() => {
      expect(practiceFetchCount).toBe(2)
    })

    await act(async () => {
      resolveFreshFetch?.()
      await Promise.resolve()
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByTestId('current-word')).toHaveTextContent('beta')
      expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
    })

    await act(async () => {
      resolveStaleFetch?.()
      await Promise.resolve()
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByTestId('current-word')).toHaveTextContent('beta')
      expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
    })
  })

  it('reuses the first shuffled queue during StrictMode reloads for the same scope', async () => {
    sessionHookValue.settings = { shuffle: true }
    const randomSpy = vi.spyOn(Math, 'random')
    const randomValues = [0.9, 0.9, 0.0, 0.9]
    randomSpy.mockImplementation(() => randomValues.shift() ?? 0.5)

    const chapterWords = [
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha' },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta' },
      { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma' },
    ]

    let fetchCount = 0
    let resolveSecondFetch: (() => void) | null = null

    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/books/book-1/chapters') {
        return Promise.resolve({ ok: true, json: async () => ({ chapters: [{ id: 1, title: 'Chapter 1' }] }) } as Response)
      }
      if (url === '/api/books/book-1/chapters/1') {
        fetchCount += 1
        if (fetchCount === 1) {
          return Promise.resolve({ ok: true, json: async () => ({ words: chapterWords }) } as Response)
        }
        return new Promise(resolve => {
          resolveSecondFetch = () => resolve({ ok: true, json: async () => ({ words: chapterWords }) } as Response)
        })
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/progress') return Promise.resolve({ chapter_progress: {} })
      return Promise.resolve({})
    })

    render(
      <React.StrictMode>
        <MemoryRouter initialEntries={['/practice?book=book-1&chapter=1']}>
          <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
        </MemoryRouter>
      </React.StrictMode>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('current-word')).toHaveTextContent('alpha')
      expect(fetchCount).toBe(2)
    })

    await act(async () => {
      resolveSecondFetch?.()
      await Promise.resolve()
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByTestId('current-word')).toHaveTextContent('alpha')
      expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
    })
    expect(randomSpy).toHaveBeenCalledTimes(2)
    randomSpy.mockRestore()
  })
})
