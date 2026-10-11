import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const apiFetchMock = vi.hoisted(() => vi.fn())

vi.mock('../../../lib', () => ({
  apiFetch: apiFetchMock,
}))

import { getLearnerProfile, getLearningStats } from './learningStatsService'

describe('getLearningStats', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds the canonical query string with only the days filter', async () => {
    apiFetchMock.mockResolvedValueOnce({ summary: { days: 7 } })

    const result = await getLearningStats({ days: 7 })

    expect(apiFetchMock).toHaveBeenCalledTimes(1)
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/ai/learning-stats?days=7',
      { cache: 'no-store' },
    )
    expect(result).toEqual({ summary: { days: 7 } })
  })

  it('adds book_id when bookId is provided and not "all"', async () => {
    apiFetchMock.mockResolvedValueOnce({})

    await getLearningStats({ days: 30, bookId: 'ielts-core' })

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/ai/learning-stats?days=30&book_id=ielts-core',
      { cache: 'no-store' },
    )
  })

  it('adds mode when mode is provided and not "all"', async () => {
    apiFetchMock.mockResolvedValueOnce({})

    await getLearningStats({ days: 14, mode: 'dictation' })

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/ai/learning-stats?days=14&mode=dictation',
      { cache: 'no-store' },
    )
  })

  it('omits book_id and mode when the values equal "all"', async () => {
    apiFetchMock.mockResolvedValueOnce({})

    await getLearningStats({ days: 14, bookId: 'all', mode: 'all' })

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/ai/learning-stats?days=14',
      { cache: 'no-store' },
    )
  })

  it('propagates apiFetch failures', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('network down'))

    await expect(getLearningStats({ days: 7 })).rejects.toThrow('network down')
  })
})

describe('getLearnerProfile', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses the canonical stats-view URL with no-store cache', async () => {
    apiFetchMock.mockResolvedValueOnce({ dimensions: [] })

    const result = await getLearnerProfile()

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/ai/learner-profile?view=stats',
      { cache: 'no-store' },
    )
    expect(result).toEqual({ dimensions: [] })
  })

  it('returns null when the request fails (matches useLearningStats fallback)', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('500'))

    const result = await getLearnerProfile()

    expect(result).toBeNull()
  })
})
