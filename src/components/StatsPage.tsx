import { useState, useRef, type MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStats, useWrongWords, useLearningStats } from '../features/vocabulary/hooks'
import type { MetricKey, RangeKey, DailyLearning } from '../features/vocabulary/hooks'

const MODE_LABELS: Record<string, string> = {
  smart: '智能模式',
  listening: '听力模式',
  meaning: '释义模式',
  dictation: '默写模式',
  radio: '选择模式',
  quickmemory: '速记模式',
}

const RANGE_OPTIONS: { label: string; value: RangeKey }[] = [
  { label: '7天', value: 7 },
  { label: '14天', value: 14 },
  { label: '30天', value: 30 },
]

const METRIC_OPTIONS: { label: string; value: MetricKey }[] = [
  { label: '学习词数', value: 'words' },
  { label: '正确率', value: 'accuracy' },
  { label: '学习时长', value: 'duration' },
]

function fmtDuration(secs: number): string {
  if (!secs) return '0分钟'
  const m = Math.floor(secs / 60)
  if (m < 60) return `${m}分钟`
  return `${Math.floor(m / 60)}小时${m % 60 ? m % 60 + '分钟' : ''}`
}

function fmtDate(dateStr: string, range: RangeKey): string {
  const d = new Date(dateStr)
  if (range === 7) return `${d.getMonth() + 1}/${d.getDate()}`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ── SVG line chart ────────────────────────────────────────────────────────────

interface ChartProps {
  data: DailyLearning[]
  metric: MetricKey
  range: RangeKey
}

function LearningChart({ data, metric, range }: ChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{ idx: number; x: number; y: number } | null>(null)

  const W = 560
  const H = 160
  const padL = 44
  const padR = 12
  const padT = 12
  const padB = 32
  const innerW = W - padL - padR
  const innerH = H - padT - padB

  const getValue = (d: DailyLearning): number | null => {
    if (metric === 'words') return d.words_studied
    if (metric === 'accuracy') return d.accuracy
    if (metric === 'duration') return d.duration_seconds > 0 ? Math.round(d.duration_seconds / 60) : 0
    return null
  }

  const values = data.map(getValue)
  const validValues = values.filter((v): v is number => v != null && v > 0)
  const maxVal = validValues.length > 0 ? Math.max(...validValues) : (metric === 'accuracy' ? 100 : 10)
  const yMax = metric === 'accuracy' ? 100 : maxVal === 0 ? 10 : Math.ceil(maxVal * 1.15)

  const xOf = (i: number) => padL + (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW)
  const yOf = (v: number | null) => {
    if (v == null) return padT + innerH
    return padT + innerH - (v / yMax) * innerH
  }

  // Build polyline points (skip null gaps by splitting into segments)
  const segments: string[][] = []
  let cur: string[] = []
  data.forEach((d, i) => {
    const v = getValue(d)
    if (v != null && (metric !== 'accuracy' || v > 0)) {
      cur.push(`${xOf(i)},${yOf(v)}`)
    } else {
      if (cur.length > 0) { segments.push(cur); cur = [] }
    }
  })
  if (cur.length > 0) segments.push(cur)

  // Fill polygon for the largest segment
  const allPts = segments.flat()
  let fillPoints = ''
  if (allPts.length > 0) {
    const firstX = parseFloat(allPts[0].split(',')[0])
    const lastX = parseFloat(allPts[allPts.length - 1].split(',')[0])
    const baseY = padT + innerH
    fillPoints = `${firstX},${baseY} ${allPts.join(' ')} ${lastX},${baseY}`
  }

  // Y axis labels (4 steps)
  const ySteps = 4
  const yLabels = Array.from({ length: ySteps + 1 }, (_, i) => {
    const val = (yMax * i) / ySteps
    if (metric === 'accuracy') return `${Math.round(val)}%`
    if (metric === 'duration') return val >= 60 ? `${Math.round(val / 60)}h` : `${Math.round(val)}m`
    return `${Math.round(val)}`
  })

  // X axis labels: show a subset based on range
  const xStep = range === 7 ? 1 : range === 14 ? 2 : 5
  const xLabels = data.reduce<{ i: number; label: string }[]>((acc, d, i) => {
    if (i % xStep === 0 || i === data.length - 1) {
      acc.push({ i, label: fmtDate(d.date, range) })
    }
    return acc
  }, [])

  const handleMouseMove = (e: MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const svgX = ((e.clientX - rect.left) / rect.width) * W
    // Find nearest data point
    let closest = 0
    let minDist = Infinity
    data.forEach((_, i) => {
      const dx = Math.abs(xOf(i) - svgX)
      if (dx < minDist) { minDist = dx; closest = i }
    })
    if (minDist < innerW / data.length + 4) {
      const v = getValue(data[closest])
      setTooltip({ idx: closest, x: xOf(closest), y: yOf(v) })
    } else {
      setTooltip(null)
    }
  }

  const tooltipData = tooltip != null ? data[tooltip.idx] : null
  const tooltipVal = tooltipData ? getValue(tooltipData) : null
  const tooltipLabel = tooltipVal == null ? '--'
    : metric === 'accuracy' ? `${tooltipVal}%`
    : metric === 'duration' ? fmtDuration((tooltipData?.duration_seconds ?? 0))
    : `${tooltipVal} 词`

  return (
    <div className="lc-wrap" onMouseLeave={() => setTooltip(null)}>
      <svg
        ref={svgRef}
        className="lc-svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={handleMouseMove}
      >
        {/* Y grid lines + labels */}
        {Array.from({ length: ySteps + 1 }, (_, i) => {
          const ratio = i / ySteps
          const y = padT + innerH - ratio * innerH
          return (
            <g key={i}>
              <line
                x1={padL} y1={y} x2={padL + innerW} y2={y}
                stroke="var(--border)" strokeWidth="0.5"
                strokeDasharray={i === 0 ? undefined : '3,3'}
              />
              <text
                x={padL - 4} y={y + 4}
                textAnchor="end" fontSize="9" fill="var(--text-tertiary)"
              >
                {yLabels[i]}
              </text>
            </g>
          )
        })}

        {/* Fill area */}
        {fillPoints && (
          <polygon points={fillPoints} fill="rgba(255, 126, 54, 0.10)" />
        )}

        {/* Line segments */}
        {segments.map((seg, si) => (
          <polyline
            key={si}
            points={seg.join(' ')}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.8"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* Data dots */}
        {data.map((d, i) => {
          const v = getValue(d)
          if (v == null || (metric !== 'accuracy' && v === 0)) return null
          return (
            <circle
              key={i}
              cx={xOf(i)} cy={yOf(v)}
              r={tooltip?.idx === i ? 5 : 3}
              fill={tooltip?.idx === i ? 'var(--accent)' : 'var(--accent)'}
              stroke="var(--bg-color)"
              strokeWidth={tooltip?.idx === i ? 2 : 0}
            />
          )
        })}

        {/* X axis labels */}
        {xLabels.map(({ i, label }) => (
          <text
            key={i}
            x={xOf(i)} y={H - 6}
            textAnchor="middle" fontSize="9" fill="var(--text-tertiary)"
          >
            {label}
          </text>
        ))}

        {/* Tooltip vertical line */}
        {tooltip && (
          <line
            x1={tooltip.x} y1={padT}
            x2={tooltip.x} y2={padT + innerH}
            stroke="var(--accent)" strokeWidth="1" strokeDasharray="3,2" opacity="0.5"
          />
        )}
      </svg>

      {/* Tooltip bubble */}
      {tooltip && tooltipData && (
        <div
          className="lc-tooltip"
          style={{
            left: `${(tooltip.x / W) * 100}%`,
            top: `${((tooltip.y - padT) / (H - padT - padB)) * 100}%`,
          }}
        >
          <div className="lc-tooltip-date">{tooltipData.date}</div>
          <div className="lc-tooltip-val">{tooltipLabel}</div>
          {metric !== 'accuracy' && tooltipData.sessions > 0 && (
            <div className="lc-tooltip-sub">{tooltipData.sessions} 次练习</div>
          )}
          {metric === 'words' && tooltipData.sessions > 0 && (
            <div className="lc-tooltip-sub">
              {tooltipData.accuracy != null ? `正确率 ${tooltipData.accuracy}%` : ''}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StatsPage() {
  const navigate = useNavigate()
  const { todayWords, totalWords, chapterStats, loading: statsLoading } = useStats()
  const { words: wrongWords } = useWrongWords()

  const [range, setRange] = useState<RangeKey>(30)
  const [metric, setMetric] = useState<MetricKey>('words')
  const [bookId, setBookId] = useState('all')
  const [mode, setMode] = useState('all')

  const { daily, books, modes, summary, alltime, useFallback, loading: chartLoading } = useLearningStats(range, bookId, mode)

  // Today's row from the daily chart data
  const todayStr = new Date().toISOString().slice(0, 10)
  const todayRow = daily.find(d => d.date === todayStr)
  const displayTodayWords = todayRow?.words_studied ?? todayWords

  // Accuracy: use alltime today_accuracy (from chapter progress, always accurate)
  const displayTodayAccuracy = alltime?.today_accuracy != null ? `${alltime.today_accuracy}%` : '--'
  const displayAlltimeAccuracy = alltime?.accuracy != null ? `${alltime.accuracy}%` : '--'

  // Duration: only from real sessions
  const displayTodayDuration = alltime && alltime.today_duration_seconds > 0
    ? fmtDuration(alltime.today_duration_seconds) : null
  const displayAlltimeDuration = alltime && alltime.duration_seconds > 0
    ? fmtDuration(alltime.duration_seconds) : null

  // Total words: from chapter progress (words_learned), always accurate
  const displayTotalWords = alltime?.total_words ?? totalWords

  const hasChartData = daily.some(d => {
    if (metric === 'words') return d.words_studied > 0
    if (metric === 'accuracy') return d.accuracy != null
    return d.duration_seconds > 0
  })

  return (
    <div className="stats-page">
      <div className="page-content">

        {/* Top stat cards */}
        <div className="stats-cards">
          <div className="stats-card">
            <div className="stats-card-value">{displayTodayWords}</div>
            <div className="stats-card-label">今日学习词数</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayTodayAccuracy}</div>
            <div className="stats-card-label">
              今日正确率
              {displayTodayDuration && <span className="stats-card-sub">{displayTodayDuration}</span>}
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayTotalWords}</div>
            <div className="stats-card-label">累计学习词数</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayAlltimeAccuracy}</div>
            <div className="stats-card-label">
              累计正确率
              {displayAlltimeDuration && <span className="stats-card-sub">{displayAlltimeDuration}</span>}
            </div>
          </div>
        </div>

        {/* Learning chart */}
        <div className="stats-section">
          <div className="stats-section-header">
            <h2 className="stats-section-title">学习记录</h2>
            {/* Range tabs */}
            <div className="lc-tabs">
              {RANGE_OPTIONS.map(o => (
                <button
                  key={o.value}
                  className={`lc-tab${range === o.value ? ' active' : ''}`}
                  onClick={() => setRange(o.value)}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Metric + filter bar */}
          <div className="lc-filters">
            <div className="lc-metric-tabs">
              {METRIC_OPTIONS.map(o => (
                <button
                  key={o.value}
                  className={`lc-metric-tab${metric === o.value ? ' active' : ''}`}
                  onClick={() => setMetric(o.value)}
                >
                  {o.label}
                </button>
              ))}
            </div>
            <div className="lc-selects">
              {books.length > 0 && (
                <select
                  className="lc-select"
                  value={bookId}
                  onChange={e => setBookId(e.target.value)}
                >
                  <option value="all">全部词书</option>
                  {books.map(b => (
                    <option key={b.id} value={b.id}>{b.title}</option>
                  ))}
                </select>
              )}
              {modes.length > 0 && (
                <select
                  className="lc-select"
                  value={mode}
                  onChange={e => setMode(e.target.value)}
                >
                  <option value="all">全部模式</option>
                  {modes.map(m => (
                    <option key={m} value={m}>{MODE_LABELS[m] || m}</option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Chart */}
          {chartLoading ? (
            <div className="stats-chart-loading"><div className="loading-spinner" /></div>
          ) : !hasChartData ? (
            <div className="stats-empty" style={{ padding: '24px 0' }}>
              <p>该时间段暂无学习记录</p>
              <a className="stats-go-practice" onClick={() => navigate('/')}>去练习 →</a>
            </div>
          ) : (
            <LearningChart data={daily} metric={metric} range={range} />
          )}

          {/* Legend + period summary */}
          {!chartLoading && hasChartData && summary && (
            <div className="lc-legend-row">
              <div className="lc-legend">
                <span className="legend-dot" style={{ background: 'var(--accent)' }} />
                <span>{METRIC_OPTIONS.find(o => o.value === metric)?.label}</span>
                {useFallback && (
                  <span className="lc-fallback-note">（基于章节进度估算）</span>
                )}
              </div>
              <div className="lc-period-summary">
                <span>{range}天共 <strong>{summary.total_words}</strong> 词</span>
                {summary.accuracy != null && <span>· 正确率 <strong>{summary.accuracy}%</strong></span>}
                {!useFallback && <span>· <strong>{summary.total_sessions}</strong> 次练习</span>}
              </div>
            </div>
          )}
        </div>

        {/* Chapter accuracy */}
        <div className="stats-section">
          <h2 className="stats-section-title">章节正确率</h2>
          {statsLoading ? (
            <div className="stats-chart-loading"><div className="loading-spinner" /></div>
          ) : chapterStats.length === 0 ? (
            <div className="stats-empty">
              <p>暂无章节正确率数据</p>
              <a className="stats-go-practice" onClick={() => navigate('/')}>去练习 →</a>
            </div>
          ) : (
            <div className="stats-accuracy-list">
              {chapterStats.map(s => (
                <div key={s.bookId} className="stats-accuracy-item">
                  <div className="stats-accuracy-title">{s.title}</div>
                  <div className="stats-accuracy-bar-wrap">
                    <div
                      className="stats-accuracy-bar"
                      style={{ width: `${s.accuracy || 0}%` }}
                    />
                  </div>
                  <div className="stats-accuracy-pct">{s.accuracy != null ? `${s.accuracy}%` : '--'}</div>
                  <div className="stats-accuracy-counts">
                    <span className="correct-count">✓ {s.correct}</span>
                    <span className="wrong-count">✗ {s.wrong}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Wrong words summary */}
        <div className="stats-section">
          <h2 className="stats-section-title">错词概览</h2>
          <div className="stats-wrong-summary">
            <div className="stats-wrong-count">
              <span className="wrong-num">{wrongWords.length}</span>
              <span className="wrong-label">个错词</span>
            </div>
            {wrongWords.length > 0 && (
              <button className="stats-review-btn" onClick={() => navigate('/errors')}>
                查看错词本 →
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
