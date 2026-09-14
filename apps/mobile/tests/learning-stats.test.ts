import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { LearningStatsPayload } from '@ielts-vocab/app-core'
import {
  loadLearningStatsCached,
  peekLearningStats,
  resetLearningStatsCacheForTests,
} from '../src/api/learningStatsCache'

const sampleStats = {
  books: [],
  chapter_breakdown: [],
  chapter_mode_stats: [],
  daily: [],
  history_wrong_top10: [],
  mode_breakdown: [],
  modes: [],
  pending_wrong_top10: [],
  pie_chart: [],
  summary: {},
  alltime: { today_mastered_words: 12 },
  use_fallback: false,
  wrong_top10: [],
  wrong_words: {},
} satisfies LearningStatsPayload

describe('learning stats cache', () => {
  it('dedupes concurrent loadLearningStats fetches', async () => {
    resetLearningStatsCacheForTests()
    let calls = 0
    const fetcher = async () => {
      calls += 1
      await new Promise(resolve => setTimeout(resolve, 10))
      return sampleStats
    }

    const [left, right] = await Promise.all([
      loadLearningStatsCached(fetcher),
      loadLearningStatsCached(fetcher),
    ])

    assert.equal(calls, 1)
    assert.equal(left.alltime?.today_mastered_words, 12)
    assert.equal(right.alltime?.today_mastered_words, 12)
    assert.equal(peekLearningStats()?.alltime?.today_mastered_words, 12)
  })

  it('returns cached payload synchronously from peekLearningStats', async () => {
    resetLearningStatsCacheForTests()
    assert.equal(peekLearningStats(), null)

    await loadLearningStatsCached(async () => sampleStats)

    assert.equal(peekLearningStats()?.alltime?.today_mastered_words, 12)
  })

  it('reuses a warm cache without another fetch inside the ttl window', async () => {
    resetLearningStatsCacheForTests()
    let calls = 0
    const fetcher = async () => {
      calls += 1
      return sampleStats
    }

    await loadLearningStatsCached(fetcher)
    await loadLearningStatsCached(fetcher)

    assert.equal(calls, 1)
  })
})
