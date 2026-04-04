import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useLearningStats } from './useLearningStats'

const apiFetchMock = vi.fn()
const authState = vi.hoisted(() => ({
  user: { id: 2, username: 'luo' },
}))

vi.mock('../../../contexts', () => ({
  useAuth: () => ({
    user: authState.user,
  }),
}))

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

describe('useLearningStats', () => {
  beforeEach(() => {
    vi.useRealTimers()
    apiFetchMock.mockReset()
    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith('/api/ai/learning-stats?')) {
        return Promise.resolve({
          daily: [],
          books: [],
          modes: [],
          summary: null,
          alltime: { today_review_words: 2 },
          mode_breakdown: [],
          pie_chart: [],
          wrong_top10: [],
          chapter_breakdown: [],
          chapter_mode_stats: [],
          use_fallback: false,
        })
      }

      if (url === '/api/ai/learner-profile') {
        return Promise.resolve(null)
      }

      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })
  })

  it('refetches stats when the window regains focus and disables caching for stats requests', async () => {
    let nowMs = 1_000
    const dateNowSpy = vi.spyOn(Date, 'now').mockImplementation(() => nowMs)

    renderHook(() => useLearningStats(7, 'all', 'all'))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2)
    })

    expect(apiFetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/ai/learning-stats?days=7',
      { cache: 'no-store' },
    )
    expect(apiFetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/ai/learner-profile',
      { cache: 'no-store' },
    )

    act(() => {
      nowMs += 2_000
      window.dispatchEvent(new Event('focus'))
    })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(4)
    })

    dateNowSpy.mockRestore()
  })

  it('periodically refetches stats while the page stays visible', async () => {
    let nowMs = 1_000
    const dateNowSpy = vi.spyOn(Date, 'now').mockImplementation(() => nowMs)
    const intervalCallbacks: Array<() => void> = []
    const setIntervalSpy = vi.spyOn(window, 'setInterval').mockImplementation(((handler: TimerHandler) => {
      intervalCallbacks.push(handler as () => void)
      return 1 as unknown as number
    }) as typeof window.setInterval)
    const clearIntervalSpy = vi.spyOn(window, 'clearInterval').mockImplementation(() => {})

    renderHook(() => useLearningStats(7, 'all', 'all'))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2)
    })

    act(() => {
      nowMs += 60_000
      intervalCallbacks[0]?.()
    })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(4)
    })

    clearIntervalSpy.mockRestore()
    setIntervalSpy.mockRestore()
    dateNowSpy.mockRestore()
  })
})
