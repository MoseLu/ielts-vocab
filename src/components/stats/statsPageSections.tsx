import type { NavigateFunction } from 'react-router-dom'
import type { MetricKey, RangeKey } from '../../features/vocabulary/hooks'

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
  window.dispatchEvent(new CustomEvent('practice-mode-request', {
    detail: { mode: 'quickmemory' },
  }))
  navigate('/practice?review=due')
}

interface StatsSummaryCardsProps {
  dueReviews: number | string
  pendingWrongWords: number | string
  focusBookRemaining: string
  focusBookScope: string
  focusBookMeaning: string
  todayWords: number | string
  todayDuration: string
  todayAccuracy: string
  weakestMode: string
  totalLearned: number | string
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
  dueReviews,
  pendingWrongWords,
  focusBookRemaining,
  focusBookScope,
  focusBookMeaning,
  todayWords,
  todayDuration,
  todayAccuracy,
  weakestMode,
  totalLearned,
  streak,
}: StatsSummaryCardsProps) {
  const cards: StatsSummaryCard[] = [
    {
      value: dueReviews,
      label: '到期待复习词',
      variant: 'detailed',
      scope: '按速记队列里已经到复习点的词数统计，优先看今天还剩多少没清掉。',
      meaning: '这是今天最该先处理的积压量，不是累计复习次数。',
    },
    {
      value: pendingWrongWords,
      label: '待清错词',
      variant: 'detailed',
      scope: '按错词本里仍未过关的词统计，只有连续答对到目标次数才会消掉。',
      meaning: '表示今天除了到期复习之外，还有多少错词需要继续清理。',
    },
    {
      value: focusBookRemaining,
      label: '当前词书剩余',
      variant: 'detailed',
      scope: focusBookScope,
      meaning: focusBookMeaning,
    },
    {
      value: todayWords,
      label: '今日学习词数',
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
      value: weakestMode,
      label: '当前弱项模式',
      variant: 'simple',
    },
    {
      value: totalLearned,
      label: '累计学过的不同词',
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
