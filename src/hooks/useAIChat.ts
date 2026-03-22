// ── useAIChat ─────────────────────────────────────────────────────────────────
// Smart AI assistant hook with:
//   - Personalized proactive greeting (calls /api/ai/greet on open)
//   - Cross-session memory (conversation history stored in DB)
//   - Rich context: quick memory records, mode performance, study sessions
//   - Session logging via logSession()

import { useState, useCallback } from 'react'
import { setGlobalLearningContext, getGlobalLearningContext } from '../contexts/AIChatContext'
import type { AIMessage, LearningContext } from '../types'
import { safeParse, AIAskResponseSchema } from '../lib'
import { STORAGE_KEYS } from '../constants'

interface UseAIChatOptions {
  userId?: string
}

export interface GeneratedBook {
  bookId: string
  title: string
  description: string
  chapters: Array<{ id: string; title: string; wordCount: number }>
  words: Array<{
    chapterId: string
    word: string
    phonetic: string
    pos: string
    definition: string
  }>
}

// ── Rich context builders ─────────────────────────────────────────────────────

function buildQuickMemorySummary() {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS) || '{}'
    const records = JSON.parse(raw) as Record<string, {
      status: 'known' | 'unknown'
      nextReview: number
    }>
    const now = Date.now()
    return Object.values(records).reduce(
      (acc, r) => {
        if (r.status === 'known') acc.known++
        else acc.unknown++
        if (r.nextReview && r.nextReview <= now) acc.dueToday++
        return acc
      },
      { known: 0, unknown: 0, dueToday: 0 },
    )
  } catch {
    return null
  }
}

function buildModePerformance() {
  try {
    return JSON.parse(localStorage.getItem('mode_performance') || '{}') as Record<
      string,
      { correct: number; wrong: number }
    >
  } catch {
    return {}
  }
}

function getAuthToken() {
  return localStorage.getItem('auth_token')
}

// ── Session logger ────────────────────────────────────────────────────────────

export async function logSession(data: {
  mode: string
  bookId?: string | null
  chapterId?: string | null
  wordsStudied: number
  correctCount: number
  wrongCount: number
  durationSeconds: number
  startedAt: number   // epoch ms
}) {
  const token = getAuthToken()
  if (!token) return
  try {
    await fetch('/api/ai/log-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        mode: data.mode,
        bookId: data.bookId,
        chapterId: data.chapterId,
        wordsStudied: data.wordsStudied,
        correctCount: data.correctCount,
        wrongCount: data.wrongCount,
        durationSeconds: data.durationSeconds,
        startedAt: data.startedAt,
      }),
    })
  } catch {
    // Non-critical
  }
}

// ── Mode performance tracker (client-side localStorage) ──────────────────────

export function recordModeAnswer(mode: string, correct: boolean) {
  try {
    const stored = JSON.parse(localStorage.getItem('mode_performance') || '{}') as Record<
      string,
      { correct: number; wrong: number }
    >
    if (!stored[mode]) stored[mode] = { correct: 0, wrong: 0 }
    if (correct) stored[mode].correct++
    else stored[mode].wrong++
    localStorage.setItem('mode_performance', JSON.stringify(stored))
  } catch {
    // Non-critical
  }
}

// ── Main hook ─────────────────────────────────────────────────────────────────

export function useAIChat(_options: UseAIChatOptions = {}) {
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isGreeting, setIsGreeting] = useState(false)   // greeting in progress
  const [greetingDone, setGreetingDone] = useState(false) // greeting has completed (success or fail)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [contextLoaded, setContextLoaded] = useState(false)

  // Build the rich context object — merges global context (updated by PracticePage)
  // with local quick-memory and mode-performance data from localStorage.
  const buildContext = useCallback(() => {
    return {
      ...getGlobalLearningContext(),
      quickMemorySummary: buildQuickMemorySummary(),
      modePerformance: buildModePerformance(),
    }
  }, [])

  const _syncWrongWords = useCallback(async () => {
    try {
      const token = getAuthToken()
      const wrongWords = JSON.parse(localStorage.getItem(STORAGE_KEYS.WRONG_WORDS) || '[]')
      if (wrongWords.length > 0 && token) {
        await fetch('/api/ai/wrong-words/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ words: wrongWords }),
        })
      }
    } catch {
      // Non-critical
    }
  }, [])

  const _fetchGreeting = useCallback(async () => {
    const token = getAuthToken()
    if (!token) return
    setIsGreeting(true)
    try {
      const resp = await fetch('/api/ai/greet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ context: buildContext() }),
      })
      if (!resp.ok) throw new Error('Greet failed')
      const raw = await resp.json()
      const result = safeParse(AIAskResponseSchema, raw)
      const content = result.success
        ? result.data.reply
        : '你好！我是雅思小助手，有什么我可以帮你的吗？'
      const options = (result.success && result.data.options) ? result.data.options : undefined
      setMessages([{
        id: 'greet',
        role: 'assistant',
        content,
        options: options ?? undefined,
        timestamp: Date.now(),
      }])
    } catch {
      setMessages([{
        id: 'greet',
        role: 'assistant',
        content: '你好！我是雅思小助手 👋\n\n我可以帮你分析学习进度、找出薄弱单词、制定复习计划，或者生成专属词书。有什么我可以帮你的吗？',
        timestamp: Date.now(),
      }])
    } finally {
      setIsGreeting(false)
      setGreetingDone(true)
    }
  }, [buildContext])

  const openPanel = useCallback(async () => {
    setIsOpen(true)
    if (contextLoaded) return
    setContextLoaded(true)
    await _syncWrongWords()
    await _fetchGreeting()
  }, [contextLoaded, _syncWrongWords, _fetchGreeting])

  const closePanel = useCallback(() => setIsOpen(false), [])

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: AIMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)

    try {
      const token = getAuthToken()
      const resp = await fetch('/api/ai/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          message: text,
          context: buildContext(),
        }),
      })

      if (!resp.ok) {
        const err = await resp.json()
        if (resp.status === 401 && err.error === 'Token has expired') {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('user')
          window.location.href = '/login?expired=1'
          throw new Error('登录已过期，请重新登录')
        }
        throw new Error(err.error || '请求失败')
      }

      const raw = await resp.json()
      const result = safeParse(AIAskResponseSchema, raw)
      if (!result.success) {
        console.error('[AI] Zod validation failed:', JSON.stringify(raw, null, 2))
        throw new Error('AI响应格式错误')
      }

      setMessages(prev => [...prev, {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content: result.data.reply,
        options: result.data.options ?? undefined,
        timestamp: Date.now(),
      }])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误'
      setError(msg)
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `出错了：${msg}`,
        timestamp: Date.now(),
      }])
    } finally {
      setIsLoading(false)
    }
  }, [buildContext])

  return {
    messages,
    isLoading,
    isGreeting,
    greetingDone,
    error,
    isOpen,
    contextLoaded,
    openPanel,
    closePanel,
    sendMessage,
  }
}
