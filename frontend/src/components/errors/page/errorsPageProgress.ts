import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  WRONG_WORD_SCOPE_LABELS,
  getWrongWordDimensionHistoryWrong,
  getWrongWordDimensionProgress,
  getWrongWordDimensionState,
} from '../../../features/vocabulary/wrongWordsStore'

type Tone = 'neutral' | 'warning' | 'accent' | 'success'

export interface ErrorJourneyStep {
  step: string
  label: string
  detail: string
  tone: Tone
}

export interface ErrorBookOverview {
  activeIndex: number
  focusLabel: string
  steps: ErrorJourneyStep[]
}

export interface WrongWordDimensionProgressModel {
  dimension: WrongWordDimension
  label: string
  headline: string
  detail: string
  historyWrong: number
  progressPercent: number
  pending: boolean
  clearedToday: boolean
}

export interface WrongWordCardModel {
  statusTone: Tone
  statusLabel: string
  statusDescription: string
  isTodayNew: boolean
  feedbackLabel: string | null
  focusLabel: string | null
  bookProgressLabel: string
  bookProgressNote: string
  bookProgressPercent: number
  historyDimensionCount: number
  pendingDimensionCount: number
  clearedDimensionCount: number
  reviewProgressLabel: string
  reviewProgressNote: string
  reviewProgressPercent: number
  reviewTarget: number
  reviewStreak: number
  reviewRemaining: number
  dimensions: WrongWordDimensionProgressModel[]
}

function getTimestamp(value?: string): number | null {
  if (typeof value !== 'string' || !value.trim()) return null
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? null : timestamp
}

function isToday(value?: string): boolean {
  const timestamp = getTimestamp(value)
  if (timestamp == null) return false

  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()
  const end = start + (24 * 60 * 60 * 1000)
  return timestamp >= start && timestamp < end
}

