import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'

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
  duration_seconds: number
  today_accuracy: number | null
  today_duration_seconds: number
  /** 速记：今日首次进入艾宾浩斯队列的词数 */
  today_new_words: number
  /** 速记：今日在非首日再次学习的词数 */
  today_review_words: number
  /** 速记：累计至少作答过 2 轮的词数 */
  alltime_review_words: number
  /** 速记：累计复习人次（含模糊回溯） */
  cumulative_review_events: number
  /** 已到复习点且已按时回顾的比例 %（对抗艾宾浩斯遗忘曲线的完成度，取决于是否按时复习） */
  ebbinghaus_rate: number | null
  ebbinghaus_due_total: number
  ebbinghaus_met: number
  qm_word_total: number
  /** 按复习轮次（对应 1/1/4/7/14/30 天间隔）的到期/达成统计 */
  ebbinghaus_stages?: EbbinghausStagePoint[]
}

export interface EbbinghausStagePoint {
  stage: number
  interval_days: number
  due_total: number
  due_met: number
  actual_pct: number | null
}

export interface ModeStat {
  mode: string
  words_studied: number
  correct_count: number
  wrong_count: number
  duration_seconds: number
  sessions: number
  accuracy: number | null
  attempts?: number
  avg_words_per_session?: number
}

export interface PieSegment {
  mode: string
  value: number
  sessions: number
}

export interface WrongTopItem {
  word: string
  wrong_count: number
  phonetic: string
  pos: string
}

export interface ChapterBreakdownRow {
  book_id: string
  book_title: string
  chapter_id: number
  chapter_title: string
  words_learned: number
  correct: number
  wrong: number
  accuracy: number | null
}

export interface ChapterModeStatRow {
  book_id: string
  book_title: string
  chapter_id: number
  chapter_title: string
  mode: string
  correct: number
  wrong: number
  accuracy: number
}

export type MetricKey = 'words' | 'accuracy' | 'duration'
export type RangeKey = 7 | 14 | 30

export function useLearningStats(days: RangeKey, bookId: string, mode: string) {
  const { user } = useAuth()
  const [daily, setDaily] = useState<DailyLearning[]>([])
  const [books, setBooks] = useState<LearningBook[]>([])
  const [modes, setModes] = useState<string[]>([])
  const [summary, setSummary] = useState<LearningSummary | null>(null)
  const [alltime, setAlltime] = useState<LearningAlltime | null>(null)
  const [modeBreakdown, setModeBreakdown] = useState<ModeStat[]>([])
  const [pieChart, setPieChart] = useState<PieSegment[]>([])
  const [wrongTop10, setWrongTop10] = useState<WrongTopItem[]>([])
  const [chapterBreakdown, setChapterBreakdown] = useState<ChapterBreakdownRow[]>([])
  const [chapterModeStats, setChapterModeStats] = useState<ChapterModeStatRow[]>([])
  const [useFallback, setUseFallback] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    if (!user) {
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const params = new URLSearchParams({ days: String(days) })
      if (bookId && bookId !== 'all') params.set('book_id', bookId)
      if (mode && mode !== 'all') params.set('mode', mode)

      const d = await apiFetch<{
        daily?: DailyLearning[]
        books?: LearningBook[]
        modes?: string[]
        summary?: LearningSummary | null
        alltime?: LearningAlltime | null
        mode_breakdown?: ModeStat[]
        pie_chart?: PieSegment[]
        wrong_top10?: WrongTopItem[]
        chapter_breakdown?: ChapterBreakdownRow[]
        chapter_mode_stats?: ChapterModeStatRow[]
        use_fallback?: boolean
      }>(`/api/ai/learning-stats?${params}`)
      setDaily(d.daily || [])
      setBooks(d.books || [])
      setModes(d.modes || [])
      setSummary(d.summary || null)
      setAlltime(d.alltime || null)
      setModeBreakdown(d.mode_breakdown || [])
      setPieChart(d.pie_chart || [])
      setWrongTop10(d.wrong_top10 || [])
      setChapterBreakdown(d.chapter_breakdown || [])
      setChapterModeStats(d.chapter_mode_stats || [])
      setUseFallback(d.use_fallback || false)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [days, bookId, mode, user])

  useEffect(() => { fetchStats() }, [fetchStats])

  return {
    daily,
    books,
    modes,
    summary,
    alltime,
    modeBreakdown,
    pieChart,
    wrongTop10,
    chapterBreakdown,
    chapterModeStats,
    useFallback,
    loading,
    refetch: fetchStats,
  }
}
