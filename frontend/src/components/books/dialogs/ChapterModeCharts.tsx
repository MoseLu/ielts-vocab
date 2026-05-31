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

interface ChapterModeCompletionRow {
  key: string
  kind: 'completion'
  label: string
  percent: number
  color: string
  title: string
}

interface ChapterModeAccuracyRow {
  key: string
  kind: 'mode'
  label: string
  percent: number
  color: string
  title: string
  summaryLabel: string
}

interface ChapterModeSectionRow {
  key: string
  kind: 'section'
  label: string
}

type ChapterModeValueRow = ChapterModeCompletionRow | ChapterModeAccuracyRow
type ChapterModeTableRow = ChapterModeSectionRow | ChapterModeValueRow

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
  const safeCompletion = clampPercent(completionPercent)
  const modeRows = Object.entries(modeMeta).map<ChapterModeAccuracyRow | null>(([key, meta], index) => {
    const record = modes?.[key]
    if (!record) return null
    const correct = Math.max(0, record.correct_count ?? 0)
    const wrong = Math.max(0, record.wrong_count ?? 0)
    const attempts = correct + wrong
    if (attempts <= 0) return null
    const accuracy = clampPercent(record.accuracy ?? 0)
    return {
      key,
      kind: 'mode',
      label: meta.label,
      percent: accuracy,
      color: CHART_COLORS[index % CHART_COLORS.length],
      title: `${meta.title}正确率 ${accuracy}%`,
      summaryLabel: `${meta.title} ${accuracy}%`,
    }
  }).filter((row): row is ChapterModeAccuracyRow => row !== null)

  const modeSectionRows: ChapterModeTableRow[] = modeRows.length
    ? [{ key: 'mode-section', kind: 'section', label: '模式正确率' }]
    : []
  const rows: ChapterModeTableRow[] = [
    {
      key: 'completion',
      kind: 'completion',
      label: '完成率',
      percent: safeCompletion,
      color: 'var(--chapter-card-tone, var(--accent))',
      title: `章节完成率 ${safeCompletion}%`,
    },
    ...modeSectionRows,
    ...modeRows,
  ]
  const modeSummary = modeRows.length
    ? modeRows.map(mode => mode.summaryLabel).join('，')
    : '暂无模式练习'

  return (
    <div
      className="chapter-mode-charts"
      role="img"
      aria-label={`章节完成率 ${safeCompletion}%，模式正确率：${modeSummary}`}
    >
      <div className="chapter-mode-chart-panel">
        <div className="chapter-mode-table" aria-label="章节完成率与模式正确率">
          {rows.map(row => row.kind === 'section' ? (
            <span key={row.key} className="chapter-mode-table-section">
              <span>{row.label}</span>
            </span>
          ) : (
            <span
              key={row.key}
              className={`chapter-mode-table-row chapter-mode-table-row-${row.kind}`}
              title={row.title}
              style={{
                '--chapter-mode-color': row.color,
                '--chapter-mode-percent': `${row.percent}%`,
              } as CSSProperties}
            >
              <span className="chapter-mode-cell chapter-mode-cell-label">
                {row.kind === 'mode' && <i />}
                <span>{row.label}</span>
              </span>
              <span className="chapter-mode-cell chapter-mode-cell-track">
                <span className="chapter-mode-row-track">
                  <i />
                </span>
              </span>
              <strong className="chapter-mode-cell chapter-mode-cell-value">
                {row.percent}%
              </strong>
            </span>
          ))}
        </div>

        {modeRows.length === 0 && (
          <div className="chapter-mode-empty">暂无模式练习</div>
        )}
      </div>
    </div>
  )
}
