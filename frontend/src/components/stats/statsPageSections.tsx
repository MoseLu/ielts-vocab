import type { NavigateFunction } from 'react-router-dom'
import type { MetricKey, RangeKey } from '../../features/vocabulary/hooks'
import { requestPracticeMode } from '../../composables/practice/page/practiceModeEvents'

export const RANGE_OPTIONS: Array<{ value: RangeKey; label: string }> = [
  { value: 7, label: '7天' },
  { value: 14, label: '14天' },
  { value: 30, label: '30天' },
]

export const METRIC_OPTIONS: Array<{ value: MetricKey; label: string }> = [
  { value: 'words', label: '学习词数' },
  { value: 'accuracy', label: '正确率' },
  { value: 'duration', label: '学习时长' },
]

export function ebbRateToneClass(rate: number | null | undefined): string {
  if (rate == null) return 'ebb-rate--na'
  if (rate < 60) return 'ebb-rate--low'
  if (rate < 80) return 'ebb-rate--mid'
  return 'ebb-rate--high'
}

export function startEbbinghausReview(navigate: NavigateFunction): void {
  requestPracticeMode('quickmemory')
  navigate('/practice?review=due')
}

interface StatsSummaryCardsProps {
  todayNewWords: number | string
  todayReviewWords: number | string
  totalLearnedNewWords: number | string
  totalReviewedWords: number | string
  totalStudyDuration: string
  todayWords: number | string
  todayDuration: string
  todayAccuracy: string
  streak: number | string
}

interface StatsSummaryCard {
  value: number | string
  label: string
  variant: 'detailed' | 'simple'
  scope?: string
  meaning?: string
}

export function StatsSummaryCards({
  todayNewWords,
  todayReviewWords,
  totalLearnedNewWords,
  totalReviewedWords,
  totalStudyDuration,
  todayWords,
  todayDuration,
  todayAccuracy,
  streak,
}: StatsSummaryCardsProps) {
  const cards: StatsSummaryCard[] = [
    {
      value: todayNewWords,
      label: '今日学习新词',
      variant: 'detailed',
      scope: '按今天第一次进入速记记忆队列的不同单词统计。',
      meaning: '表示今天第一次开始学、并写入记忆计划的新词数。',
    },
    {
      value: todayReviewWords,
      label: '今日复习旧词',
      variant: 'detailed',
      scope: '按今天有复习记录且首次学习时间早于今天的不同单词统计。',
      meaning: '表示今天回顾过多少旧词，不包含首次接触的新词。',
    },
    {
      value: totalLearnedNewWords,
      label: '累计学习新词',
      variant: 'detailed',
      scope: '按累计学过的不同单词统计；章节累计明显虚高时，会回退到全局去重口径。',
      meaning: '表示从开始使用到现在，一共学过多少个不同的新词。',
    },
    {
      value: todayWords,
      label: '今日学过单词',
      variant: 'simple',
    },
    {
      value: todayDuration,
      label: '今日学习时长',
      variant: 'simple',
    },
    {
      value: todayAccuracy,
      label: '今日答题正确率',
      variant: 'simple',
    },
    {
      value: totalReviewedWords,
      label: '累计复习旧词',
      variant: 'simple',
    },
    {
      value: totalStudyDuration,
      label: '总学习时长',
      variant: 'simple',
    },
    {
      value: streak,
      label: '连续学习天数',
      variant: 'simple',
    },
  ]

  return (
    <div className="stats-cards stats-cards-9">
      {cards.map(card => (
        <div key={card.label} className={`stats-card stats-card--${card.variant}`}>
          <div className="stats-card-label">{card.label}</div>
          <div className="stats-card-value">{card.value}</div>
          {card.variant === 'detailed' ? (
            <div className="stats-card-meta">
              <div className="stats-card-meta-row">
                <span className="stats-card-meta-label">怎么算</span>
                <span className="stats-card-meta-text">{card.scope}</span>
              </div>
              <div className="stats-card-meta-row">
                <span className="stats-card-meta-label">表示什么</span>
                <span className="stats-card-meta-text">{card.meaning}</span>
              </div>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  )
}
