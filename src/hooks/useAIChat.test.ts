// ── Tests for src/hooks/useAIChat.ts ──────────────────────────────────────────

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import {
  logSession,
  recordModeAnswer,
  startSession,
  useAIChat,
} from './useAIChat'
import { clearGlobalLearningContext, setGlobalLearningContext } from '../contexts/AIChatContext'
import { STORAGE_KEYS } from '../constants'

const QUICK_MEMORY_KEY = 'quick_memory_records'
const MODE_PERF_KEY = 'mode_performance'

beforeEach(() => {
  localStorage.clear()
  clearGlobalLearningContext()
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

describe('startSession recovery', () => {
  it('reconciles a cached unfinished session before opening a new one', async () => {
    const now = Date.now()
    localStorage.setItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION, JSON.stringify({
      version: 1,
      sessionId: 88,
      mode: 'quickmemory',
      bookId: 'book-old',
      chapterId: '3',
      startedAt: now - 5 * 60 * 1000,
      lastActiveAt: now - 60 * 1000,
      wordsStudied: 4,
      correctCount: 3,
      wrongCount: 1,
    }))

    const mockFetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 88 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ sessionId: 99 }), { status: 200 }))
    vi.stubGlobal('fetch', mockFetch)

    const sessionId = await startSession({
      mode: 'smart',
      bookId: 'book-new',
      chapterId: '5',
    })

    expect(sessionId).toBe(99)
    expect(mockFetch).toHaveBeenCalledTimes(2)
    expect(mockFetch.mock.calls[0][0]).toBe('/api/ai/log-session')
    expect(mockFetch.mock.calls[1][0]).toBe('/api/ai/start-session')

    const recoveredBody = JSON.parse(mockFetch.mock.calls[0][1].body as string)
    expect(recoveredBody.sessionId).toBe(88)
    expect(recoveredBody.endedAt).toBeGreaterThan(recoveredBody.startedAt)

    const nextSnapshot = JSON.parse(localStorage.getItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION) || '{}')
    expect(nextSnapshot.sessionId).toBe(99)
    expect(nextSnapshot.mode).toBe('smart')
    vi.restoreAllMocks()
  })
})

describe('useAIChat semantic commands', () => {
  it('records pronunciation after a semantic start flow and free-form reply', async () => {
    setGlobalLearningContext({
      currentWord: 'dynamic',
      currentBook: 'ielts_speaking',
      currentChapter: '2',
    })

    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({
        word: 'dynamic',
        score: 88,
        passed: true,
        stress_feedback: '重音稳定',
        vowel_feedback: '元音自然',
        speed_feedback: '语速自然',
      }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useAIChat())

    await act(async () => {
      await result.current.sendMessage('开始发音训练')
    })

    expect(mockFetch).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.sendMessage('Dynamic pricing can confuse users.')
    })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/ai/pronunciation-check')
    const body = JSON.parse(options.body as string)
    expect(body).toMatchObject({
      word: 'dynamic',
      transcript: 'dynamic',
      sentence: 'Dynamic pricing can confuse users.',
      bookId: 'ielts_speaking',
      chapterId: '2',
    })

    await waitFor(() => {
      const content = result.current.messages.at(-1)?.content || ''
      expect(content).toContain('已记录：发音 + 造句证据')
    })

    vi.restoreAllMocks()
  })

  it('records pronunciation evidence with current learning context', async () => {
    setGlobalLearningContext({
      currentWord: 'dynamic',
      currentBook: 'ielts_speaking',
      currentChapter: '2',
    })

    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({
        word: 'dynamic',
        score: 85,
        passed: true,
        stress_feedback: '重音稳定',
        vowel_feedback: '元音清晰',
        speed_feedback: '语速自然',
      }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useAIChat())

    await act(async () => {
      await result.current.sendMessage([
        '记录发音',
        '单词：dynamic',
        '我的跟读：dynamic',
        '我的例句：Dynamic pricing can confuse users.',
      ].join('\n'))
    })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/ai/pronunciation-check')
    const body = JSON.parse(options.body as string)
    expect(body).toMatchObject({
      word: 'dynamic',
      transcript: 'dynamic',
      sentence: 'Dynamic pricing can confuse users.',
      bookId: 'ielts_speaking',
      chapterId: '2',
    })

    await waitFor(() => {
      expect(result.current.messages.at(-1)?.content).toContain('已记录：发音 + 造句证据')
    })

    vi.restoreAllMocks()
  })

  it('records speaking answers after a semantic task prompt and direct reply', async () => {
    setGlobalLearningContext({
      currentWord: 'dynamic',
      currentBook: 'ielts_speaking',
      currentChapter: '2',
    })

    const mockFetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        part: 1,
        topic: 'education',
        question: 'Part 1: How do you improve your academic vocabulary?',
        follow_ups: ['可以给一个学习场景。'],
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        part: 1,
        topic: 'education',
        question: 'Part 1: How do you improve your academic vocabulary?',
        follow_ups: ['能再补充一个具体例子吗？'],
      }), { status: 200 }))
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useAIChat())

    await act(async () => {
      await result.current.sendMessage('开始口语训练')
    })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    expect(mockFetch.mock.calls[0][0]).toBe('/api/ai/speaking-simulate')

    await act(async () => {
      await result.current.sendMessage('Dynamic vocabulary helped me sound more coherent in the exam.')
    })

    expect(mockFetch).toHaveBeenCalledTimes(2)
    const [url, options] = mockFetch.mock.calls[1]
    expect(url).toBe('/api/ai/speaking-simulate')
    const body = JSON.parse(options.body as string)
    expect(body).toMatchObject({
      part: 1,
      topic: 'education',
      targetWords: ['dynamic'],
      responseText: 'Dynamic vocabulary helped me sound more coherent in the exam.',
      bookId: 'ielts_speaking',
      chapterId: '2',
    })

    await waitFor(() => {
      const lastMessage = result.current.messages.at(-1)
      expect(lastMessage?.content).toContain('已记录你的回答')
      expect(lastMessage?.options).toContain('我再补充一句')
    })

    vi.restoreAllMocks()
  })

  it('records speaking answers with target words and surfaces follow-ups', async () => {
    setGlobalLearningContext({
      currentWord: 'dynamic',
      currentBook: 'ielts_speaking',
      currentChapter: '2',
    })

    const mockFetch = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({
        part: 2,
        topic: 'education',
        question: 'Part 2: Describe a time when education vocabulary helped your IELTS performance.',
        follow_ups: ['请给一个具体例子。', '能否换成更学术的表达？'],
      }), { status: 200 })),
    )
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useAIChat())

    await act(async () => {
      await result.current.sendMessage([
        '记录口语回答',
        'Part：2',
        '主题：education',
        '目标词：dynamic、coherent',
        '我的回答：Dynamic vocabulary helped me sound more coherent.',
      ].join('\n'))
    })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/ai/speaking-simulate')
    const body = JSON.parse(options.body as string)
    expect(body).toMatchObject({
      part: 2,
      topic: 'education',
      targetWords: ['dynamic', 'coherent'],
      responseText: 'Dynamic vocabulary helped me sound more coherent.',
      bookId: 'ielts_speaking',
      chapterId: '2',
    })

    await waitFor(() => {
      const content = result.current.messages.at(-1)?.content || ''
      expect(content).toContain('已记录你的回答')
      expect(content).toContain('目标词：dynamic、coherent')
      expect(content).toContain('请给一个具体例子。')
    })

    vi.restoreAllMocks()
  })
})
