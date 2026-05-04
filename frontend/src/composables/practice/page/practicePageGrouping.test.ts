import { describe, expect, it } from 'vitest'
import { buildPracticeGroupWindows, resolvePracticeGroupWindow } from './practicePageGrouping'

describe('practice page chapter grouping', () => {
  it('merges the final short group into the previous group', () => {
    const windows = buildPracticeGroupWindows(202, 50)

    expect(windows).toEqual([
      { start: 0, end: 50, total: 202, groupSize: 50 },
      { start: 50, end: 100, total: 202, groupSize: 50 },
      { start: 100, end: 150, total: 202, groupSize: 50 },
      { start: 150, end: 202, total: 202, groupSize: 50 },
    ])
  })

  it('keeps a near-full chapter as one group', () => {
    expect(buildPracticeGroupWindows(51, 50)).toEqual([
      { start: 0, end: 51, total: 51, groupSize: 50 },
    ])
  })

  it('resolves saved chapter progress into the active group', () => {
    expect(resolvePracticeGroupWindow(202, 50, 60)).toEqual({
      start: 50,
      end: 100,
      total: 202,
      groupSize: 50,
    })
  })
})
