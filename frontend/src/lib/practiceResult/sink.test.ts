import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { buildPracticeResultCommand } from './adapters'
import { readPracticeResultOutbox } from './outbox'
import { applyPracticeResult } from './sink'

beforeEach(() => {
  localStorage.clear()
  vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('11111111-2222-4333-8444-555555555555')
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('practice result sink', () => {
  it('persists the command before applying legacy plane handlers', async () => {
    const handledPlanes: string[] = []
    const command = buildPracticeResultCommand({
      userScope: 7,
      route: '/practice',
      mode: 'smart',
      dimension: 'meaning',
      word: 'abandon',
      result: 'correct',
      session: { sessionId: 42 },
      progressScope: { bookId: 'book-1', chapterId: 2 },
    })

    const result = await applyPracticeResult(command, {
      progress: () => {
        expect(readPracticeResultOutbox('7')[0]).toMatchObject({ status: 'sending' })
        handledPlanes.push('progress')
      },
      session: () => { handledPlanes.push('session') },
      wordMastery: () => { handledPlanes.push('wordMastery') },
      smartStats: () => { handledPlanes.push('smartStats') },
      wrongWordsOnFailure: () => { handledPlanes.push('wrongWordsOnFailure') },
      modePerformance: () => { handledPlanes.push('modePerformance') },
    })

    expect(result.planes.every(plane => plane.status === 'ok')).toBe(true)
    expect(handledPlanes).toEqual([
      'progress',
      'session',
      'wordMastery',
      'smartStats',
      'wrongWordsOnFailure',
      'modePerformance',
    ])
    expect(readPracticeResultOutbox('7')[0]).toMatchObject({ status: 'acked' })
  })

  it('marks missing optional handlers as skipped', async () => {
    const command = buildPracticeResultCommand({
      userScope: 7,
      route: '/practice',
      mode: 'follow',
      dimension: 'speaking',
      word: 'abandon',
      result: 'wrong',
    })

    const result = await applyPracticeResult(command, {
      progress: () => {},
      session: () => {},
    })

    expect(result.planes).toEqual(expect.arrayContaining([
      { plane: 'progress', status: 'ok' },
      { plane: 'session', status: 'ok' },
      { plane: 'wordMastery', status: 'skipped' },
      { plane: 'wrongWordsOnFailure', status: 'skipped' },
    ]))
    expect(readPracticeResultOutbox('7')[0]).toMatchObject({ status: 'acked' })
  })

  it('marks the command failed when a required plane handler fails', async () => {
    const command = buildPracticeResultCommand({
      userScope: 7,
      route: '/practice',
      mode: 'meaning',
      dimension: 'meaning',
      word: 'abandon',
      result: 'wrong',
    })

    const result = await applyPracticeResult(command, {
      progress: () => {},
      session: () => {
        throw new Error('session unavailable')
      },
    })

    expect(result.planes).toEqual(expect.arrayContaining([
      { plane: 'session', status: 'failed', error: 'session unavailable' },
    ]))
    expect(readPracticeResultOutbox('7')[0]).toMatchObject({
      status: 'failed',
      lastError: 'session unavailable',
    })
  })
})
