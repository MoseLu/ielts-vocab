import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLearningStats, type MetricKey, type RangeKey } from '../../../features/vocabulary/hooks'
import {
  ebbinghausRateCaption,
  ebbinghausSummaryHelp,
  fmtDuration,
  fmtPct,
  isKnownStatsMode,
  isStatsInitialLoading,
  resolveEbbStages,
  sortStatsModeFilters,
  sortStatsModes,
} from '../../../components/stats/StatsPageSupport'

const STATS_REFRESH_OPTIONS = {
  pollIntervalMs: 0,
  blockInitialQuickMemoryReconcile: false,
  blockOnLearnerProfile: false,
} as const

export function useStatsPage() {
  const navigate = useNavigate()

  const [range, setRange] = useState<RangeKey>(30)
  const [metric, setMetric] = useState<MetricKey>('words')
  const [bookId, setBookId] = useState('all')
  const [mode, setMode] = useState('all')

  const {
    daily,
    books,
    modes,
    summary,
    alltime,
    modeBreakdown,
    pieChart,
    historyWrongTop10,
    pendingWrongTop10,
    learnerProfile,
    useFallback,
    loading: chartLoading,
    learnerProfileLoading,
  } = useLearningStats(range, bookId, mode, STATS_REFRESH_OPTIONS)

  const displayTodayNewWords = alltime?.today_new_words ?? (chartLoading ? '…' : '--')
  const displayTodayReviewWords = alltime?.today_review_words ?? (chartLoading ? '…' : '--')
  const displayTodayWords = alltime
    ? alltime.today_new_words + alltime.today_review_words
    : (chartLoading ? '…' : '--')
  const displayTodayDuration = alltime && alltime.today_duration_seconds > 0
    ? fmtDuration(alltime.today_duration_seconds)
    : '--'
  const displayTodayAccuracy = fmtPct(alltime?.today_accuracy ?? learnerProfile?.summary.today_accuracy ?? null)
  const displayTotalLearnedNewWords = alltime?.total_words != null ? alltime.total_words : (chartLoading ? '…' : '--')
  const displayTotalReviewedWords = alltime?.alltime_review_words ?? (chartLoading ? '…' : '--')
  const displayTotalStudyDuration = alltime && alltime.duration_seconds > 0
    ? fmtDuration(alltime.duration_seconds)
    : '--'
  const displayStreak = learnerProfile?.summary.streak_days ?? alltime?.streak_days ?? '--'
  const ebbRateCaption = ebbinghausRateCaption(alltime)
  const ebbSummaryHelp = ebbinghausSummaryHelp(alltime)
  const visibleModes = useMemo(() => modes.filter(item => item !== 'game'), [modes])
  const visibleModeBreakdown = useMemo(() => modeBreakdown.filter(item => item.mode !== 'game'), [modeBreakdown])
  const visiblePieChart = useMemo(() => pieChart.filter(item => item.mode !== 'game'), [pieChart])
  const normalizedModes = useMemo(() => sortStatsModeFilters(visibleModes), [visibleModes])
  const normalizedModeBreakdown = useMemo(() => sortStatsModes(visibleModeBreakdown), [visibleModeBreakdown])
  const normalizedPieChart = useMemo(() => sortStatsModes(visiblePieChart), [visiblePieChart])
  const weakestModeLabel = useMemo(() => {
    const weakestMode = alltime?.weakest_mode
    return weakestMode && weakestMode !== 'game' && isKnownStatsMode(weakestMode) ? weakestMode : null
  }, [alltime?.weakest_mode])

  const hasChartData = useMemo(() => {
    return daily.some(item => {
      if (metric === 'words') return item.words_studied > 0
      if (metric === 'accuracy') return item.accuracy != null
      return item.duration_seconds > 0
    })
  }, [daily, metric])

  const ebbStages = useMemo(() => resolveEbbStages(alltime), [alltime])
  const isInitialLoading = isStatsInitialLoading({
    chartLoading,
    summary,
    alltime,
    dailyLength: daily.length,
    booksLength: books.length,
    modesLength: normalizedModes.length,
    modeBreakdownLength: normalizedModeBreakdown.length,
    pieChartLength: normalizedPieChart.length,
    historyWrongTopLength: historyWrongTop10.length,
    pendingWrongTopLength: pendingWrongTop10.length,
    hasLearnerProfile: Boolean(learnerProfile),
  })

  const goToPlan = useCallback(() => {
    navigate('/plan')
  }, [navigate])

  const startEbbinghausReview = useCallback(() => {
    navigate('/practice?review=due')
  }, [navigate])

  return {
    range,
    metric,
    bookId,
    mode,
    daily,
    books,
    modes: normalizedModes,
    summary,
    alltime,
    modeBreakdown: normalizedModeBreakdown,
    pieChart: normalizedPieChart,
    learnerProfile,
    useFallback,
    chartLoading,
    learnerProfileLoading,
    historyWrongTop10,
    pendingWrongTop10,
    displayTodayNewWords,
    displayTodayReviewWords,
    displayTodayWords,
    displayTodayDuration,
    displayTodayAccuracy,
    displayTotalLearnedNewWords,
    displayTotalReviewedWords,
    displayTotalStudyDuration,
    displayStreak,
    ebbRateCaption,
    ebbSummaryHelp,
    weakestModeLabel,
    hasChartData,
    ebbStages,
    isInitialLoading,
    setRange,
    setMetric,
    setBookId,
    setMode,
    goToPlan,
    startEbbinghausReview,
  }
}
