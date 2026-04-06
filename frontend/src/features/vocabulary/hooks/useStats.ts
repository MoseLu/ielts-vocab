import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'
import { useVocabBooks } from './useVocabBooks'

export interface ChapterStat {
  bookId: string
  title: string
  correct: number
  wrong: number
  total: number
  accuracy: number | null
}

export interface DayStat {
  day: number
  learned: number
}

export function useStats() {
  const { user } = useAuth()
  const { books } = useVocabBooks()
  const [progressData, setProgressData] = useState<{ day: number; correct_count: number }[]>([])
  const [bookProgress, setBookProgress] = useState<Record<string, {
    correct_count: number; wrong_count: number; current_index: number
  }>>({})
  const [loading, setLoading] = useState(true)

  const fetchAll = useCallback(async () => {
    if (!user) {
      setLoading(false)
      return
    }

    try {
      const [d1, d2] = await Promise.all([
        apiFetch<{ progress?: { day: number; correct_count: number }[] }>('/api/progress'),
        apiFetch<{ progress?: Record<string, { correct_count: number; wrong_count: number; current_index: number }> }>(
          '/api/books/progress',
        ),
      ])
      setProgressData(d1.progress || [])
      setBookProgress(d2.progress || {})
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { fetchAll() }, [fetchAll])

  // Today's words = today's day number's correct_count from progressData
  // (day N corresponds to "today" in the 30-day plan)
  const today = new Date()
  const dayOfYear = Math.floor((today.getTime() - new Date(today.getFullYear(), 0, 0).getTime()) / 86400000)
  const todayDayNum = dayOfYear % 30 + 1
  const todayWords = progressData.find(p => p.day === todayDayNum)?.correct_count ?? 0

  const totalWords = progressData.reduce((sum, p) => sum + (p.correct_count || 0), 0)

  // 30-day chart data
  const chartData: DayStat[] = Array.from({ length: 30 }, (_, i) => {
    const dayNum = i + 1
    const found = progressData.find(p => p.day === dayNum)
    return { day: dayNum, learned: found?.correct_count ?? 0 }
  })

  const maxLearned = Math.max(...chartData.map(d => d.learned), 10)

  // Book title map
  const bookTitleMap: Record<string, string> = {}
  for (const b of books) {
    bookTitleMap[b.id] = b.title
  }

  // Chapter stats from book progress
  const chapterStats: ChapterStat[] = Object.entries(bookProgress)
    .map(([bookId, data]) => ({
      bookId,
      title: bookTitleMap[bookId] || bookId,
      correct: data.correct_count || 0,
      wrong: data.wrong_count || 0,
      total: data.current_index || 0,
      accuracy: data.correct_count != null && data.wrong_count != null
        ? Math.round((data.correct_count / (data.correct_count + data.wrong_count)) * 100)
        : null,
    }))
    .filter(s => s.correct + s.wrong > 0)

  return { progressData, bookProgress, todayWords, totalWords, chartData, maxLearned, chapterStats, loading }
}
