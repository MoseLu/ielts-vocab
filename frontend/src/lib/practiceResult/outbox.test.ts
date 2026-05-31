import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  enqueuePracticeResultCommand,
  getPracticeResultOutboxStorageKey,
  listRetryablePracticeResults,
  markPracticeResultAcked,
  markPracticeResultFailed,
  markPracticeResultSending,
  pruneAckedPracticeResults,
  readPracticeResultOutbox,
} from './outbox'
import type { PracticeResultCommand } from './types'

function command(overrides: Partial<PracticeResultCommand> = {}): PracticeResultCommand {
  return {
    traceId: 'practice:trace-1',
    idempotencyKey: 'practice:session-1:smart:book-1:abandon:meaning:0',
    userScope: '7',
    route: '/practice',
    mode: 'smart',
    scopeKey: 'book:book-1',
    scopeType: 'book',
    originScope: { scopeKey: 'book:book-1', scopeType: 'book', bookId: 'book-1' },
    dimension: 'meaning',
    word: 'abandon',
    result: 'correct',
    occurredAt: 1_000,
    adapter: 'practice',
    ...overrides,
  }
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-05-05T00:00:00.000Z'))
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('practice result outbox', () => {
  it('stores commands in a user-scoped outbox', () => {
    const entry = enqueuePracticeResultCommand(command())

    expect(entry.status).toBe('pending')
    expect(localStorage.getItem(getPracticeResultOutboxStorageKey('7'))).toContain('abandon')
    expect(readPracticeResultOutbox('7')).toHaveLength(1)
  })

  it('marks sending, failed, retryable, and acked states', () => {
    const item = command()

    markPracticeResultSending(item)
    expect(readPracticeResultOutbox('7')[0]).toMatchObject({ status: 'sending', attempts: 1 })

    markPracticeResultFailed(item, 'network down', 1_000)
    expect(listRetryablePracticeResults('7')).toHaveLength(0)

    vi.advanceTimersByTime(1_000)
    expect(listRetryablePracticeResults('7')).toHaveLength(1)

    markPracticeResultAcked(item)
    expect(readPracticeResultOutbox('7')[0]).toMatchObject({ status: 'acked' })
  })

  it('prunes old acked entries while keeping active work', () => {
    markPracticeResultAcked(command())
    enqueuePracticeResultCommand(command({
      idempotencyKey: 'practice:session-1:smart:book-1:basic:meaning:1',
      word: 'basic',
    }))

    vi.advanceTimersByTime(5_000)

    expect(pruneAckedPracticeResults('7', 1_000)).toBe(1)
    expect(readPracticeResultOutbox('7').map(entry => entry.command.word)).toEqual(['basic'])
  })

  it('caps stored active and acked entries before writing', () => {
    for (let index = 0; index < 70; index += 1) {
      markPracticeResultFailed(command({
        idempotencyKey: `practice:session-1:smart:book-1:active-${index}:meaning:${index}`,
        word: `active-${index}`,
        occurredAt: 1_000 + index,
      }), 'offline')
      vi.advanceTimersByTime(1)
    }

    for (let index = 0; index < 30; index += 1) {
      markPracticeResultAcked(command({
        idempotencyKey: `practice:session-1:smart:book-1:acked-${index}:meaning:${index}`,
        word: `acked-${index}`,
        occurredAt: 2_000 + index,
      }))
      vi.advanceTimersByTime(1)
    }

    const entries = readPracticeResultOutbox('7')
    const activeWords = entries
      .filter(entry => entry.status !== 'acked')
      .map(entry => entry.command.word)
    const ackedWords = entries
      .filter(entry => entry.status === 'acked')
      .map(entry => entry.command.word)

    expect(activeWords).toHaveLength(60)
    expect(ackedWords).toHaveLength(20)
    expect(activeWords).toContain('active-69')
    expect(activeWords).not.toContain('active-0')
    expect(ackedWords).toContain('acked-29')
    expect(ackedWords).not.toContain('acked-0')
  })

  it('does not throw when browser storage rejects the outbox write', () => {
    const setItem = vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
      throw new DOMException('quota exceeded', 'QuotaExceededError')
    })

    expect(() => enqueuePracticeResultCommand(command())).not.toThrow()
    expect(setItem).toHaveBeenCalled()
    expect(readPracticeResultOutbox('7')).toEqual([])
  })
})
