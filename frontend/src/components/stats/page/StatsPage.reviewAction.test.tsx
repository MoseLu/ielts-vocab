import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import StatsPage from './StatsPage'

const navigateMock = vi.fn()
const hooksState = vi.hoisted(() => ({
  wrongWords: {
    words: [],
    loading: false,
  },
  learningStats: {
    daily: [],
    books: [],
    modes: [],
    summary: {
      total_words: 40,
      total_duration_seconds: 1200,
      total_sessions: 3,
      accuracy: 90,
    },
    alltime: {
      total_words: 120,
      accuracy: 88,
      duration_seconds: 7200,
      today_accuracy: 92,
      today_duration_seconds: 900,
      today_new_words: 15,
      today_review_words: 10,
      alltime_review_words: 48,
      cumulative_review_events: 60,
      ebbinghaus_rate: 75,
      ebbinghaus_due_total: 20,
      ebbinghaus_met: 15,
      qm_word_total: 160,
      ebbinghaus_stages: [],
      upcoming_reviews_3d: 4,
      streak_days: 6,
      weakest_mode: 'listening',
      weakest_mode_accuracy: 70,
      trend_direction: 'improving' as const,
    },
    modeBreakdown: [],
    pieChart: [],
    wrongTop10: [],
    historyWrongTop10: [],
    pendingWrongTop10: [],
    chapterBreakdown: [],
    chapterModeStats: [],
    learnerProfile: null,
    useFallback: false,
    loading: false,
    learnerProfileLoading: false,
    refreshing: false,
    refetch: vi.fn(),
  },
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('../../../features/vocabulary/hooks', () => ({
  useWrongWords: () => hooksState.wrongWords,
  useLearningStats: () => hooksState.learningStats,
}))

describe('StatsPage review action', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        media: '',
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    class MockResizeObserver {
      observe = vi.fn()
      unobserve = vi.fn()
      disconnect = vi.fn()
    }

    Object.defineProperty(globalThis, 'ResizeObserver', {
      writable: true,
      value: MockResizeObserver,
    })
  })

  beforeEach(() => {
    navigateMock.mockReset()
  })

  it('starts the Ebbinghaus due review queue when the user clicks the review button', async () => {
    const user = userEvent.setup()
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent')

    render(<StatsPage />)

    await user.click(screen.getByRole('button', { name: '去复习' }))

    expect(dispatchSpy).toHaveBeenCalledWith(expect.objectContaining({
      type: 'practice-mode-request',
      detail: { mode: 'quickmemory' },
    }))
    expect(navigateMock).toHaveBeenCalledWith('/practice?review=due')
  })
})
