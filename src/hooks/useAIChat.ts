// ── useAIChat ─────────────────────────────────────────────────────────────────
// Smart AI assistant hook with:
//   - Personalized proactive greeting (calls /api/ai/greet on open)
//   - Cross-session memory (conversation history stored in DB)
//   - Rich context: quick memory records, mode performance, study sessions
//   - Session logging via logSession()

import { useState, useCallback } from 'react'
import { z } from 'zod'
import { setGlobalLearningContext, getGlobalLearningContext } from '../contexts/AIChatContext'
import type { AIMessage, LearningContext } from '../types'
import { safeParse, AIAskResponseSchema, apiFetch } from '../lib'
import { STORAGE_KEYS } from '../constants'

// ── localStorage schemas (permissive — extra keys ignored) ───────────────────
const QuickMemoryRecordSchema = z.record(
  z.string(),
  z.object({ status: z.enum(['known', 'unknown']), nextReview: z.number().optional() }).passthrough()
)
const ModePerformanceSchema = z.record(
  z.string(),
  z.object({ correct: z.number(), wrong: z.number() }).passthrough()
)
const WrongWordsSchema = z.array(z.record(z.string(), z.unknown()))
const SmartWordStatsSchema = z.record(
  z.string(),
  z.object({
    listening: z.object({ correct: z.number(), wrong: z.number() }),
    meaning:   z.object({ correct: z.number(), wrong: z.number() }),
    dictation: z.object({ correct: z.number(), wrong: z.number() }),
  }).passthrough()
)

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
    const parsed = safeParse(QuickMemoryRecordSchema, JSON.parse(localStorage.getItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS) || '{}'))
    if (!parsed.success) return null
    const records = parsed.data
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
    const parsed = safeParse(ModePerformanceSchema, JSON.parse(localStorage.getItem('mode_performance') || '{}'))
    return parsed.success ? parsed.data : {}
  } catch {
    return {}
  }
}

// ── Session timer ─────────────────────────────────────────────────────────────

/**
 * Notify the server that a practice session has started.
 * Returns the server-assigned sessionId, or null on failure.
 * The server records started_at using its own clock, avoiding any client drift.
 */
export async function startSession(): Promise<number | null> {
  try {
    const res = await apiFetch<{ sessionId: number }>('/api/ai/start-session', { method: 'POST' })
    return res.sessionId ?? null
  } catch {
    return null
  }
}

// ── Session logger ────────────────────────────────────────────────────────────

export async function logSession(data: {
  mode: string
  bookId?: string | null
  chapterId?: string | null
  wordsStudied: number
  correctCount: number
  wrongCount: number
  /** Used as fallback when sessionId is absent. */
  durationSeconds: number
  /** Epoch ms — fallback startedAt when sessionId is absent. */
  startedAt: number
  /** Server session ID from startSession(). When present the server computes duration. */
  sessionId?: number | null
}) {
  apiFetch('/api/ai/log-session', {
    method: 'POST',
    body: JSON.stringify({
      sessionId: data.sessionId,
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
      wordsStudied: data.wordsStudied,
      correctCount: data.correctCount,
      wrongCount: data.wrongCount,
      durationSeconds: data.durationSeconds,
      startedAt: data.startedAt,
    }),
  }).catch(() => { /* non-critical */ })
}

// ── Mode performance tracker (client-side localStorage) ──────────────────────

export function recordModeAnswer(mode: string, correct: boolean) {
  try {
    const parsed = safeParse(ModePerformanceSchema, JSON.parse(localStorage.getItem('mode_performance') || '{}'))
    const stored = parsed.success ? parsed.data : {}
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
  // with local quick-memory, mode-performance, and historical chapter progress.
  const buildContext = useCallback(() => {
    // Summarise locally-stored chapter progress so AI sees historical completion data
    const chapterProgressSummary = (() => {
      try {
        const ChapterProgressSchema = z.record(z.string(), z.object({
          current_index: z.number().optional(),
          correct_count: z.number().optional(),
          wrong_count: z.number().optional(),
          is_completed: z.boolean().optional(),
          words_learned: z.number().optional(),
          updatedAt: z.string().optional(),
        }).passthrough())
        const cParsed = safeParse(ChapterProgressSchema, JSON.parse(localStorage.getItem('chapter_progress') || '{}'))
        const raw = cParsed.success ? cParsed.data : {}
        type CP = typeof raw[string]
        const _raw = raw as Record<string, CP>
        const entries = Object.entries(_raw)
        if (!entries.length) return undefined
        const completed = entries.filter(([, p]) => p.is_completed).length
        const totalCorrect = entries.reduce((s, [, p]) => s + (p.correct_count ?? 0), 0)
        const totalWrong = entries.reduce((s, [, p]) => s + (p.wrong_count ?? 0), 0)
        const totalAnswered = totalCorrect + totalWrong
        return {
          chaptersAttempted: entries.length,
          chaptersCompleted: completed,
          totalCorrect,
          totalWrong,
          overallAccuracy: totalAnswered > 0 ? Math.round(totalCorrect / totalAnswered * 100) : 0,
        }
      } catch { return undefined }
    })()
    return {
      ...getGlobalLearningContext(),
      quickMemorySummary: buildQuickMemorySummary(),
      modePerformance: buildModePerformance(),
      localHistory: chapterProgressSummary,
    }
  }, [])

  const _syncWrongWords = useCallback(async () => {
    try {
      const wwParsed = safeParse(WrongWordsSchema, JSON.parse(localStorage.getItem(STORAGE_KEYS.WRONG_WORDS) || '[]'))
      const wrongWords = wwParsed.success ? wwParsed.data : []
      if (!wrongWords.length) return
      const ssParsed = safeParse(SmartWordStatsSchema, JSON.parse(localStorage.getItem(STORAGE_KEYS.SMART_WORD_STATS) || '{}'))
      const smartStats = ssParsed.success ? ssParsed.data : {}
      const enriched = wrongWords.map(w => {
        const ws = smartStats[w.word as string]
        return {
          ...w,
          listeningCorrect: ws?.listening.correct ?? 0,
          listeningWrong:   ws?.listening.wrong   ?? 0,
          meaningCorrect:   ws?.meaning.correct   ?? 0,
          meaningWrong:     ws?.meaning.wrong     ?? 0,
          dictationCorrect: ws?.dictation.correct ?? 0,
          dictationWrong:   ws?.dictation.wrong   ?? 0,
        }
      })
      await apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({ words: enriched }),
      })
    } catch {
      // Non-critical
    }
  }, [])

  const _fetchGreeting = useCallback(async () => {
    setIsGreeting(true)
    try {
      const raw = await apiFetch('/api/ai/greet', {
        method: 'POST',
        body: JSON.stringify({ context: buildContext() }),
      })
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
      const raw = await apiFetch('/api/ai/ask', {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          context: buildContext(),
        }),
      })
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
