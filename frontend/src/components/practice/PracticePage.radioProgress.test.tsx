import React, { useEffect } from 'react'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const saveProgressMock = vi.fn()
const beginSessionMock = vi.fn()
const prepareSessionForLearningActionMock = vi.fn(async () => {})
const completeCurrentSessionMock = vi.fn(async () => 0)
const handleRadioProgressChangeMock = vi.fn()
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
  beginSession: beginSessionMock,
  prepareSessionForLearningAction: prepareSessionForLearningActionMock,
  completeCurrentSession: completeCurrentSessionMock,
  computeChapterWordsLearned: vi.fn(() => 0),
  registerAnsweredWord: vi.fn(),
  markRadioSessionInteraction: vi.fn(async () => {}),
  handleRadioProgressChange: handleRadioProgressChangeMock,
  syncCurrentSessionSnapshot: vi.fn(),
  isCurrentSessionActive: vi.fn(() => true),
}
const controlsHookValue = {
  saveProgress: saveProgressMock,
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
  PracticePageContent: ({ onFavoriteWordIndexChange }: { onFavoriteWordIndexChange: (index: number) => void }) => {
    useEffect(() => {
      onFavoriteWordIndexChange(1)
    }, [])
    return <div>radio</div>
  },
}))

describe('PracticePage radio progress sync', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    saveProgressMock.mockReset()
    beginSessionMock.mockReset()
    prepareSessionForLearningActionMock.mockClear()
    completeCurrentSessionMock.mockClear()
    handleRadioProgressChangeMock.mockClear()
    vi.mocked(fetch).mockReset()
    localStorage.clear()
  })

  it('persists radio queue position through the shared saveProgress path', async () => {
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
            ],
          }),
        } as Response)
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/learner-profile') return Promise.resolve({})
      if (url === '/api/books/book-1/chapters/progress') return Promise.resolve({ chapter_progress: {} })
      return Promise.resolve({})
    })

    render(
      <MemoryRouter initialEntries={['/practice?book=book-1&chapter=1']}>
        <PracticePage user={{ id: 42 }} mode="radio" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(saveProgressMock).toHaveBeenLastCalledWith(0, 0, { advanceToNext: false })
    })
  })
})
