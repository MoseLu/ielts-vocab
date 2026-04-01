import {
  QUICK_MEMORY_MASTERY_TARGET,
  resetQuickMemoryRecord,
  updateQuickMemoryRecord,
} from './quickMemory'

describe('quickMemory', () => {
  it('resets the consecutive known count when the learner gets a word wrong', () => {
    const { records: seeded } = updateQuickMemoryRecord({}, 'alpha', 'known', false, 1000)
    const result = updateQuickMemoryRecord(seeded, 'alpha', 'unknown', false, 2000)

    expect(result.record).toEqual(expect.objectContaining({
      status: 'unknown',
      knownCount: 0,
      unknownCount: 1,
      lastSeen: 2000,
    }))
  })

  it('marks a word as mastered after the full Ebbinghaus streak completes', () => {
    let records = {}
    let currentRecord = null

    for (let index = 0; index < QUICK_MEMORY_MASTERY_TARGET; index += 1) {
      const result = updateQuickMemoryRecord(records, 'alpha', 'known', false, 1000 + index)
      records = result.records
      currentRecord = result.record
    }

    expect(currentRecord).toEqual(expect.objectContaining({
      status: 'known',
      knownCount: QUICK_MEMORY_MASTERY_TARGET,
      nextReview: 0,
    }))
  })

  it('resets an existing word back to the start of the Ebbinghaus chain', () => {
    const { records: seeded } = updateQuickMemoryRecord({}, 'alpha', 'known', true, 1000)
    const result = resetQuickMemoryRecord(seeded, 'alpha', 2000)

    expect(result.record).toEqual(expect.objectContaining({
      status: 'unknown',
      knownCount: 0,
      fuzzyCount: 1,
      lastSeen: 2000,
    }))
    expect(result.record?.nextReview).toBeGreaterThan(2000)
  })
})
