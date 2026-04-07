import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'
import { reconcileQuickMemoryRecordsWithBackend } from '../../../lib/quickMemorySync'

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
  /** 3天内待复习词数（含已到期未复习的） */
  upcoming_reviews_3d?: number
  /** 连续学习天数 */
  streak_days?: number
  /** 最弱模式（正确率最低的模式） */
  weakest_mode?: string | null
  /** 最弱模式正确率 */
  weakest_mode_accuracy?: number | null
  /** 趋势方向 */
  trend_direction?: 'improving' | 'stable' | 'declining'
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
  recognition_wrong?: number
  listening_wrong?: number
  meaning_wrong?: number
  dictation_wrong?: number
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

export interface LearnerProfileSummary {
  date: string
  today_words: number
  today_accuracy: number
  today_duration_seconds: number
  today_sessions: number
  streak_days: number
  weakest_mode: string | null
  weakest_mode_label: string | null
  weakest_mode_accuracy: number | null
  due_reviews: number
  trend_direction: 'improving' | 'stable' | 'declining' | 'new'
}

export interface LearnerProfileDimension {
  dimension: string
  label: string
  correct: number
  wrong: number
  attempts: number
  accuracy: number | null
  weakness: number
}

export interface LearnerProfileFocusWord {
  word: string
  definition: string
  wrong_count: number
  dominant_dimension: string
  dominant_dimension_label: string
  dominant_wrong: number
  focus_score: number
}

export interface LearnerProfileTopic {
  title: string
  count: number
  word_context: string
  latest_answer: string
  latest_at: string | null
}

export interface LearnerProfileDailyPlanAction {
  kind: 'add-book' | 'due-review' | 'error-review' | 'continue-book'
  cta_label: string
  mode?: string | null
  book_id?: string | null
  dimension?: string | null
}

export interface LearnerProfileDailyPlanTask {
  id: string
  kind: 'add-book' | 'due-review' | 'error-review' | 'continue-book'
  title: string
  description: string
  status: 'pending' | 'completed'
  completion_source?: 'completed_today' | 'already_clear' | null
  badge: string
  action: LearnerProfileDailyPlanAction
}

export interface LearnerProfileDailyPlanTodayContent {
  date: string
  studied_words: number
  duration_seconds: number
  sessions: number
  latest_activity_title: string | null
  latest_activity_at: string | null
}

export interface LearnerProfileDailyPlanFocusBook {
  book_id: string
  title: string
  current_index: number
  total_words: number
  progress_percent: number
  remaining_words: number
  is_completed: boolean
}

export interface LearnerProfileDailyPlan {
  tasks: LearnerProfileDailyPlanTask[]
  today_content: LearnerProfileDailyPlanTodayContent
  focus_book: LearnerProfileDailyPlanFocusBook | null
}

export interface LearnerProfile {
  date: string
  summary: LearnerProfileSummary
  dimensions: LearnerProfileDimension[]
  focus_words: LearnerProfileFocusWord[]
  daily_plan?: LearnerProfileDailyPlan
  repeated_topics: LearnerProfileTopic[]
  next_actions: string[]
  mode_breakdown: ModeStat[]
}

export type MetricKey = 'words' | 'accuracy' | 'duration'
export type RangeKey = 7 | 14 | 30

export interface UseLearningStatsOptions {
  pollIntervalMs?: number
}

