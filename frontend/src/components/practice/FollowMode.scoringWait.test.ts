import { describe, expect, it } from 'vitest'
import source from './FollowMode.tsx?raw'

describe('FollowMode scoring wait UX', () => {
  it('shows truthful scoring progress and keeps explanation async after score display', () => {
    expect(source).toContain('正在评分，通常几秒内完成。')
    expect(source).toContain('评分仍在进行，录音已提交，请稍等。')
    const scoringFlow = source.slice(source.indexOf('setScoreResult(result)'))
    expect(scoringFlow.indexOf('setScoreResult(result)')).toBeLessThan(scoringFlow.indexOf('void explainFollowReadPronunciation'))
  })
})
