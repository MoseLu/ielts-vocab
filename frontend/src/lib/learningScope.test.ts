import { describe, expect, it } from 'vitest'

import { buildLearningScope } from './learningScope'

describe('buildLearningScope', () => {
  it('normalizes legacy global scope keys to user scope', () => {
    expect(buildLearningScope({ scopeKey: 'global' }).scopeKey).toBe('user')
  })
})
