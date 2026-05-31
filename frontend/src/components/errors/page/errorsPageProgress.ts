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
  detail: string
  historyWrong: number
  progressPercent: number
  pending: boolean
}

export interface WrongWordCardModel {
  dimensions: WrongWordDimensionProgressModel[]
}

function getTimestamp(value?: string): number | null {
  if (typeof value !== 'string' || !value.trim()) return null
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? null : timestamp
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
    detail: progress.pending
      ? `累计错 ${historyWrong} 次，答对一次即可处理`
      : (
          clearedAt
            ? `累计错 ${historyWrong} 次，${clearedAt} 已完成`
            : `累计错 ${historyWrong} 次，这一项已经过关`
        ),
    historyWrong,
    progressPercent: progress.target > 0 ? Math.round((progress.streak / progress.target) * 100) : 0,
    pending: progress.pending,
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

  return {
    dimensions,
  }
}
