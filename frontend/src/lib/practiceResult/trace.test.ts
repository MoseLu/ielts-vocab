import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildPracticeIdempotencyKey,
  isValidPracticeIdempotencyKey,
} from './commandKeys'
import {
  createPracticeTraceId,
  isValidPracticeTraceId,
  normalizePracticeTraceId,
} from './trace'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('practice result trace helpers', () => {
  it('creates trace ids with a stable practice prefix', () => {
    vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('11111111-2222-4333-8444-555555555555')

    const traceId = createPracticeTraceId()

    expect(traceId).toBe('practice:11111111-2222-4333-8444-555555555555')
    expect(isValidPracticeTraceId(traceId)).toBe(true)
  })

  it('normalizes invalid trace ids by creating a new one', () => {
    vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee')

    expect(normalizePracticeTraceId('bad space')).toBe('practice:aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee')
  })
})

describe('practice result idempotency keys', () => {
  it('builds deterministic keys without user identity', () => {
    const key = buildPracticeIdempotencyKey({
      sessionId: 42,
      mode: 'Smart',
      scopeKey: 'book-1/chapter 2',
      wordKey: 'Abandon',
      dimension: 'meaning',
      attemptIndex: 3,
    })

    expect(key).toBe('practice:42:smart:book-1-chapter-2:abandon:meaning:3')
    expect(isValidPracticeIdempotencyKey(key)).toBe(true)
    expect(key).not.toContain('user')
  })

  it('falls back to local session ids before a backend session exists', () => {
    const key = buildPracticeIdempotencyKey({
      localSessionId: 'local round 1',
      mode: 'quickmemory',
      scopeKey: 'due-review',
      wordKey: 'precise',
      dimension: 'recognition',
      attemptIndex: 0,
    })

    expect(key).toBe('practice:local-round-1:quickmemory:due-review:precise:recognition:0')
    expect(isValidPracticeIdempotencyKey(key)).toBe(true)
  })
})
