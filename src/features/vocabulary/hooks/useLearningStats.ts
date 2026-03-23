import { useState, useEffect, useCallback } from 'react'

export interface DailyLearning {
  date: string           // 'YYYY-MM-DD'
  words_studied: number
  correct_count: number
  wrong_count: number
  duration_seconds: number
  sessions: number
  accuracy: number | null  // null when no attempts that day
}

export interface LearningBook {
  id: string
  title: string
}

export interface LearningSummary {
  total_words: number
  total_duration_seconds: number
  total_sessions: number
  accuracy: number | null
}

export interface LearningAlltime {
  total_words: number
  accuracy: number | null
}

export type MetricKey = 'words' | 'accuracy' | 'duration'
export type RangeKey = 7 | 14 | 30

export function useLearningStats(days: RangeKey, bookId: string, mode: string) {
  const [daily, setDaily] = useState<DailyLearning[]>([])
  const [books, setBooks] = useState<LearningBook[]>([])
  const [modes, setModes] = useState<string[]>([])
  const [summary, setSummary] = useState<LearningSummary | null>(null)
  const [alltime, setAlltime] = useState<LearningAlltime | null>(null)
  const [useFallback, setUseFallback] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) { setLoading(false); return }

    setLoading(true)
    try {
      const params = new URLSearchParams({ days: String(days) })
      if (bookId && bookId !== 'all') params.set('book_id', bookId)
      if (mode && mode !== 'all') params.set('mode', mode)

      const res = await fetch(`/api/ai/learning-stats?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const d = await res.json()
        setDaily(d.daily || [])
        setBooks(d.books || [])
        setModes(d.modes || [])
        setSummary(d.summary || null)
        setAlltime(d.alltime || null)
        setUseFallback(d.use_fallback || false)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [days, bookId, mode])

  useEffect(() => { fetchStats() }, [fetchStats])

  return { daily, books, modes, summary, alltime, useFallback, loading, refetch: fetchStats }
}
