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
import { ChapterProgressMapSchema } from '../lib/schemas'
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

function buildChapterProgressSummary() {
  try {
    const cParsed = safeParse(ChapterProgressMapSchema, JSON.parse(localStorage.getItem('chapter_progress') || '{}'))
    const raw = cParsed.success ? cParsed.data : {}
    const entries = Object.entries(raw)
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
  } catch {
    return undefined
  }
}

// ── Session timer ─────────────────────────────────────────────────────────────

/**
 * Notify the server that a practice session has started.
 * Returns the server-assigned sessionId, or null on failure.
 * The server records started_at using its own clock, avoiding any client drift.
 */
/** 创建服务端会话行；请传入当前练习模式与词书上下文，避免仅 start-session 产生 mode 为空的记录 */
export async function startSession(ctx?: {
  mode?: string
  bookId?: string | null
  chapterId?: string | null
}): Promise<number | null> {
  try {
    const res = await apiFetch<{ sessionId: number }>('/api/ai/start-session', {
      method: 'POST',
      body: JSON.stringify({
        mode: ctx?.mode ?? 'smart',
        bookId: ctx?.bookId ?? undefined,
        chapterId: ctx?.chapterId != null && ctx.chapterId !== '' ? String(ctx.chapterId) : undefined,
      }),
    })
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
      mode: data.mode ?? 'smart',
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
    // Parse chapter_progress (keyed as `{bookId}_{chapterId}` where chapterId is numeric)
    // and aggregate both per-book AND overall summaries for the AI.
    const chapterProgressSummary = (() => {
      try {
        const cParsed = safeParse(ChapterProgressMapSchema, JSON.parse(localStorage.getItem('chapter_progress') || '{}'))
        const raw = cParsed.success ? cParsed.data : {}
        const entries = Object.entries(raw)
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

    // Per-book breakdown: group chapter_progress entries by bookId.
    // Key format: {bookId}_{chapterId} where chapterId is always an integer suffix.
    const localBookProgress = (() => {
      try {
        const cParsed = safeParse(ChapterProgressSchema, JSON.parse(localStorage.getItem('chapter_progress') || '{}'))
        const raw = cParsed.success ? cParsed.data : {}
        const bookMap: Record<string, { chaptersCompleted: number; chaptersAttempted: number; correct: number; wrong: number; wordsLearned: number }> = {}

        for (const [key, data] of Object.entries(raw)) {
          // Split off trailing numeric chapterId: "ielts_listening_premium_3" → bookId="ielts_listening_premium"
          const match = key.match(/^(.+)_(\d+)$/)
          if (!match) continue
          const bookId = match[1]
          if (!bookMap[bookId]) bookMap[bookId] = { chaptersCompleted: 0, chaptersAttempted: 0, correct: 0, wrong: 0, wordsLearned: 0 }
          bookMap[bookId].chaptersAttempted++
          if (data.is_completed) bookMap[bookId].chaptersCompleted++
          bookMap[bookId].correct += data.correct_count ?? 0
          bookMap[bookId].wrong += data.wrong_count ?? 0
          bookMap[bookId].wordsLearned += data.words_learned ?? 0
        }

        // Merge in book-level progress (correct/wrong totals at book scope)
        try {
          const BookProgressSchema = z.record(z.string(), z.object({
            correct_count: z.number().optional(),
            wrong_count: z.number().optional(),
            is_completed: z.boolean().optional(),
          }).passthrough())
          const bParsed = safeParse(BookProgressSchema, JSON.parse(localStorage.getItem('book_progress') || '{}'))
          if (bParsed.success) {
            for (const [bookId, bp] of Object.entries(bParsed.data)) {
              if (!bookMap[bookId]) bookMap[bookId] = { chaptersCompleted: 0, chaptersAttempted: 0, correct: 0, wrong: 0, wordsLearned: 0 }
              // Only use book-level stats if chapter-level stats are absent
              if (bookMap[bookId].chaptersAttempted === 0) {
                bookMap[bookId].correct = bp.correct_count ?? 0
                bookMap[bookId].wrong = bp.wrong_count ?? 0
              }
            }
          }
        } catch { /* ignore */ }

        return Object.keys(bookMap).length > 0 ? bookMap : null
      } catch { return null }
    })()

    return {
      ...getGlobalLearningContext(),
      quickMemorySummary: buildQuickMemorySummary(),
      modePerformance: buildModePerformance(),
      localHistory: chapterProgressSummary,
      localBookProgress,
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
      const normalized = text.trim()
      if (normalized.startsWith('/correct ')) {
        const sentence = normalized.replace('/correct ', '').trim()
        const result = await apiFetch<Record<string, unknown>>('/api/ai/correct-text', {
          method: 'POST',
          body: JSON.stringify({ text: sentence }),
        })
        const upgrades = Array.isArray(result.upgrades) ? result.upgrades as Array<Record<string, string>> : []
        const collocations = Array.isArray(result.collocations) ? result.collocations as Array<Record<string, string>> : []
        const lines = [
          '写作纠错结果：',
          `- 语法：${result.grammar_ok ? '基本正确' : '建议优化'}`,
          `- 修正句：${String(result.corrected_sentence || sentence)}`,
        ]
        if (upgrades.length) {
          lines.push('- 词汇升级：')
          upgrades.slice(0, 3).forEach((u) => lines.push(`  ${u.from} -> ${u.to}（${u.reason || '提升学术表达'}）`))
        }
        if (collocations.length) {
          lines.push('- 搭配建议：')
          collocations.slice(0, 3).forEach((c) => lines.push(`  ${c.wrong} -> ${c.right}`))
        }
        lines.push(String(result.encouragement || '继续保持，建议多练 Task 2 学术表达。'))
        setMessages(prev => [...prev, {
          id: `asst_${Date.now()}`,
          role: 'assistant',
          content: lines.join('\n'),
          timestamp: Date.now(),
        }])
        return
      }
      if (normalized.startsWith('/example ')) {
        const word = normalized.replace('/example ', '').trim()
        const result = await apiFetch<{ examples: Array<{ sentence: string; source?: string }> }>(`/api/ai/ielts-example?word=${encodeURIComponent(word)}`)
        const lines = ['真题语境例句：', ...result.examples.slice(0, 3).map((e, i) => `${i + 1}. ${e.sentence} (${e.source || 'unknown'})`)]
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: lines.join('\n'), timestamp: Date.now() }])
        return
      }
      if (normalized.startsWith('/synonyms ')) {
        const pair = normalized.replace('/synonyms ', '').split(/\s+vs\s+|\s+/i)
        const [a, b] = pair
        const result = await apiFetch<{ summary: string; quiz?: { question?: string } }>('/api/ai/synonyms-diff', {
          method: 'POST',
          body: JSON.stringify({ a, b }),
        })
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: `${result.summary}\n${result.quiz?.question || ''}`.trim(), timestamp: Date.now() }])
        return
      }
      if (normalized.startsWith('/family ')) {
        const word = normalized.replace('/family ', '').trim()
        const result = await apiFetch<Record<string, unknown>>(`/api/ai/word-family?word=${encodeURIComponent(word)}`)
        const variants = (result.variants as Array<Record<string, string>> | undefined) || []
        const textOut = variants.length
          ? `词族树 ${word}：\n${variants.map(v => `- ${v.word} (${v.pos})`).join('\n')}`
          : String(result.message || '暂无词族数据')
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: textOut, timestamp: Date.now() }])
        return
      }
      if (normalized.startsWith('/collocation')) {
        const result = await apiFetch<{ items: Array<{ wrong: string; right: string; explanation: string }> }>('/api/ai/collocations/practice?count=5')
        const textOut = `搭配训练：\n${result.items.map(i => `- ${i.wrong} -> ${i.right}（${i.explanation}）`).join('\n')}`
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: textOut, timestamp: Date.now() }])
        return
      }
      if (normalized.startsWith('/plan')) {
        const result = await apiFetch<{ level: string; plan: string[] }>('/api/ai/review-plan')
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: `今日自适应计划（${result.level}）：\n- ${result.plan.join('\n- ')}`, timestamp: Date.now() }])
        return
      }
      if (normalized.startsWith('/assessment')) {
        const result = await apiFetch<{ questions: Array<{ word: string; definition: string }> }>('/api/ai/vocab-assessment?count=10')
        const preview = result.questions.slice(0, 5).map((q, idx) => `${idx + 1}. ${q.word}: ${q.definition}`).join('\n')
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: `词汇量评估（预览）：\n${preview}`, timestamp: Date.now() }])
        return
      }
      if (normalized.startsWith('/speaking')) {
        const result = await apiFetch<{ question: string; follow_ups: string[] }>('/api/ai/speaking-simulate', {
          method: 'POST',
          body: JSON.stringify({ part: 1, topic: 'education' }),
        })
        setMessages(prev => [...prev, { id: `asst_${Date.now()}`, role: 'assistant', content: `${result.question}\n- ${result.follow_ups.join('\n- ')}`, timestamp: Date.now() }])
        return
      }

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
