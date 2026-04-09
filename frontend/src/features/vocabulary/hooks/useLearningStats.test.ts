import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLearningStats } from './useLearningStats'

const apiFetchMock = vi.fn()
const reconcileQuickMemoryRecordsWithBackendMock = vi.fn(() => Promise.resolve({ uploadedCount: 0 }))
const authState = vi.hoisted(() => ({
  user: { id: 2, username: 'luo' },
  isLoading: false,
}))

vi.mock('../../../contexts', () => ({
  useAuth: () => ({
    user: authState.user,
    isLoading: authState.isLoading,
  }),
}))

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../../lib/quickMemorySync', () => ({
  reconcileQuickMemoryRecordsWithBackend: (...args: unknown[]) => reconcileQuickMemoryRecordsWithBackendMock(...args),
}))

function buildStatsResponse() {
  return {
    daily: [],
    books: [],
    modes: [],
    summary: null,
    alltime: { today_review_words: 2 },
    mode_breakdown: [],
    pie_chart: [],
    wrong_top10: [],
    history_wrong_top10: [],
    pending_wrong_top10: [],
    chapter_breakdown: [],
    chapter_mode_stats: [],
    use_fallback: false,
  }
}

function createDeferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(res => {
    resolve = res
  })

  return { promise, resolve }
}

describe('useLearningStats', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  beforeEach(() => {
    vi.useRealTimers()
    apiFetchMock.mockReset()
    reconcileQuickMemoryRecordsWithBackendMock.mockReset()
    reconcileQuickMemoryRecordsWithBackendMock.mockResolvedValue({ uploadedCount: 0 })
    authState.user = { id: 2, username: 'luo' }
    authState.isLoading = false
    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith('/api/ai/learning-stats?')) {
        return Promise.resolve(buildStatsResponse())
      }

      if (url === '/api/ai/learner-profile?view=stats') {
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
      '/api/ai/learner-profile?view=stats',
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

  it('skips periodic polling when the caller disables it', async () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval')

    renderHook(() => useLearningStats(7, 'all', 'all', { pollIntervalMs: 0 }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2)
    })

    const statsPollingCalls = setIntervalSpy.mock.calls.filter(([, timeout]) => timeout === 60_000)
    expect(statsPollingCalls).toHaveLength(0)
    setIntervalSpy.mockRestore()
  })

  it('keeps loading false during background refreshes after the first fetch resolves', async () => {
    let nowMs = 1_000
    let statsRequestCount = 0
    const dateNowSpy = vi.spyOn(Date, 'now').mockImplementation(() => nowMs)
    const backgroundStats = createDeferred<ReturnType<typeof buildStatsResponse>>()

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith('/api/ai/learning-stats?')) {
        statsRequestCount += 1
        if (statsRequestCount === 2) {
          return backgroundStats.promise
        }

        return Promise.resolve(buildStatsResponse())
      }

      if (url === '/api/ai/learner-profile?view=stats') {
        return Promise.resolve(null)
      }

      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { result } = renderHook(() => useLearningStats(7, 'all', 'all'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      nowMs += 2_000
      window.dispatchEvent(new Event('focus'))
    })

    await waitFor(() => {
      expect(statsRequestCount).toBe(2)
      expect(result.current.refreshing).toBe(true)
    })

    expect(result.current.loading).toBe(false)

    act(() => {
      backgroundStats.resolve(buildStatsResponse())
    })

    await waitFor(() => {
      expect(result.current.refreshing).toBe(false)
    })

    dateNowSpy.mockRestore()
  })

  it('keeps the first-screen loading state until auth hydration finishes', async () => {
    authState.user = null
    authState.isLoading = true

    const { result, rerender } = renderHook(() => useLearningStats(7, 'all', 'all', { pollIntervalMs: 0 }))

    expect(result.current.loading).toBe(true)
    expect(apiFetchMock).not.toHaveBeenCalled()

    authState.user = { id: 2, username: 'luo' }
    authState.isLoading = false
    rerender()

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2)
      expect(result.current.loading).toBe(false)
    })
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

  it('starts stats requests immediately on the stats page while quick-memory reconciliation continues in the background', async () => {
    const reconcileDeferred = createDeferred<{ uploadedCount: number }>()
    reconcileQuickMemoryRecordsWithBackendMock.mockReturnValue(reconcileDeferred.promise)

    const { result } = renderHook(() => useLearningStats(7, 'all', 'all', {
      pollIntervalMs: 0,
      blockInitialQuickMemoryReconcile: false,
      blockOnLearnerProfile: false,
    }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2)
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/ai/learning-stats?days=7',
        { cache: 'no-store' },
      )
    })

    expect(reconcileQuickMemoryRecordsWithBackendMock).toHaveBeenCalledTimes(1)
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      reconcileDeferred.resolve({ uploadedCount: 0 })
    })
  })

  it('refreshes stats once more after a background reconcile uploads newer quick-memory records', async () => {
    let statsRequestCount = 0
    reconcileQuickMemoryRecordsWithBackendMock.mockResolvedValue({ uploadedCount: 2 })
    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith('/api/ai/learning-stats?')) {
        statsRequestCount += 1
        return Promise.resolve(buildStatsResponse())
      }

      if (url === '/api/ai/learner-profile?view=stats') {
        return Promise.resolve(null)
      }

      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { result } = renderHook(() => useLearningStats(7, 'all', 'all', {
      pollIntervalMs: 0,
      blockInitialQuickMemoryReconcile: false,
      blockOnLearnerProfile: false,
    }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.refreshing).toBe(false)
      expect(statsRequestCount).toBe(2)
    })
  })
})
