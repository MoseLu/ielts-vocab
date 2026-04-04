import { describe, expect, it } from 'vitest'
import {
  buildChoiceStageGuide,
  buildDictationStageGuide,
  buildQuickMemoryStageGuide,
} from './practiceStageGuide'

describe('practiceStageGuide', () => {
  it('marks review choice stages with anti-forgetting guidance', () => {
    const guide = buildChoiceStageGuide({
      mode: 'meaning',
      queueIndex: 1,
      total: 5,
      reviewMode: true,
    })

    expect(guide.laneLabel).toBe('到期复习')
    expect(guide.context).toContain('对抗遗忘')
    expect(guide.rows.map(row => row.label)).toEqual([
      '这一步干什么',
      '这一步有什么作用',
      '过关后会怎样',
    ])
  })

  it('keeps error dictation stages focused on pinpointing the mistake', () => {
    const guide = buildDictationStageGuide({
      queueIndex: 0,
      total: 3,
      errorMode: true,
      isExampleMode: false,
      phase: 'review',
      isCorrect: false,
    })

    expect(guide.laneLabel).toBe('错词攻坚')
    expect(guide.title).toBe('别急着跳关，先看清错在哪里')
    expect(guide.rows[1]?.value).toContain('字母层级')
  })

  it('builds quick-memory review guidance around the user choice', () => {
    const guide = buildQuickMemoryStageGuide({
      queueIndex: 2,
      total: 8,
      phase: 'review',
      choice: 'unknown',
    })

    expect(guide.title).toBe('立刻复盘，把陌生词钉住')
    expect(guide.rows[2]?.value).toContain('后续复习链')
  })
})
