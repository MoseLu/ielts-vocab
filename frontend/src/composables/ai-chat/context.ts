import { z } from 'zod'
import { getGlobalLearningContext } from '../../contexts/AIChatContext'
import { ChapterProgressMapSchema } from '../../lib/schemas'
import { readWrongWordsFromStorage } from '../../features/vocabulary/wrongWordsStore'
import { readQuickMemoryRecordsFromStorage } from '../../lib/quickMemory'
import { safeParse } from '../../lib'
import type { LearningContext } from '../../types'

const ModePerformanceSchema = z.record(
  z.string(),
  z.object({ correct: z.number(), wrong: z.number() }).passthrough(),
)
const WrongWordsSchema = z.array(z.record(z.string(), z.unknown()))
const RECENT_WRONG_WORD_LIMIT = 6
const RECENT_WRONG_WORD_WINDOW_MS = 3 * 24 * 60 * 60 * 1000

function parseWrongWordUpdatedAt(value: unknown): number {
  if (typeof value !== 'string' || !value.trim()) return 0
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? timestamp : 0
}

function buildRecentWrongWords() {
  try {
    const parsedWrongWords = safeParse(WrongWordsSchema, readWrongWordsFromStorage())
    const wrongWords = parsedWrongWords.success ? parsedWrongWords.data : []
    if (!wrongWords.length) return undefined

    const now = Date.now()
    const sorted = wrongWords
      .map((word, index) => ({
        index,
        word: String(word.word ?? '').trim(),
        updatedAt: parseWrongWordUpdatedAt(word.updated_at ?? word.updatedAt),
      }))
      .filter(item => item.word)
      .sort((left, right) => right.updatedAt - left.updatedAt || left.index - right.index)

    const recentOnly = sorted.filter(item => (
      item.updatedAt > 0 && now - item.updatedAt <= RECENT_WRONG_WORD_WINDOW_MS
    ))
    const selected = (recentOnly.length > 0 ? recentOnly : sorted).slice(0, RECENT_WRONG_WORD_LIMIT)
    return selected.map(item => item.word)
  } catch {
    return undefined
  }
}

function buildQuickMemorySummary() {
  try {
    const records = readQuickMemoryRecordsFromStorage()
    const now = Date.now()
    return Object.values(records).reduce(
      (acc, record) => {
        if (record.status === 'known') acc.known += 1
        else acc.unknown += 1
        if (record.nextReview && record.nextReview <= now) acc.dueToday += 1
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
    const parsed = safeParse(
      ModePerformanceSchema,
      JSON.parse(localStorage.getItem('mode_performance') || '{}'),
    )
    return parsed.success ? parsed.data : {}
  } catch {
    return {}
  }
}

export function buildAIChatContext(): LearningContext {
  const chapterProgressSummary = (() => {
    try {
      const parsed = safeParse(
        ChapterProgressMapSchema,
        JSON.parse(localStorage.getItem('chapter_progress') || '{}'),
      )
      const raw = parsed.success ? parsed.data : {}
      const entries = Object.entries(raw)
      if (!entries.length) return undefined

      const completed = entries.filter(([, progress]) => progress.is_completed).length
      const totalCorrect = entries.reduce((sum, [, progress]) => sum + (progress.correct_count ?? 0), 0)
      const totalWrong = entries.reduce((sum, [, progress]) => sum + (progress.wrong_count ?? 0), 0)
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
  })()

  const localBookProgress = (() => {
    try {
      const parsed = safeParse(
        ChapterProgressMapSchema,
        JSON.parse(localStorage.getItem('chapter_progress') || '{}'),
      )
      const raw = parsed.success ? parsed.data : {}
      const bookMap: Record<string, {
        chaptersCompleted: number
        chaptersAttempted: number
        correct: number
        wrong: number
        wordsLearned: number
      }> = {}

      for (const [key, data] of Object.entries(raw)) {
        const match = key.match(/^(.+)_(\d+)$/)
        if (!match) continue
        const bookId = match[1]
        if (!bookMap[bookId]) {
          bookMap[bookId] = {
            chaptersCompleted: 0,
            chaptersAttempted: 0,
            correct: 0,
            wrong: 0,
            wordsLearned: 0,
          }
        }

        bookMap[bookId].chaptersAttempted += 1
        if (data.is_completed) bookMap[bookId].chaptersCompleted += 1
        bookMap[bookId].correct += data.correct_count ?? 0
        bookMap[bookId].wrong += data.wrong_count ?? 0
        bookMap[bookId].wordsLearned += data.words_learned ?? 0
      }

      try {
        const BookProgressSchema = z.record(
          z.string(),
          z.object({
            correct_count: z.number().optional(),
            wrong_count: z.number().optional(),
            is_completed: z.boolean().optional(),
          }).passthrough(),
        )
        const parsedBookProgress = safeParse(
          BookProgressSchema,
          JSON.parse(localStorage.getItem('book_progress') || '{}'),
        )
        if (parsedBookProgress.success) {
          for (const [bookId, progress] of Object.entries(parsedBookProgress.data)) {
            if (!bookMap[bookId]) {
              bookMap[bookId] = {
                chaptersCompleted: 0,
                chaptersAttempted: 0,
                correct: 0,
                wrong: 0,
                wordsLearned: 0,
              }
            }
            if (bookMap[bookId].chaptersAttempted === 0) {
              bookMap[bookId].correct = progress.correct_count ?? 0
              bookMap[bookId].wrong = progress.wrong_count ?? 0
            }
          }
        }
      } catch {
        // Ignore book-progress fallback failures.
      }

      return Object.keys(bookMap).length > 0 ? bookMap : null
    } catch {
      return null
    }
  })()

  return {
    ...getGlobalLearningContext(),
    recentWrongWords: buildRecentWrongWords(),
    quickMemorySummary: buildQuickMemorySummary(),
    modePerformance: buildModePerformance(),
    localHistory: chapterProgressSummary,
    localBookProgress,
  }
}
