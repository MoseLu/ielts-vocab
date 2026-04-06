import type {
  DailyLearning,
  EbbinghausStagePoint,
  LearnerProfile,
  LearningAlltime,
  MetricKey,
  RangeKey,
} from '../../features/vocabulary/hooks'
import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  getWrongWordActiveCount,
  getWrongWordDimensionHistoryWrong,
  isWrongWordPendingInDimension,
} from '../../features/vocabulary/wrongWordsStore'

export const STATS_MODE_ORDER = [
  'smart',
  'quickmemory',
  'listening',
  'meaning',
  'dictation',
  'radio',
  'errors',
] as const

const STATS_MODE_RANK: Record<string, number> = STATS_MODE_ORDER.reduce<Record<string, number>>((acc, mode, index) => {
  acc[mode] = index
  return acc
}, {})

export const MODE_LABELS: Record<string, string> = {
  smart: '智能模式',
  quickmemory: '速记模式',
  listening: '听音选义',
  meaning: '释义拼词',
  dictation: '听写模式',
  radio: '随身听',
  errors: '错词强化',
}

export function isKnownStatsMode(mode: string): boolean {
  return mode in STATS_MODE_RANK
}

export function sortStatsModes<T extends { mode: string }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftRank = STATS_MODE_RANK[left.mode] ?? Number.MAX_SAFE_INTEGER
    const rightRank = STATS_MODE_RANK[right.mode] ?? Number.MAX_SAFE_INTEGER
    if (leftRank !== rightRank) return leftRank - rightRank
    return left.mode.localeCompare(right.mode)
  })
}

export function sortStatsModeFilters(modes: string[]): string[] {
  return [...modes]
    .filter(isKnownStatsMode)
    .sort((left, right) => (STATS_MODE_RANK[left] ?? Number.MAX_SAFE_INTEGER) - (STATS_MODE_RANK[right] ?? Number.MAX_SAFE_INTEGER))
}

export interface WrongTopDisplayItem {
  word: string
  wrong_count: number
  phonetic: string
  pos: string
  recognition_wrong?: number
  listening_wrong?: number
  meaning_wrong?: number
  dictation_wrong?: number
}

export interface ChartProps {
  data: DailyLearning[]
  metric: MetricKey
  range: RangeKey
  compact?: boolean
}

export function getScopedDimensionCount(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
  scope: WrongWordCollectionScope,
): number {
  if (scope === 'history') {
    return getWrongWordDimensionHistoryWrong(word, dimension)
  }

  return isWrongWordPendingInDimension(word, dimension)
    ? getWrongWordDimensionHistoryWrong(word, dimension)
    : 0
}

export function inferErrorReason(
  word: Partial<WrongWordRecord>,
  scope: WrongWordCollectionScope,
): string {
  const total = WRONG_WORD_DIMENSIONS.reduce(
    (sum, dimension) => sum + getScopedDimensionCount(word, dimension, scope),
    0,
  )
  if (total === 0) return '—'

  const [topDimension] = [...WRONG_WORD_DIMENSIONS].sort((left, right) => {
    return getScopedDimensionCount(word, right, scope) - getScopedDimensionCount(word, left, scope)
  })

  return WRONG_WORD_DIMENSION_LABELS[topDimension] || '—'
}

export function buildWrongTopItems(
  words: WrongWordRecord[],
  scope: WrongWordCollectionScope,
): WrongTopDisplayItem[] {
  return words
    .filter(word => getWrongWordActiveCount(word, scope) > 0)
    .map(word => ({
      word: word.word,
      wrong_count: getWrongWordActiveCount(word, scope),
      phonetic: word.phonetic,
      pos: word.pos,
      recognition_wrong: getScopedDimensionCount(word, 'recognition', scope),
      meaning_wrong: getScopedDimensionCount(word, 'meaning', scope),
      listening_wrong: getScopedDimensionCount(word, 'listening', scope),
      dictation_wrong: getScopedDimensionCount(word, 'dictation', scope),
    }))
    .sort((a, b) => b.wrong_count - a.wrong_count || a.word.localeCompare(b.word))
    .slice(0, 10)
}

export function fmtDuration(secs: number): string {
  if (!secs) return '0分钟'
  const minutes = Math.floor(secs / 60)
  if (minutes < 60) return `${minutes}分钟`
  return `${Math.floor(minutes / 60)}小时${minutes % 60 ? `${minutes % 60}分钟` : ''}`
}

export function fmtDate(dateStr: string, range: RangeKey): string {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

export function fmtPct(value: number | null | undefined): string {
  if (value == null) return '--'
  return `${value}%`
}

export function trendDirectionLabel(value: LearnerProfile['summary']['trend_direction'] | undefined): string {
  if (value === 'improving') return '学习趋势在提升'
  if (value === 'declining') return '学习趋势有下滑'
  if (value === 'new') return '刚开始积累画像'
  return '学习趋势相对稳定'
}

export function ebbinghausRateCaption(alltime: LearningAlltime | null | undefined): string {
  const dueTotal = alltime?.ebbinghaus_due_total ?? 0
  const poolTotal = alltime?.qm_word_total ?? 0

  if (poolTotal === 0) return '还没有进入复习库的词'
  if (dueTotal === 0) return '当前暂无到点词'
  return '按时复习率'
}

export function ebbinghausSummaryHelp(alltime: LearningAlltime | null | undefined): string {
  const dueTotal = alltime?.ebbinghaus_due_total ?? 0
  const poolTotal = alltime?.qm_word_total ?? 0

  if (poolTotal === 0) {
    return '复习库词数 = 已进入艾宾浩斯安排的词。开始速记后，这里会逐步累计。'
  }

  if (dueTotal === 0) {
    return '已到复习点 = 现在该复习的词；按时完成 = 这些词里已及时复习的数量。当前没有词到达复习点，所以前两项会显示 0。'
  }

  return '已到复习点 = 现在该复习的词；按时完成 = 这些词里已及时复习的数量；复习库词数 = 已进入艾宾浩斯安排的总词数。'
}

export function resolveEbbStages(alltime: LearningAlltime | null | undefined): EbbinghausStagePoint[] {
  if (alltime?.ebbinghaus_stages && alltime.ebbinghaus_stages.length > 0) {
    return alltime.ebbinghaus_stages
  }

  return [1, 1, 4, 7, 14, 30].map((interval_days, stage) => ({
    stage,
    interval_days,
    due_total: 0,
    due_met: 0,
    actual_pct: null,
  }))
}

export function isStatsInitialLoading({
  chartLoading,
  summary,
  alltime,
  dailyLength,
  booksLength,
  modesLength,
  modeBreakdownLength,
  pieChartLength,
  historyWrongTopLength,
  pendingWrongTopLength,
  hasLearnerProfile,
}: {
  chartLoading: boolean
  summary: unknown
  alltime: LearningAlltime | null | undefined
  dailyLength: number
  booksLength: number
  modesLength: number
  modeBreakdownLength: number
  pieChartLength: number
  historyWrongTopLength: number
  pendingWrongTopLength: number
  hasLearnerProfile: boolean
}) {
  return (
    chartLoading &&
    !summary &&
    !alltime &&
    dailyLength === 0 &&
    booksLength === 0 &&
    modesLength === 0 &&
    modeBreakdownLength === 0 &&
    pieChartLength === 0 &&
    historyWrongTopLength === 0 &&
    pendingWrongTopLength === 0 &&
    !hasLearnerProfile
  )
}
