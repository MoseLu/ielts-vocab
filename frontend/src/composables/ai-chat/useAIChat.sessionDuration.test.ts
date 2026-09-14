import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushStudySessionOnPageHide, logSession, recordStudySessionUserActivity } from './sessionTracking'
import { STORAGE_KEYS } from '../../constants'

const STARTED_AT = Date.parse('2026-04-11T18:08:40.000Z')
const LAST_ACTIVE_AT = Date.parse('2026-04-11T18:08:48.000Z')
const EXPECTED_DURATION_SECONDS = 2 * 60 + 8
const EXPECTED_ENDED_AT = LAST_ACTIVE_AT + 2 * 60 * 1000

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

  it('uses the same idle cap for pagehide session flushes', async () => {
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
      await Promise.resolve()
      await Promise.resolve()
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

  it('refreshes the idle cap from real user activity', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)
    writeActiveSession(603)
    const activityAt = LAST_ACTIVE_AT + 90 * 1000

    recordStudySessionUserActivity(activityAt)

    await logSession({
      sessionId: 603,
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
    expect(body.durationSeconds).toBe(2 * 60 + 98)
    expect(body.endedAt).toBe(activityAt + 2 * 60 * 1000)
    expect(body.durationCappedByActivity).toBe(true)
  })

  it('does not refresh the idle cap from passive mouse movement', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)
    writeActiveSession(604)

    window.dispatchEvent(new MouseEvent('mousemove'))

    await logSession({
      sessionId: 604,
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
})
