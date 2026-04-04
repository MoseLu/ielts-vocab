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
  todayNew: number | string
  totalNew: number | string
  todayReview: number | string
  alltimeReview: number | string
  todayDuration: string
  alltimeDuration: string
  todayAccuracy: string
  alltimeAccuracy: string
  streak: number | string
}

export function StatsSummaryCards({
  todayNew,
  totalNew,
  todayReview,
  alltimeReview,
  todayDuration,
  alltimeDuration,
  todayAccuracy,
  alltimeAccuracy,
  streak,
}: StatsSummaryCardsProps) {
  const cards = [
    { value: todayNew, label: '今日学习新词数' },
    { value: totalNew, label: '累计学习新词数' },
    { value: todayReview, label: '今日复习旧词数' },
    { value: alltimeReview, label: '累计复习旧词数', sub: '至少 2 轮作答的词' },
    { value: todayDuration, label: '今日学习时长' },
    { value: alltimeDuration, label: '累计学习时长' },
    { value: todayAccuracy, label: '今日正确率', sub: '章节进度' },
    { value: alltimeAccuracy, label: '累计正确率', sub: '章节进度' },
    { value: streak, label: '连续学习', sub: '天' },
  ]

  return (
    <div className="stats-cards stats-cards-9">
      {cards.map(card => (
        <div key={card.label} className="stats-card">
          <div className="stats-card-value">{card.value}</div>
          <div className="stats-card-label">{card.label}</div>
          {card.sub ? <div className="stats-card-sub">{card.sub}</div> : null}
        </div>
      ))}
    </div>
  )
}
