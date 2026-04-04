import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLearningStats } from './useLearningStats'

const apiFetchMock = vi.fn()
const reconcileQuickMemoryRecordsWithBackendMock = vi.fn(() => Promise.resolve())
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

vi.mock('../../../lib/quickMemorySync', () => ({
  reconcileQuickMemoryRecordsWithBackend: (...args: unknown[]) => reconcileQuickMemoryRecordsWithBackendMock(...args),
}))

describe('useLearningStats', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  beforeEach(() => {
    vi.useRealTimers()
    apiFetchMock.mockReset()
    reconcileQuickMemoryRecordsWithBackendMock.mockReset()
    reconcileQuickMemoryRecordsWithBackendMock.mockResolvedValue(undefined)
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

    expect(reconcileQuickMemoryRecordsWithBackendMock).toHaveBeenCalledWith({
      skipIfLocalEmpty: true,
      minIntervalMs: 15_000,
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
    const nativeSetInterval = window.setInterval.bind(window)
    const setIntervalSpy = vi.spyOn(window, 'setInterval').mockImplementation(((handler: TimerHandler, timeout?: number, ...args: unknown[]) => {
      if (timeout === 60_000 && typeof handler === 'function') {
        intervalCallbacks.push(handler as () => void)
      }

      return nativeSetInterval(handler, timeout, ...args)
    }) as typeof window.setInterval)

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

    setIntervalSpy.mockRestore()
    dateNowSpy.mockRestore()
  })

  it('reconciles local quick-memory records before the stats request starts', async () => {
    renderHook(() => useLearningStats(7, 'all', 'all'))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2)
    })

    expect(reconcileQuickMemoryRecordsWithBackendMock).toHaveBeenCalledTimes(1)
    expect(
      reconcileQuickMemoryRecordsWithBackendMock.mock.invocationCallOrder[0],
    ).toBeLessThan(apiFetchMock.mock.invocationCallOrder[0] ?? Number.MAX_SAFE_INTEGER)
  })
})
