import { Skeleton } from '../../ui'

export function MiniBarChart({ data, valueKey, labelKey, tone = 'indigo' }: {
  data: Record<string, any>[]
  valueKey: string
  labelKey: string
  tone?: 'indigo' | 'green'
}) {
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1)
  return (
    <div className="admin-mini-bar-chart">
      <svg className={`admin-mini-bar-chart-svg admin-mini-bar-chart-svg--${tone}`} viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden="true">
        {data.map((d, i) => {
          const h = Math.max(2, Math.round((d[valueKey] / max) * 56))
          const width = 100 / data.length
          const barWidth = Math.max(width - 1.5, 1)
          return (
            <rect
              key={i}
              className="admin-mini-bar-chart-bar"
              x={i * width}
              y={60 - h}
              width={barWidth}
              height={h}
              rx="1.5"
              ry="1.5"
            >
              <title>{`${d[labelKey]}: ${d[valueKey]}`}</title>
            </rect>
          )
        })}
      </svg>
    </div>
  )
}

export function StatCard({ label, value, sub, tone = 'indigo' }: {
  label: string
  value: string | number
  sub?: string
  tone?: 'indigo' | 'green' | 'amber' | 'blue'
}) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className={`admin-stat-value admin-stat-value--${tone}`}>{value}</div>
      {sub && <div className="admin-stat-sub">{sub}</div>}
    </div>
  )
}

export function AdminTableSkeleton() {
  return (
    <div className="admin-table-skeleton" aria-hidden="true">
      <div className="admin-table-skeleton-head">
        {Array.from({ length: 9 }, (_, index) => (
          <Skeleton key={index} width="100%" height={14} />
        ))}
      </div>
      <div className="admin-table-skeleton-body">
        {Array.from({ length: 6 }, (_, rowIndex) => (
          <div key={rowIndex} className="admin-table-skeleton-row">
            <Skeleton width="80%" height={16} />
            <Skeleton width="92%" height={16} />
            <Skeleton width="68%" height={16} />
            <Skeleton width="60%" height={16} />
            <Skeleton width="52%" height={16} />
            <Skeleton width="48%" height={16} />
            <Skeleton width="54%" height={16} />
            <Skeleton width="72%" height={16} />
            <Skeleton width="76%" height={16} />
          </div>
        ))}
      </div>
    </div>
  )
}

export function TtsBooksSkeleton() {
  return (
    <div className="admin-tts-skeleton" aria-hidden="true">
      {Array.from({ length: 6 }, (_, index) => (
        <div key={index} className="tts-book-card tts-book-card--skeleton">
          <Skeleton width="58%" height={18} />
          <div className="tts-book-progress">
            <Skeleton width="100%" height={8} />
            <Skeleton width="46%" height={14} />
          </div>
          <Skeleton variant="rectangular" width="40%" height={38} />
        </div>
      ))}
    </div>
  )
}
