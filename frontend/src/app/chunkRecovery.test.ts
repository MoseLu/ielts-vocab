import { describe, expect, it } from 'vitest'
import { isRecoverableChunkLoadError } from './chunkRecovery'

describe('isRecoverableChunkLoadError', () => {
  it('matches stale vite chunk fetch failures', () => {
    expect(isRecoverableChunkLoadError(new TypeError('Failed to fetch dynamically imported module'))).toBe(true)
    expect(isRecoverableChunkLoadError(new Error('Importing a module script failed.'))).toBe(true)
  })

  it('ignores unrelated runtime failures', () => {
    expect(isRecoverableChunkLoadError(new Error('Network Error'))).toBe(false)
    expect(isRecoverableChunkLoadError('Something else broke')).toBe(false)
  })
})
