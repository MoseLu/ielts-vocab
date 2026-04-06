import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'
import { QUICK_MEMORY_MASTERY_TARGET } from '../../lib/quickMemory'
import { STORAGE_KEYS } from '../../constants'

const apiFetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const practiceControlBarMock = vi.fn(() => <div data-testid="practice-control-bar" />)
const fetchMock = vi.fn()
const toggleFavoriteMock = vi.fn()
const useFavoriteWordsMock = vi.fn(() => ({
  isFavorite: (word: string) => word === 'beta',
  isPending: () => false,
  toggleFavorite: (...args: unknown[]) => toggleFavoriteMock(...args),
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
  buildSmartQueue: vi.fn(() => []),
  syncSmartStatsToBackend: vi.fn(),
  loadSmartStatsFromBackend: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  recordModeAnswer: vi.fn(),
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

vi.mock('./PracticeControlBar', () => ({
  default: (props: unknown) => practiceControlBarMock(props),
}))

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
  default: ({
    vocabulary,
      reviewHasMore,
      onContinueReview,
      onQuickMemoryRecordChange,
      onIndexChange,
      favoriteSlot,
    }: {
      vocabulary: Array<{ word: string }>
      reviewHasMore?: boolean
      onContinueReview?: () => void
      onIndexChange?: (index: number) => void
      onQuickMemoryRecordChange?: (word: { word: string }, record: {
        status: 'known' | 'unknown'
        firstSeen: number
      lastSeen: number
      knownCount: number
      unknownCount: number
        nextReview: number
        fuzzyCount: number
      }) => void
      favoriteSlot?: React.ReactNode
    }) => (
    <div data-testid="quickmemory-mode">
      reviewWords:{vocabulary.map(word => word.word).join(',')}
      {favoriteSlot}
      {vocabulary[1] && onIndexChange ? (
        <button type="button" onClick={() => onIndexChange(1)}>go-second-word</button>
      ) : null}
      {vocabulary[0] && onQuickMemoryRecordChange ? (
        <button
          type="button"
          onClick={() => onQuickMemoryRecordChange(vocabulary[0], {
            status: 'known',
            firstSeen: 1000,
            lastSeen: 2000,
            knownCount: QUICK_MEMORY_MASTERY_TARGET,
            unknownCount: 0,
            nextReview: 0,
            fuzzyCount: 0,
          })}
        >
          finish-ebbinghaus
        </button>
      ) : null}
      {reviewHasMore && onContinueReview ? (
        <button type="button" onClick={onContinueReview}>continue-review</button>
      ) : null}
    </div>
  ),
}))

describe('PracticePage quick-memory review mode', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    practiceControlBarMock.mockClear()
    fetchMock.mockReset()
    toggleFavoriteMock.mockReset()
    localStorage.clear()
  })

  it('loads the dedicated Ebbinghaus review queue instead of the day vocabulary list', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      reviewLimitCustomized: true,
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
            { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
          ],
          summary: {
            due_count: 1,
            upcoming_count: 1,
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
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha,beta')
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due')
    expect(startSessionMock).not.toHaveBeenCalled()
  })

  it('migrates legacy uncustomized review batches back to the default unlimited limit', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '50',
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=0&within_days=3&offset=0&scope=due') {
        return Promise.resolve({
          words: [{ word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' }],
          summary: {
            due_count: 1,
            upcoming_count: 0,
            returned_count: 1,
            review_window_days: 3,
            offset: 0,
            limit: null,
            total_count: 1,
            has_more: false,
            next_offset: null,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha')
    })

    expect(JSON.parse(localStorage.getItem('app_settings') || '{}')).toMatchObject({
      reviewLimit: 'unlimited',
      reviewLimitCustomized: false,
    })
  })

  it('preserves a deliberate 50-word batch when the user explicitly customized the review size', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '50',
      reviewLimitCustomized: true,
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=50&within_days=3&offset=0&scope=due') {
        return Promise.resolve({
          words: [{ word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' }],
          summary: {
            due_count: 1,
            upcoming_count: 0,
            returned_count: 1,
            review_window_days: 3,
            offset: 0,
            limit: 50,
            total_count: 1,
            has_more: false,
            next_offset: null,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha')
    })
  })

  it('treats unlimited review batches as no cap instead of collapsing them to a single word', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: 'unlimited',
      reviewLimitCustomized: true,
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=0&within_days=3&offset=0&scope=due') {
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
            limit: null,
            total_count: 2,
            has_more: false,
            next_offset: null,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha,beta')
    })
  })

  it('shows the empty review state after the due queue resolves with no words', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      reviewLimitCustomized: true,
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due') {
        return Promise.resolve({
          words: [],
          summary: {
            due_count: 0,
            upcoming_count: 0,
            returned_count: 0,
            review_window_days: 3,
            offset: 0,
            limit: 10,
            total_count: 0,
            has_more: false,
            next_offset: null,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('暂无待复习的单词')).toBeInTheDocument()
    })
  })

  it('routes the Shift+W favorite shortcut to the currently displayed quick-memory word', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=0&within_days=1&offset=0&scope=due') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
            { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
          ],
          summary: {
            due_count: 2,
            upcoming_count: 0,
            returned_count: 2,
            review_window_days: 1,
            offset: 0,
            limit: null,
            total_count: 2,
            has_more: false,
            next_offset: null,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha,beta')
    })

    await user.click(screen.getByRole('button', { name: 'go-second-word' }))
    fireEvent.keyDown(window, { key: 'W', code: 'KeyW', shiftKey: true })

    expect(toggleFavoriteMock).toHaveBeenCalledWith(
      expect.objectContaining({ word: 'beta' }),
      expect.objectContaining({
        bookId: null,
        chapterId: null,
        chapterTitle: '艾宾浩斯复习',
      }),
    )
  })
})
