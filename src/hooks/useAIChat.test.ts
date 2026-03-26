// ── Tests for src/hooks/useAIChat.ts ──────────────────────────────────────────

import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  logSession,
  recordModeAnswer,
} from './useAIChat'

const QUICK_MEMORY_KEY = 'quick_memory_records'
const MODE_PERF_KEY = 'mode_performance'

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

// ── recordModeAnswer ──────────────────────────────────────────────────────────

describe('recordModeAnswer', () => {
  it('creates a new mode entry on first call', () => {
    recordModeAnswer('smart', true)
    const stored = JSON.parse(localStorage.getItem(MODE_PERF_KEY)!)
    expect(stored.smart).toEqual({ correct: 1, wrong: 0 })
  })

  it('increments correct count when correct=true', () => {
    recordModeAnswer('listening', true)
    recordModeAnswer('listening', true)
    recordModeAnswer('listening', false)
    const stored = JSON.parse(localStorage.getItem(MODE_PERF_KEY)!)
    expect(stored.listening).toEqual({ correct: 2, wrong: 1 })
  })

  it('increments wrong count when correct=false', () => {
    recordModeAnswer('dictation', false)
    recordModeAnswer('dictation', false)
    const stored = JSON.parse(localStorage.getItem(MODE_PERF_KEY)!)
    expect(stored.dictation).toEqual({ correct: 0, wrong: 2 })
  })

  it('handles malformed localStorage gracefully', () => {
    localStorage.setItem(MODE_PERF_KEY, 'not json')
    expect(() => recordModeAnswer('test', true)).not.toThrow()
  })
})

// ── logSession ───────────────────────────────────────────────────────────────

describe('logSession', () => {
  it('sends POST with cookie credentials (HttpOnly session)', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)

    await logSession({
      mode: 'smart',
      bookId: 'book1',
      chapterId: 'ch1',
      wordsStudied: 20,
      correctCount: 18,
      wrongCount: 2,
      durationSeconds: 300,
      startedAt: Date.now() - 300000,
    })

    expect(mockFetch).toHaveBeenCalled()
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/ai/log-session')
    expect(options.credentials).toBe('include')
    vi.restoreAllMocks()
  })

  it('sends POST request with session data', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)

    const now = Date.now()
    await logSession({
      mode: 'meaning',
      bookId: 'book2',
      chapterId: null,
      wordsStudied: 10,
      correctCount: 9,
      wrongCount: 1,
      durationSeconds: 120,
      startedAt: now - 120000,
    })

    expect(mockFetch).toHaveBeenCalled()
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/ai/log-session')
    expect(options.method).toBe('POST')
    expect(options.credentials).toBe('include')
    const headers = options.headers as Record<string, string>
    expect(headers['Content-Type']).toContain('application/json')
    const body = JSON.parse(options.body as string)
    expect(body.mode).toBe('meaning')
    expect(body.wordsStudied).toBe(10)
    expect(body.correctCount).toBe(9)
    expect(body.wrongCount).toBe(1)
    vi.restoreAllMocks()
  })

  it('handles fetch errors gracefully (non-critical)', async () => {
    const mockFetch = vi.fn(() => Promise.reject(new Error('network error')))
    vi.stubGlobal('fetch', mockFetch)

    // Should not throw
    await expect(logSession({
      mode: 'smart',
      wordsStudied: 5,
      correctCount: 4,
      wrongCount: 1,
      durationSeconds: 60,
      startedAt: Date.now() - 60000,
    })).resolves.not.toThrow()
    vi.restoreAllMocks()
  })
})
