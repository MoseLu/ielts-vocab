import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushStudySessionOnPageHide, logSession } from './useAIChat'
import { STORAGE_KEYS } from '../constants'

const STARTED_AT = Date.parse('2026-04-11T18:08:40.000Z')
const LAST_ACTIVE_AT = Date.parse('2026-04-11T18:08:48.000Z')
const EXPECTED_DURATION_SECONDS = 20 * 60 + 8
const EXPECTED_ENDED_AT = LAST_ACTIVE_AT + 20 * 60 * 1000

function writeActiveSession(sessionId: number) {
  localStorage.setItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION, JSON.stringify({
    version: 1,
    sessionId,
    mode: 'quickmemory',
    bookId: 'ielts_listening_premium',
    chapterId: '55',
    startedAt: STARTED_AT,
    lastActiveAt: LAST_ACTIVE_AT,
    wordsStudied: 1,
    correctCount: 0,
    wrongCount: 1,
  }))
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-04-12T01:19:26.000Z'))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('study session idle duration cap', () => {
  it('caps logged duration at the last active timestamp plus idle grace', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)
    writeActiveSession(601)

    await logSession({
      sessionId: 601,
      mode: 'quickmemory',
      bookId: 'ielts_listening_premium',
      chapterId: '55',
      wordsStudied: 1,
      correctCount: 0,
      wrongCount: 1,
      durationSeconds: Math.round((Date.now() - STARTED_AT) / 1000),
      startedAt: STARTED_AT,
    })

    const body = JSON.parse(mockFetch.mock.calls[0][1].body as string)
    expect(body.durationSeconds).toBe(EXPECTED_DURATION_SECONDS)
    expect(body.endedAt).toBe(EXPECTED_ENDED_AT)
    expect(body.durationCappedByActivity).toBe(true)
  })

  it('uses the same idle cap for pagehide session flushes', () => {
    const sendBeaconMock = vi.fn(() => false)
    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    const originalSendBeacon = navigator.sendBeacon
    vi.stubGlobal('fetch', mockFetch)
    Object.defineProperty(navigator, 'sendBeacon', {
      configurable: true,
      value: sendBeaconMock,
    })
    writeActiveSession(602)

    try {
      flushStudySessionOnPageHide({
        sessionId: 602,
        mode: 'quickmemory',
        bookId: 'ielts_listening_premium',
        chapterId: '55',
        wordsStudied: 1,
        correctCount: 0,
        wrongCount: 1,
        startedAt: STARTED_AT,
      })

      expect(sendBeaconMock).toHaveBeenCalledWith('/api/ai/log-session', expect.any(Blob))
      expect(mockFetch).toHaveBeenCalledWith('/api/ai/log-session', expect.objectContaining({ keepalive: true }))
      const body = JSON.parse(mockFetch.mock.calls[0][1].body as string)
      expect(body.durationSeconds).toBe(EXPECTED_DURATION_SECONDS)
      expect(body.endedAt).toBe(EXPECTED_ENDED_AT)
      expect(body.durationCappedByActivity).toBe(true)
    } finally {
      Object.defineProperty(navigator, 'sendBeacon', {
        configurable: true,
        value: originalSendBeacon,
      })
    }
  })
})