export function useLearningStats(
  days: RangeKey,
  bookId: string,
  mode: string,
  options: UseLearningStatsOptions = {},
) {
  const { user } = useAuth()
  const userId = user?.id ?? null
  const { pollIntervalMs = 60_000 } = options
  const lastFetchStartedAtRef = useRef(0)
  const hasResolvedInitialFetchRef = useRef(false)
  const lastUserIdRef = useRef(userId)
  const [daily, setDaily] = useState<DailyLearning[]>([])
  const [books, setBooks] = useState<LearningBook[]>([])
  const [modes, setModes] = useState<string[]>([])
  const [summary, setSummary] = useState<LearningSummary | null>(null)
  const [alltime, setAlltime] = useState<LearningAlltime | null>(null)
  const [modeBreakdown, setModeBreakdown] = useState<ModeStat[]>([])
  const [pieChart, setPieChart] = useState<PieSegment[]>([])
  const [wrongTop10, setWrongTop10] = useState<WrongTopItem[]>([])
  const [historyWrongTop10, setHistoryWrongTop10] = useState<WrongTopItem[]>([])
  const [pendingWrongTop10, setPendingWrongTop10] = useState<WrongTopItem[]>([])
  const [chapterBreakdown, setChapterBreakdown] = useState<ChapterBreakdownRow[]>([])
  const [chapterModeStats, setChapterModeStats] = useState<ChapterModeStatRow[]>([])
  const [learnerProfile, setLearnerProfile] = useState<LearnerProfile | null>(null)
  const [useFallback, setUseFallback] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (lastUserIdRef.current === userId) return

    lastUserIdRef.current = userId
    hasResolvedInitialFetchRef.current = false
    setLoading(Boolean(userId))
    setRefreshing(false)
  }, [userId])

  const fetchStats = useCallback(async () => {
    if (!userId) {
      hasResolvedInitialFetchRef.current = false
      setLoading(false)
      setRefreshing(false)
      return
    }

    const isInitialFetch = !hasResolvedInitialFetchRef.current
    lastFetchStartedAtRef.current = Date.now()
    if (isInitialFetch) {
      setLoading(true)
    } else {
      setRefreshing(true)
    }
    try {
      await reconcileQuickMemoryRecordsWithBackend({
        skipIfLocalEmpty: true,
        minIntervalMs: 15_000,
      }).catch(() => {})

      const params = new URLSearchParams({ days: String(days) })
      if (bookId && bookId !== 'all') params.set('book_id', bookId)
      if (mode && mode !== 'all') params.set('mode', mode)

      const [d, profile] = await Promise.all([
        apiFetch<{
          daily?: DailyLearning[]
          books?: LearningBook[]
          modes?: string[]
          summary?: LearningSummary | null
          alltime?: LearningAlltime | null
          mode_breakdown?: ModeStat[]
          pie_chart?: PieSegment[]
          wrong_top10?: WrongTopItem[]
          history_wrong_top10?: WrongTopItem[]
          pending_wrong_top10?: WrongTopItem[]
          chapter_breakdown?: ChapterBreakdownRow[]
          chapter_mode_stats?: ChapterModeStatRow[]
          use_fallback?: boolean
        }>(`/api/ai/learning-stats?${params}`, { cache: 'no-store' }),
        apiFetch<LearnerProfile>('/api/ai/learner-profile?view=stats', { cache: 'no-store' }).catch(() => null),
      ])
      setDaily(d.daily || [])
      setBooks(d.books || [])
      setModes(d.modes || [])
      setSummary(d.summary || null)
      setAlltime(d.alltime || null)
      setModeBreakdown(d.mode_breakdown || [])
      setPieChart(d.pie_chart || [])
      const nextHistoryWrongTop10 = d.history_wrong_top10 || d.wrong_top10 || []
      setWrongTop10(nextHistoryWrongTop10)
      setHistoryWrongTop10(nextHistoryWrongTop10)
      setPendingWrongTop10(d.pending_wrong_top10 || [])
      setChapterBreakdown(d.chapter_breakdown || [])
      setChapterModeStats(d.chapter_mode_stats || [])
      setLearnerProfile(profile || null)
      setUseFallback(d.use_fallback || false)
    } catch {
      // ignore
    } finally {
      hasResolvedInitialFetchRef.current = true
      setLoading(false)
      setRefreshing(false)
    }
  }, [days, bookId, mode, userId])

  const refetchIfStale = useCallback(() => {
    if (Date.now() - lastFetchStartedAtRef.current < 1500) return
    void fetchStats()
  }, [fetchStats])

  useEffect(() => { fetchStats() }, [fetchStats])

  useEffect(() => {
    if (!userId) return

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refetchIfStale()
      }
    }

    window.addEventListener('focus', refetchIfStale)
    window.addEventListener('pageshow', refetchIfStale)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('focus', refetchIfStale)
      window.removeEventListener('pageshow', refetchIfStale)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [refetchIfStale, userId])

  useEffect(() => {
    if (!userId) return
    if (pollIntervalMs <= 0) return

    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== 'visible') return
      refetchIfStale()
    }, pollIntervalMs)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [pollIntervalMs, refetchIfStale, userId])

  return {
    daily,
    books,
    modes,
    summary,
    alltime,
    modeBreakdown,
    pieChart,
    wrongTop10,
    historyWrongTop10,
    pendingWrongTop10,
    chapterBreakdown,
    chapterModeStats,
    learnerProfile,
    useFallback,
    loading,
    refreshing,
    refetch: fetchStats,
  }
}
