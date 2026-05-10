import type { CSSProperties } from 'react'

export interface ChapterModeChartMeta {
  label: string
  title: string
}

export interface ChapterModeChartRecord {
  correct_count: number
  wrong_count: number
  accuracy: number
  is_completed: boolean
}

interface ChapterModeChartsProps {
  modeMeta: Record<string, ChapterModeChartMeta>
  modes?: Record<string, ChapterModeChartRecord>
  completionPercent: number
}

interface UsedMode {
  key: string
  label: string
  title: string
  accuracy: number
  color: string
}

const CHART_COLORS = [
  'var(--chapter-mode-series-1)',
  'var(--chapter-mode-series-2)',
  'var(--chapter-mode-series-3)',
  'var(--chapter-mode-series-4)',
  'var(--chapter-mode-series-5)',
  'var(--chapter-mode-series-6)',
]

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value))
}

export default function ChapterModeCharts({ modeMeta, modes, completionPercent }: ChapterModeChartsProps) {
  const usedModes = Object.entries(modeMeta).map(([key, meta], index) => {
    const record = modes?.[key]
    if (!record) return null
    const correct = Math.max(0, record.correct_count ?? 0)
    const wrong = Math.max(0, record.wrong_count ?? 0)
    const attempts = correct + wrong
    if (attempts <= 0) return null
    return {
      key,
      label: meta.label,
      title: meta.title,
      accuracy: Math.max(0, Math.min(100, record.accuracy ?? 0)),
      color: CHART_COLORS[index % CHART_COLORS.length],
    }
  }).filter(Boolean) as UsedMode[]

  const safeCompletion = clampPercent(completionPercent)
  const modeSummary = usedModes.length
    ? usedModes.map(mode => `${mode.title} ${mode.accuracy}%`).join('，')
    : '暂无模式练习'

  return (
    <div
      className="chapter-mode-charts"
      role="img"
      aria-label={`章节完成率 ${safeCompletion}%，模式正确率：${modeSummary}`}
    >
      <div className="chapter-mode-chart-panel">
        <div
          className="chapter-mode-completion"
          style={{ '--chapter-completion-percent': `${safeCompletion}%` } as CSSProperties}
        >
          <span>完成率</span>
          <strong>{safeCompletion}%</strong>
          <i />
        </div>

        {usedModes.length > 0 ? (
          <div className="chapter-mode-compare" aria-label="模式正确率纵向对比">
            <span className="chapter-mode-compare-title">模式正确率</span>
            {usedModes.map(mode => (
              <span
                key={mode.key}
                className="chapter-mode-row"
                title={`${mode.title}正确率 ${mode.accuracy}%`}
                style={{
                  '--chapter-mode-color': mode.color,
                  '--chapter-mode-percent': `${mode.accuracy}%`,
                } as CSSProperties}
              >
                <span className="chapter-mode-row-label">
                  <i />
                  <span>{mode.label}</span>
                </span>
                <span className="chapter-mode-row-track">
                  <i />
                </span>
                <strong>{mode.accuracy}%</strong>
              </span>
            ))}
          </div>
        ) : (
          <div className="chapter-mode-empty">暂无模式练习</div>
        )}
      </div>
    </div>
  )
}
