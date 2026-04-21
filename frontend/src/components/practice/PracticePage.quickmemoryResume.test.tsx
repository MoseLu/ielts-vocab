import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'

const {
  apiFetchMock,
  quickMemoryModeMock,
  resetChapterProgressMock,
  sessionHookValue,
} = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  quickMemoryModeMock: vi.fn(),
  resetChapterProgressMock: vi.fn(async () => {}),
  sessionHookValue: {
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
    markFollowSessionInteraction: vi.fn(async () => {}),
    markRadioSessionInteraction: vi.fn(async () => {}),
    handleRadioProgressChange: vi.fn(),
    syncCurrentSessionSnapshot: vi.fn(),
    isCurrentSessionActive: vi.fn(() => true),
  },
}))
const fetchMock = vi.fn()

vi.stubGlobal('fetch', fetchMock)

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
  usePracticePageControls: () => ({
    saveProgress: vi.fn(),
    resetChapterProgress: resetChapterProgressMock,
    startRecording: vi.fn(async () => {}),
    stopRecording: vi.fn(),
    playWord: vi.fn(),
    handleContinueReview: vi.fn(),
    buildChapterPath: vi.fn(() => '/practice?book=book-1&chapter=1'),
    handleContinueErrorReview: vi.fn(),
  }),
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

vi.mock('./PracticeControlBar', () => ({ default: () => <div data-testid="practice-control-bar" /> }))
vi.mock('./WordListPanel', () => ({ default: () => null }))
vi.mock('../settings/SettingsPanel', () => ({ default: () => null }))
vi.mock('./FavoriteToggleButton', () => ({ default: () => <div data-testid="favorite-toggle" /> }))
vi.mock('./QuickMemoryMode', () => ({ default: quickMemoryModeMock }))

describe('PracticePage quick-memory resume snapshot', () => {
  beforeEach(() => {
    quickMemoryModeMock.mockImplementation(({ initialIndex }: { initialIndex?: number }) => (
      <div data-testid="quickmemory-mode">initialIndex:{String(initialIndex ?? 0)}</div>
    ))
    apiFetchMock.mockReset()
    fetchMock.mockReset()
    quickMemoryModeMock.mockClear()
    resetChapterProgressMock.mockClear()
    localStorage.clear()
  })

  it('passes the restored chapter index into QuickMemoryMode and resets it on restart', async () => {
    const user = userEvent.setup()

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
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
              queue_words: ['alpha', 'beta'],
            },
          },
        })
      }
      return Promise.resolve({})
    })

    render(
      <MemoryRouter initialEntries={['/practice?book=book-1&chapter=1']}>
        <PracticePage user={{ id: 42 }} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('initialIndex:1')
    })
    expect(screen.getByText('上次有未完成的快记练习，要从中断位置继续吗？')).toBeInTheDocument()

    await user.click(screen.getByText('重新开始'))

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('initialIndex:0')
    })
    expect(resetChapterProgressMock).toHaveBeenCalled()
  })
})