function formatMonthDay(value?: string): string | null {
  const timestamp = getTimestamp(value)
  if (timestamp == null) return null

  const date = new Date(timestamp)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function buildDimensionProgressModel(
  word: WrongWordRecord,
  dimension: WrongWordDimension,
): WrongWordDimensionProgressModel | null {
  const historyWrong = getWrongWordDimensionHistoryWrong(word, dimension)
  if (historyWrong <= 0) return null

  const progress = getWrongWordDimensionProgress(word, dimension)
  const state = getWrongWordDimensionState(word, dimension)
  const clearedAt = formatMonthDay(state.last_pass_at)

  return {
    dimension,
    label: WRONG_WORD_DIMENSION_LABELS[dimension],
    headline: progress.pending
      ? `连对 ${progress.streak}/${progress.target}`
      : '已移出待清',
    detail: progress.pending
      ? `累计错 ${historyWrong} 次，还差 ${progress.remaining} 次连续答对`
      : (
          clearedAt
            ? `累计错 ${historyWrong} 次，${clearedAt} 已移出待清`
            : `累计错 ${historyWrong} 次，这一项已经过关`
        ),
    historyWrong,
    progressPercent: progress.target > 0 ? Math.round((progress.streak / progress.target) * 100) : 0,
    pending: progress.pending,
    clearedToday: !progress.pending && isToday(state.last_pass_at),
  }
}

export function buildErrorBookOverview(scope: WrongWordCollectionScope): ErrorBookOverview {
  return {
    activeIndex: scope === 'pending' ? 1 : 2,
    focusLabel: `当前查看：${WRONG_WORD_SCOPE_LABELS[scope]}`,
    steps: [
      {
        step: '第 1 步',
        label: '答错收录',
        detail: '答错就会进入错词本',
        tone: 'neutral',
      },
      {
        step: '第 2 步',
        label: '待清推进',
        detail: '优先把问题项刷出待清',
        tone: 'warning',
      },
      {
        step: '第 3 步',
        label: '累计保留',
        detail: '累计记录还会继续保留',
        tone: 'accent',
      },
      {
        step: '第 4 步',
        label: '长期复习',
        detail: '最后进入长期稳固阶段',
        tone: 'success',
      },
    ],
  }
}

export function buildWrongWordCardModel(word: WrongWordRecord): WrongWordCardModel {
  const dimensions = WRONG_WORD_DIMENSIONS
    .map(dimension => buildDimensionProgressModel(word, dimension))
    .filter((dimension): dimension is WrongWordDimensionProgressModel => Boolean(dimension))

  const historyDimensionCount = dimensions.length
  const pendingDimensionCount = dimensions.filter(dimension => dimension.pending).length
  const clearedDimensionCount = Math.max(0, historyDimensionCount - pendingDimensionCount)
  const movedOutTodayCount = dimensions.filter(dimension => dimension.clearedToday).length
  const hasProgressToday = dimensions.some(dimension => isToday(getWrongWordDimensionState(word, dimension.dimension).last_pass_at))
  const isTodayNew = isToday(word.first_wrong_at)
  const nextPendingDimension = dimensions
    .filter(dimension => dimension.pending)
    .sort((left, right) => left.progressPercent - right.progressPercent || right.historyWrong - left.historyWrong)[0]

  let statusTone: Tone = 'warning'
  let statusLabel = '清错推进中'
  let statusDescription = pendingDimensionCount > 0
    ? `还有 ${pendingDimensionCount} 项问题没移出待清。`
    : '这个词已经完成错词本当前阶段。'

  if (pendingDimensionCount <= 0 && Boolean(word.ebbinghaus_completed)) {
    statusTone = 'success'
    statusLabel = '长期稳固完成'
    statusDescription = '错词本和艾宾浩斯这两步都已经通过。'
  } else if (pendingDimensionCount <= 0) {
    statusTone = 'accent'
    statusLabel = '已移出待清'
    statusDescription = '错词本这一步已经过关，后面继续用艾宾浩斯稳住。'
  } else if (isTodayNew) {
    statusLabel = '今日新入，开始清错'
    statusDescription = '这个词今天刚进入错词本，可以先把最短板的一项刷起来。'
  } else if (nextPendingDimension) {
    statusDescription = `优先推进 ${nextPendingDimension.label}，当前 ${nextPendingDimension.headline}。`
  }

  const reviewTarget = Math.max(
    typeof word.ebbinghaus_target === 'number' ? word.ebbinghaus_target : 0,
    Boolean(word.ebbinghaus_completed) ? 1 : 0,
  )
  const reviewStreak = Math.max(0, Math.min(word.ebbinghaus_streak ?? 0, reviewTarget || 0))
  const reviewRemaining = Math.max(0, reviewTarget - reviewStreak)
  const reviewProgressPercent = Boolean(word.ebbinghaus_completed)
    ? 100
    : (reviewTarget > 0 ? Math.round((reviewStreak / reviewTarget) * 100) : 0)

  return {
    statusTone,
    statusLabel,
    statusDescription,
    isTodayNew,
    feedbackLabel: movedOutTodayCount > 0
      ? `今天移出 ${movedOutTodayCount} 项`
      : (hasProgressToday ? '今天有推进' : null),
    focusLabel: nextPendingDimension
      ? `优先 ${nextPendingDimension.label} · ${nextPendingDimension.headline}`
      : null,
    bookProgressLabel: historyDimensionCount > 0
      ? `${clearedDimensionCount}/${historyDimensionCount} 项已移出待清`
      : '暂未形成问题项',
    bookProgressNote: pendingDimensionCount > 0
      ? `还剩 ${pendingDimensionCount} 项问题留在待清里。`
      : '错词本这一步已经清空。',
    bookProgressPercent: historyDimensionCount > 0
      ? Math.round((clearedDimensionCount / historyDimensionCount) * 100)
      : 0,
    historyDimensionCount,
    pendingDimensionCount,
    clearedDimensionCount,
    reviewProgressLabel: Boolean(word.ebbinghaus_completed)
      ? '艾宾浩斯已完成'
      : (reviewTarget > 0 ? `艾宾浩斯 ${reviewStreak}/${reviewTarget}` : '等待长期复习'),
    reviewProgressNote: Boolean(word.ebbinghaus_completed)
      ? '这个词的长期识别复习已经稳定。'
      : (
          reviewTarget > 0
            ? `还差 ${reviewRemaining} 次长期复习。`
            : '清错完成后会继续进入长期复习。'
        ),
    reviewProgressPercent,
    reviewTarget,
    reviewStreak,
    reviewRemaining,
    dimensions,
  }
}
