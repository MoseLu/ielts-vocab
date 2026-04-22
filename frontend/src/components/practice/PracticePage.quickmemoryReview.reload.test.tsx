import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const fetchMock = vi.fn()

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
  buildSmartQueue: vi.fn(() => []),
  syncSmartStatsToBackend: vi.fn(),
  loadSmartStatsFromBackend: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  recordModeAnswer: vi.fn(),
  resolveStudySessionDurationSeconds: () => 0,
  logSession: vi.fn(),
  startSession: vi.fn(),
  cancelSession: vi.fn(),
  flushStudySessionOnPageHide: vi.fn(),
  touchStudySessionActivity: vi.fn(),
  updateStudySessionSnapshot: vi.fn(),
}))

vi.mock('../../features/vocabulary/hooks', async () => {
  const actual = await vi.importActual<typeof import('../../features/vocabulary/hooks')>('../../features/vocabulary/hooks')
  return {
    ...actual,
    useFavoriteWords: () => ({
      isFavorite: () => false,
      isPending: () => false,
      toggleFavorite: vi.fn(),
    }),
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

vi.mock('./PracticeControlBar', () => ({ default: () => <div data-testid="practice-control-bar" /> }))
vi.mock('./WordListPanel', () => ({ default: () => null }))
vi.mock('./RadioMode', () => ({ default: () => null }))
vi.mock('./DictationMode', () => ({ default: () => null }))
vi.mock('./OptionsMode', () => ({ default: () => null }))
vi.mock('../settings/SettingsPanel', () => ({ default: () => null }))
vi.mock('../ui/Loading', () => ({
  Loading: ({ text }: { text: string }) => <div>{text}</div>,
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))
vi.mock('./QuickMemoryMode', () => ({
  default: ({ vocabulary }: { vocabulary: Array<{ word: string }> }) => (
    <div data-testid="quickmemory-mode">{vocabulary.map(word => word.word).join(',')}</div>
  ),
}))

describe('PracticePage quick-memory review queue reloads', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    fetchMock.mockReset()
    localStorage.clear()
  })

  it('does not reload the due queue when the parent rerenders with a fresh user object', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '1',
      reviewLimit: 'unlimited',
      reviewLimitCustomized: true,
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=100&within_days=1&offset=0&scope=due') {
        return Promise.resolve({
          words: [{ word: 'anchor', phonetic: '/a/', pos: 'n.', definition: 'anchor def' }],
          summary: {
            due_count: 1,
            upcoming_count: 0,
            returned_count: 1,
            review_window_days: 1,
            offset: 0,
            limit: 100,
            total_count: 1,
            has_more: false,
            next_offset: null,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const view = render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42, username: 'luo' }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('anchor')
    })

    view.rerender(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42, username: 'luo' }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('anchor')
    })

    expect(
      apiFetchMock.mock.calls.filter(([url]) => url === '/api/ai/quick-memory/review-queue?limit=100&within_days=1&offset=0&scope=due'),
    ).toHaveLength(1)
  })
})
