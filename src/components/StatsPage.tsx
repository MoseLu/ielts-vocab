import {
  useState,
  useRef,
  useLayoutEffect,
  useCallback,
  useEffect,
  type CSSProperties,
  type MouseEvent,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords, useLearningStats } from '../features/vocabulary/hooks'
import type {
  MetricKey,
  RangeKey,
  DailyLearning,
  ModeStat,
  PieSegment,
  EbbinghausStagePoint,
  WrongTopItem,
} from '../features/vocabulary/hooks'

const MODE_LABELS: Record<string, string> = {
  smart: '智能模式',
  listening: '听力模式',
  meaning: '释义模式',
  dictation: '默写模式',
  radio: '选择模式',
  quickmemory: '速记模式',
  errors: '错词本',
}

const PIE_COLORS = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899', '#14b8a6', '#eab308', '#64748b']

function inferErrorReason(w: WrongTopItem): string {
  const lw = w.listening_wrong ?? 0
  const mw = w.meaning_wrong ?? 0
  const dw = w.dictation_wrong ?? 0
  const total = lw + mw + dw
  if (total === 0) return '—'
  if (lw >= mw && lw >= dw) return '听力'
  if (mw >= lw && mw >= dw) return '释义'
  if (dw >= lw && dw >= mw) return '拼写'
  return '—'
}

const RANGE_OPTIONS: { label: string; value: RangeKey }[] = [
  { label: '7天', value: 7 },
  { label: '14天', value: 14 },
  { label: '30天', value: 30 },
]

const METRIC_OPTIONS: { label: string; value: MetricKey }[] = [
  { label: '学习词数（不重复）', value: 'words' },
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

function fmtPct(n: number | null | undefined): string {
  if (n == null) return '--'
  return `${n}%`
}

/** 总达成率：<50 红；50–80 橙；>80 绿；无数据中性灰 */
function ebbRateToneClass(rate: number | null | undefined): string {
  if (rate == null) return 'ebb-rate--na'
  if (rate < 50) return 'ebb-rate--low'
  if (rate <= 80) return 'ebb-rate--mid'
  return 'ebb-rate--high'
}

// ── SVG 扇形图（模式学习量占比）──────────────────────────────────────────────

function ModePieChart({ segments, variant = 'card' }: { segments: PieSegment[]; variant?: 'card' | 'strip' }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  if (total <= 0) {
    return <div className="stats-pie-empty">暂无模式分布（需有带模式的练习会话）</div>
  }
  const cx = 70
  const cy = 70
  const r = 58
  let angle = -Math.PI / 2
  const paths: ReactNode[] = []
  segments.forEach((seg, i) => {
    const a = (seg.value / total) * 2 * Math.PI
    const x1 = cx + r * Math.cos(angle)
    const y1 = cy + r * Math.sin(angle)
    angle += a
    const x2 = cx + r * Math.cos(angle)
    const y2 = cy + r * Math.sin(angle)
    const large = a > Math.PI ? 1 : 0
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
    paths.push(
      <path
        key={`${seg.mode}-${i}`}
        d={d}
        fill={PIE_COLORS[i % PIE_COLORS.length]}
        stroke="var(--bg-color)"
        strokeWidth="1.5"
      />,
    )
  })
  const wrapClass = variant === 'strip'
    ? 'stats-pie-wrap stats-pie-wrap--strip'
    : 'stats-pie-wrap stats-pie-wrap--mode'
  const svgClass = variant === 'strip'
    ? 'stats-pie-svg stats-pie-svg--strip'
    : 'stats-pie-svg stats-pie-svg--sm'
  const legClass = variant === 'strip'
    ? 'stats-pie-legend stats-pie-legend--strip'
    : 'stats-pie-legend stats-pie-legend--compact'
  return (
    <div className={wrapClass}>
      <svg className={svgClass} viewBox="0 0 140 140" aria-hidden>
        {paths}
      </svg>
      <ul className={legClass}>
        {segments.map((seg, i) => (
          <li key={seg.mode}>
            <span className="stats-pie-dot" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
            <span className="stats-pie-label">{MODE_LABELS[seg.mode] || seg.mode}</span>
            <span className="stats-pie-val">{Math.round((seg.value / total) * 100)}%</span>
            <span className="stats-pie-sub">{seg.value} 词</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Top10 错词：按错次占比的扇形图 */
const WRONG_PIE_COLORS = ['#dc2626', '#ea580c', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#14b8a6', '#0ea5e9', '#6366f1', '#a855f7']

function WrongTopPieChart({ items }: { items: WrongTopItem[] }) {
  const total = items.reduce((s, x) => s + x.wrong_count, 0)
  if (total <= 0) {
    return <div className="stats-pie-empty">暂无错词分布</div>
  }
  const cx = 70
  const cy = 70
  const r = 58
  let angle = -Math.PI / 2
  const paths: ReactNode[] = []
  items.forEach((seg, i) => {
    const a = (seg.wrong_count / total) * 2 * Math.PI
    const x1 = cx + r * Math.cos(angle)
    const y1 = cy + r * Math.sin(angle)
    angle += a
    const x2 = cx + r * Math.cos(angle)
    const y2 = cy + r * Math.sin(angle)
    const large = a > Math.PI ? 1 : 0
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
    paths.push(
      <path
        key={`${seg.word}-${i}`}
        d={d}
        fill={WRONG_PIE_COLORS[i % WRONG_PIE_COLORS.length]}
        stroke="var(--bg-color)"
        strokeWidth="1.5"
      />,
    )
  })
  return (
    <div className="stats-pie-wrap stats-pie-wrap--wrong-top">
      <svg className="stats-pie-svg stats-pie-svg--lg" viewBox="0 0 140 140" aria-hidden>
        {paths}
      </svg>
      <ul className="stats-pie-legend stats-pie-legend--wrong">
        {items.map((seg, i) => (
          <li key={`${seg.word}-${i}`}>
            <span className="stats-pie-dot" style={{ background: WRONG_PIE_COLORS[i % WRONG_PIE_COLORS.length] }} />
            <span className="stats-pie-label" title={seg.word}>
              {seg.word.length > 14 ? `${seg.word.slice(0, 13)}…` : seg.word}
            </span>
            <span className="stats-pie-val">{Math.round((seg.wrong_count / total) * 100)}%</span>
            <span className="stats-pie-sub">{seg.wrong_count} 次</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** 蓝线=艾宾浩斯标准遗忘曲线（理论参考折线）；橙线=各轮实际按时复习完成度 */
const EBB_TARGET = '#0ea5e9'
const EBB_ACTUAL = '#ea580c'

/** 六轮复习间隔对应的「标准遗忘」参考保留率（示意，连成折线；非常数 100% 横线） */
const EBB_STANDARD_FORGETTING_REF: readonly number[] = [100, 92, 78, 65, 52, 42]

function refForgettingPct(stageIndex: number, totalStages: number): number {
  const curve = EBB_STANDARD_FORGETTING_REF
  if (totalStages <= 0) return curve[0]
  if (totalStages === 1) return curve[Math.min(stageIndex, curve.length - 1)]
  const maxIdx = curve.length - 1
  const t = (stageIndex / (totalStages - 1)) * maxIdx
  const lo = Math.floor(t)
  const hi = Math.min(lo + 1, maxIdx)
  const f = t - lo
  const a = curve[lo] ?? curve[maxIdx]
  const b = curve[hi] ?? a
  return a + (b - a) * f
}

const EBB_TIP_HALF_W = 112

function EbbinghausDualChart({ stages, compact }: { stages: EbbinghausStagePoint[]; compact?: boolean }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  const [tipPos, setTipPos] = useState<{ x: number; y: number } | null>(null)

  const W = 560
  const H = compact ? 128 : 200
  const padL = compact ? 38 : 44
  const padR = 12
  const padT = compact ? 8 : 16
  const padB = compact ? 30 : 48
  const innerW = W - padL - padR
  const innerH = H - padT - padB
  const n = Math.max(stages.length, 1)
  const xOf = (i: number) => padL + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW)
  const yOf = (pct: number) => padT + innerH - (pct / 100) * innerH

  const targetPts = stages.map((_, i) => `${xOf(i)},${yOf(refForgettingPct(i, n))}`).join(' ')
  const actualSegments: string[] = []
  let cur: string[] = []
  stages.forEach((s, i) => {
    if (s.actual_pct != null && s.due_total > 0) {
      cur.push(`${xOf(i)},${yOf(s.actual_pct)}`)
    } else if (cur.length > 0) {
      actualSegments.push(cur.join(' '))
      cur = []
    }
  })
  if (cur.length > 0) actualSegments.push(cur.join(' '))

  const hasActual = stages.some(s => s.due_total > 0 && s.actual_pct != null)

  const stageLabel = (s: EbbinghausStagePoint) => `${s.interval_days}d`

  const onMove = (e: MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const svgX = ((e.clientX - rect.left) / rect.width) * W
    let bestI = 0
    let minD = Infinity
    stages.forEach((_, i) => {
      const d = Math.abs(xOf(i) - svgX)
      if (d < minD) {
        minD = d
        bestI = i
      }
    })
    const threshold = innerW / Math.max((stages.length - 1) * 2, 6)
    const hit = minD < threshold ? bestI : null
    setHoverIdx(hit)
    if (hit != null) {
      const vw = typeof window !== 'undefined' ? window.innerWidth : 1200
      const x = Math.min(Math.max(e.clientX, EBB_TIP_HALF_W + 6), vw - EBB_TIP_HALF_W - 6)
      setTipPos({ x, y: rect.top + 4 })
    } else {
      setTipPos(null)
    }
  }

  const hi = hoverIdx != null ? stages[hoverIdx] : null

  return (
    <div
      className={`ebb-chart-wrap${compact ? ' ebb-chart-wrap--compact' : ''}`}
      onMouseLeave={() => {
        setHoverIdx(null)
        setTipPos(null)
      }}
    >
      <svg
        ref={svgRef}
        className="ebb-chart-svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMove}
      >
        {[0, 25, 50, 75, 100].map(pct => (
          <g key={pct}>
            <line
              x1={padL}
              y1={yOf(pct)}
              x2={W - padR}
              y2={yOf(pct)}
              stroke="var(--border)"
              strokeWidth="1"
              strokeDasharray={pct === 0 || pct === 100 ? '0' : '4 4'}
              opacity={0.7}
            />
            <text x={padL - 4} y={yOf(pct) + 4} textAnchor="end" fontSize="9" fill="var(--text-tertiary)">
              {pct}%
            </text>
          </g>
        ))}
        <polyline fill="none" stroke={EBB_TARGET} strokeWidth="2.5" strokeDasharray="8 5" points={targetPts} />
        {actualSegments.map((pts, idx) => (
          <polyline key={idx} fill="none" stroke={EBB_ACTUAL} strokeWidth="2.5" points={pts} />
        ))}
        {stages.map((s, i) => (
          <g key={s.stage}>
            <circle cx={xOf(i)} cy={yOf(refForgettingPct(i, n))} r="4" fill={EBB_TARGET} opacity={0.95} />
            {s.actual_pct != null && s.due_total > 0 && (
              <circle cx={xOf(i)} cy={yOf(s.actual_pct)} r="5" fill={EBB_ACTUAL} stroke="var(--bg-color)" strokeWidth="1.5" />
            )}
            <text
              x={xOf(i)}
              y={H - 6}
              textAnchor="middle"
              fontSize="9"
              fill="var(--text-tertiary)"
            >
              {stageLabel(s)}
            </text>
          </g>
        ))}
      </svg>
      {hi && hoverIdx != null && tipPos != null && (
        <div
          className="ebb-chart-tooltip ebb-chart-tooltip--fixed"
          style={{
            left: tipPos.x,
            top: tipPos.y,
            transform: 'translateX(-50%)',
          }}
        >
          <div className="ebb-chart-tooltip-title">
            第 {hoverIdx + 1} 轮复习 · 间隔 {hi.interval_days} 天
          </div>
          <div className="ebb-chart-tooltip-row">
            <span className="ebb-dot" style={{ background: EBB_TARGET }} />
            标准遗忘参考（该轮）<strong>{Math.round(refForgettingPct(hoverIdx, n))}%</strong>
          </div>
          <div className="ebb-chart-tooltip-row">
            <span className="ebb-dot" style={{ background: EBB_ACTUAL }} />
            {hi.due_total > 0 ? (
              <>
                实际按时完成 <strong>{hi.actual_pct ?? 0}%</strong>
                <span className="ebb-chart-tooltip-sub">（{hi.due_met}/{hi.due_total} 词到期）</span>
              </>
            ) : (
              <span className="ebb-chart-tooltip-sub">该轮暂无到期样本</span>
            )}
          </div>
        </div>
      )}
      {!hasActual && (
        <p className="ebb-chart-note">当前各轮暂无到期样本，仅显示蓝线参考；有到期词后出现橙线。</p>
      )}
    </div>
  )
}

// ── SVG line chart ────────────────────────────────────────────────────────────

interface ChartProps {
  data: DailyLearning[]
  metric: MetricKey
  range: RangeKey
  compact?: boolean
}

function LearningChart({ data, metric, range, compact }: ChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{ idx: number; x: number; y: number } | null>(null)

  const W = 560
  const H = compact ? 118 : 160
  const padL = 44
  const padR = 12
  const padT = compact ? 8 : 12
  const padB = compact ? 24 : 32
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

  const allPts = segments.flat()
  let fillPoints = ''
  if (allPts.length > 0) {
    const firstX = parseFloat(allPts[0].split(',')[0])
    const lastX = parseFloat(allPts[allPts.length - 1].split(',')[0])
    const baseY = padT + innerH
    fillPoints = `${firstX},${baseY} ${allPts.join(' ')} ${lastX},${baseY}`
  }

  const ySteps = 4
  const yLabels = Array.from({ length: ySteps + 1 }, (_, i) => {
    const val = (yMax * i) / ySteps
    if (metric === 'accuracy') return `${Math.round(val)}%`
    if (metric === 'duration') return val >= 60 ? `${Math.round(val / 60)}h` : `${Math.round(val)}m`
    return `${Math.round(val)}`
  })

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
    <div className={`lc-wrap${compact ? ' lc-wrap--compact' : ''}`} onMouseLeave={() => setTooltip(null)}>
      <svg
        ref={svgRef}
        className="lc-svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={handleMouseMove}
      >
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

        {fillPoints && (
          <polygon points={fillPoints} fill="rgba(255, 126, 54, 0.10)" />
        )}

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

        {data.map((d, i) => {
          const v = getValue(d)
          if (v == null || (metric !== 'accuracy' && v === 0)) return null
          return (
            <circle
              key={i}
              cx={xOf(i)} cy={yOf(v)}
              r={tooltip?.idx === i ? 5 : 3}
              fill="var(--accent)"
              stroke="var(--bg-color)"
              strokeWidth={tooltip?.idx === i ? 2 : 0}
            />
          )
        })}

        {xLabels.map(({ i, label }) => (
          <text
            key={i}
            x={xOf(i)} y={H - 6}
            textAnchor="middle" fontSize="9" fill="var(--text-tertiary)"
          >
            {label}
          </text>
        ))}

        {tooltip && (
          <line
            x1={tooltip.x} y1={padT}
            x2={tooltip.x} y2={padT + innerH}
            stroke="var(--accent)" strokeWidth="1" strokeDasharray="3,2" opacity="0.5"
          />
        )}
      </svg>

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

/** 各模式统计表（可与模式占比并排，或单独成区） */
function ModeBreakdownTableBody({ modeBreakdown, onNavigate }: {
  modeBreakdown: ModeStat[]
  onNavigate: () => void
}) {
  if (modeBreakdown.length === 0) {
    return (
      <div className="stats-empty stats-empty--mode-strip">
        <p>完成练习后将显示各模式数据</p>
        <a className="stats-go-practice" onClick={onNavigate}>去练习 →</a>
      </div>
    )
  }
  return (
    <div className="mode-breakdown-table-wrap mode-breakdown-table-wrap--strip">
      <table className="stats-data-table stats-table--compact stats-table--mode-strip">
        <thead>
          <tr>
            <th>模式</th>
            <th title="速记：词表去重；其他模式：会话累计（可重复）">学习词数</th>
            <th>答题次数</th>
            <th>正确率</th>
            <th>练习</th>
            <th>场均</th>
            <th>时长</th>
          </tr>
        </thead>
        <tbody>
          {modeBreakdown.map(m => (
            <tr key={m.mode}>
              <td>{MODE_LABELS[m.mode] || m.mode}</td>
              <td>{m.words_studied}</td>
              <td>{m.attempts ?? (m.correct_count + m.wrong_count)}</td>
              <td>{fmtPct(m.accuracy)}</td>
              <td>{m.sessions}</td>
              <td>{m.avg_words_per_session ?? '--'}</td>
              <td>{m.duration_seconds > 0 ? fmtDuration(m.duration_seconds) : '--'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function StatsPage() {
  const navigate = useNavigate()
  const { words: wrongWords } = useWrongWords()

  const [range, setRange] = useState<RangeKey>(30)
  const [metric, setMetric] = useState<MetricKey>('words')
  const [bookId, setBookId] = useState('all')
  const [mode, setMode] = useState('all')

  const {
    daily,
    books,
    modes,
    summary,
    alltime,
    modeBreakdown,
    pieChart,
    wrongTop10,
    chapterBreakdown,
    chapterModeStats,
    useFallback,
    loading: chartLoading,
  } = useLearningStats(range, bookId, mode)

  const displayTodayDuration = alltime && alltime.today_duration_seconds > 0
    ? fmtDuration(alltime.today_duration_seconds) : '--'
  const displayAlltimeDuration = alltime && alltime.duration_seconds > 0
    ? fmtDuration(alltime.duration_seconds) : '--'

  const displayTotalNew = alltime?.total_words != null ? alltime.total_words : (chartLoading ? '…' : '--')
  const displayTodayNew = alltime?.today_new_words ?? (chartLoading ? '…' : '--')
  const displayTodayReview = alltime?.today_review_words ?? (chartLoading ? '…' : '--')
  const displayAlltimeReview = alltime?.alltime_review_words ?? (chartLoading ? '…' : '--')

  const displayTodayAccuracy = fmtPct(alltime?.today_accuracy)
  const displayAlltimeAccuracy = fmtPct(alltime?.accuracy)
  const displayStreak = alltime?.streak_days != null && alltime?.streak_days > 0
    ? alltime.streak_days : '--'

  const hasChartData = daily.some(d => {
    if (metric === 'words') return d.words_studied > 0
    if (metric === 'accuracy') return d.accuracy != null
    return d.duration_seconds > 0
  })

  const defaultEbbStages: EbbinghausStagePoint[] = [1, 1, 4, 7, 14, 30].map((interval_days, i) => ({
    stage: i,
    interval_days,
    due_total: 0,
    due_met: 0,
    actual_pct: null,
  }))
  const ebbStages =
    alltime?.ebbinghaus_stages && alltime.ebbinghaus_stages.length > 0
      ? alltime.ebbinghaus_stages
      : defaultEbbStages

  const statsMainLeftRef = useRef<HTMLDivElement>(null)
  const [statsWideLayout, setStatsWideLayout] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 901px)').matches,
  )
  const [statsRightHeightPx, setStatsRightHeightPx] = useState<number | undefined>(undefined)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 901px)')
    const onChange = () => setStatsWideLayout(mq.matches)
    mq.addEventListener('change', onChange)
    setStatsWideLayout(mq.matches)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const measureStatsLeftHeight = useCallback(() => {
    if (!statsWideLayout) {
      setStatsRightHeightPx(undefined)
      return
    }
    const el = statsMainLeftRef.current
    if (!el) return
    const h = Math.round(el.getBoundingClientRect().height)
    if (h > 0) setStatsRightHeightPx(h)
  }, [statsWideLayout])

  useLayoutEffect(() => {
    measureStatsLeftHeight()
  }, [
    measureStatsLeftHeight,
    chartLoading,
    wrongWords.length,
    wrongTop10.length,
    chapterBreakdown.length,
    chapterModeStats.length,
    hasChartData,
    range,
    metric,
  ])

  useLayoutEffect(() => {
    if (!statsWideLayout) return
    const el = statsMainLeftRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      measureStatsLeftHeight()
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [statsWideLayout, measureStatsLeftHeight])

  const statsRightColumnStyle: CSSProperties | undefined =
    statsWideLayout && statsRightHeightPx != null
      ? {
          height: statsRightHeightPx,
          maxHeight: statsRightHeightPx,
          minHeight: 0,
        }
      : undefined

  return (
    <div className="stats-page">
      <div className="page-content">

        <p className="stats-page-intro">
          「新词 / 复习」来自速记（艾宾浩斯）同步数据；「累计学习新词」为全书进度与去重逻辑综合结果。
        </p>

        <div className="stats-cards stats-cards-9">
          <div className="stats-card">
            <div className="stats-card-value">{displayTodayNew}</div>
            <div className="stats-card-label">今日学习新词数</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayTotalNew}</div>
            <div className="stats-card-label">累计学习新词数</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayTodayReview}</div>
            <div className="stats-card-label">今日复习旧词数</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayAlltimeReview}</div>
            <div className="stats-card-label">累计复习旧词数</div>
            <div className="stats-card-sub">至少 2 轮作答的词</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayTodayDuration}</div>
            <div className="stats-card-label">今日学习时长</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayAlltimeDuration}</div>
            <div className="stats-card-label">累计学习时长</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayTodayAccuracy}</div>
            <div className="stats-card-label">今日正确率</div>
            <div className="stats-card-sub">章节进度</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayAlltimeAccuracy}</div>
            <div className="stats-card-label">累计正确率</div>
            <div className="stats-card-sub">章节进度</div>
          </div>
          <div className="stats-card">
            <div className="stats-card-value">{displayStreak}</div>
            <div className="stats-card-label">连续学习</div>
            <div className="stats-card-sub">天</div>
          </div>
        </div>

        <div className="stats-section stats-section--mode-strip">
          <div className="stats-mode-strip-header">
            <h2 className="stats-section-title">模式占比与各模式统计</h2>
            {alltime?.weakest_mode && (
              <span className="mode-recommendation">
                建议加强：<strong>{MODE_LABELS[alltime.weakest_mode] || alltime.weakest_mode}</strong>
                {alltime.weakest_mode_accuracy != null && (
                  <span className="mode-recommendation-acc">（正确率 {alltime.weakest_mode_accuracy}%）</span>
                )}
              </span>
            )}
          </div>
          <p className="stats-section-hint">
            饼图与各模式「学习词数」：<strong>速记模式</strong>为速记词表去重词数（每词一行）；其余模式为练习会话累计（同一词多次练习会重复计）。各模式相加仍可能高于上方「累计学习新词数」——后者为全书章节进度与全局去重综合结果。
          </p>
          <div className="stats-mode-strip-grid">
            <h3 className="stats-mode-strip-title stats-mode-strip-title--pie">模式占比</h3>
            <h3 className="stats-mode-strip-title stats-mode-strip-title--modes">各模式统计</h3>
            <div className="stats-mode-strip-col stats-mode-strip-col--pie">
              {chartLoading ? (
                <div className="stats-chart-loading stats-chart-loading--strip"><div className="loading-spinner" /></div>
              ) : (
                <ModePieChart segments={pieChart} variant="strip" />
              )}
            </div>
            <div className="stats-mode-strip-col stats-mode-strip-col--modes">
              {chartLoading ? (
                <div className="stats-chart-loading stats-chart-loading--strip-table"><div className="loading-spinner" /></div>
              ) : (
                <ModeBreakdownTableBody modeBreakdown={modeBreakdown} onNavigate={() => navigate('/')} />
              )}
            </div>
          </div>
        </div>

        <div className="stats-main-layout-wrap">
          <div
            className={`stats-main-layout${statsWideLayout && statsRightHeightPx != null ? ' stats-main-layout--sync-left-height' : ''}`}
          >
            <div className="stats-main-left" ref={statsMainLeftRef}>
              <div className="stats-left-stack">
                    <section className="stats-section stats-card-wrong" aria-labelledby="stats-wrong-title">
                      <h2 id="stats-wrong-title" className="stats-section-title">重复出错 Top 10</h2>
                      <p className="stats-section-hint">错词本中累计错误次数最高的词汇（上图为错次占比，下表为明细）</p>
                      <div className="stats-card-wrong-body">
                        {chartLoading ? (
                          <div className="stats-chart-loading"><div className="loading-spinner" /></div>
                        ) : wrongTop10.length === 0 ? (
                          <div className="stats-empty"><p>暂无错词数据</p></div>
                        ) : (
                          <div className="stats-wrong-vertical">
                            <div className="stats-wrong-pie-block">
                              <h3 className="stats-subsection-title">错次占比（扇形图）</h3>
                              <WrongTopPieChart items={wrongTop10} />
                            </div>
                            <div className="stats-wrong-table-block">
                              <h3 className="stats-subsection-title">明细表</h3>
                              <div className="stats-wrong-table-scroll">
                                <table className="stats-data-table">
                                  <thead>
                                    <tr>
                                      <th>序号</th>
                                      <th>单词</th>
                                      <th>音标</th>
                                      <th>累计错次</th>
                                      <th>错因</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {wrongTop10.map((w, i) => (
                                      <tr key={w.word + i}>
                                        <td>{i + 1}</td>
                                        <td className="td-word">{w.word}</td>
                                        <td className="td-muted">{w.phonetic || '—'}</td>
                                        <td><span className="wrong-count-badge">{w.wrong_count}</span></td>
                                        <td><span className="error-reason-tag">{inferErrorReason(w)}</span></td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </section>

                    <section className="stats-section stats-card-wrong-overview" aria-labelledby="stats-wrong-overview-title">
                      <h2 id="stats-wrong-overview-title" className="stats-section-title">错词本概览</h2>
                      <div className="stats-wrong-summary">
                        <div className="stats-wrong-count">
                          <span className="wrong-num">{wrongWords.length}</span>
                          <span className="wrong-label">个错词</span>
                        </div>
                        {wrongWords.length > 0 && (
                          <button type="button" className="stats-review-btn" onClick={() => navigate('/errors')}>
                            查看错词本 →
                          </button>
                        )}
                      </div>
                    </section>
              </div>
            </div>
            <div className="stats-main-right" style={statsRightColumnStyle}>
              <div className="stats-main-right-top">
                <div className="stats-main-cell stats-main-cell--ebb">
                    <section className="stats-section stats-card-ebbinghaus" aria-labelledby="stats-ebb-title">
                      <h2 id="stats-ebb-title" className="stats-section-title">艾宾浩斯复习达成</h2>
                      <p className="stats-section-hint stats-ebb-hint-compact">
                        衡量「到期是否按时复习」：蓝虚线为艾宾浩斯标准遗忘曲线（理论参考折线）；橙实线为各轮实际按时完成度。橙线整体高于蓝线，说明按时复习对抗遗忘的效果越好。
                      </p>
                      <div className="stats-ebb-inner">
                        {chartLoading ? (
                          <div className="stats-chart-loading stats-chart-loading--ebb-split"><div className="loading-spinner" /></div>
                        ) : (
                          <>
                            <div className="ebbinghaus-summary-row ebbinghaus-summary-row--compact ebbinghaus-summary-row--split">
                              <div
                                className={`ebbinghaus-big ebbinghaus-big--compact ${ebbRateToneClass(alltime?.ebbinghaus_rate)}`}
                              >
                                {fmtPct(alltime?.ebbinghaus_rate)}
                              </div>
                              <div className="ebbinghaus-meta ebbinghaus-meta--compact">
                                <span className="ebb-meta-item">
                                  <span className="ebb-meta-label">到期</span>
                                  <span className="ebb-meta-num">{alltime?.ebbinghaus_due_total ?? 0}</span>
                                </span>
                                <span className="ebb-meta-item">
                                  <span className="ebb-meta-label">已按时</span>
                                  <span className="ebb-meta-num">{alltime?.ebbinghaus_met ?? 0}</span>
                                </span>
                                <span className="ebb-meta-item">
                                  <span className="ebb-meta-label">词库</span>
                                  <span className="ebb-meta-num">{alltime?.qm_word_total ?? 0}</span>
                                </span>
                              </div>
                            </div>
                            {(alltime?.upcoming_reviews_3d ?? 0) > 0 && (
                              <div className="ebb-upcoming-hint">
                                <span>接下来3天待复习 <strong>{alltime?.upcoming_reviews_3d}</strong> 词</span>
                                <button
                                  type="button"
                                  className="stats-review-btn stats-review-btn--ebb"
                                  onClick={() => navigate('/')}
                                >
                                  去复习
                                </button>
                              </div>
                            )}
                            <div className="stats-ebb-chart-wrap">
                              <EbbinghausDualChart stages={ebbStages} compact />
                            </div>
                          </>
                        )}
                      </div>
                    </section>
                </div>
                <div className="stats-main-cell stats-main-cell--learning">
                    <section className="stats-section stats-section--learning" aria-labelledby="stats-learning-title">
                      <div className="stats-section-header stats-learning-split-head">
                        <h2 id="stats-learning-title" className="stats-section-title">学习记录</h2>
                        <div className="lc-tabs">
                          {RANGE_OPTIONS.map(o => (
                            <button
                              key={o.value}
                              type="button"
                              className={`lc-tab${range === o.value ? ' active' : ''}`}
                              onClick={() => setRange(o.value)}
                            >
                              {o.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="lc-filters lc-filters--compact">
                        <div className="lc-metric-tabs">
                          {METRIC_OPTIONS.map(o => (
                            <button
                              key={o.value}
                              type="button"
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

                      {chartLoading ? (
                        <div className="stats-chart-loading stats-chart-loading--learn-split"><div className="loading-spinner" /></div>
                      ) : !hasChartData ? (
                        <div className="stats-empty stats-empty--compact">
                          <p>该时间段暂无学习记录</p>
                          <a className="stats-go-practice" onClick={() => navigate('/')}>去练习 →</a>
                        </div>
                      ) : (
                        <LearningChart data={daily} metric={metric} range={range} compact />
                      )}

                      {!chartLoading && hasChartData && summary && (
                        <div className="lc-legend-row lc-legend-row--compact">
                          <div className="lc-legend">
                            <span className="lc-crosshair-legend" title="悬停图表时显示">
                              <i className="lc-crosshair-icon" aria-hidden />
                              悬停所选日期
                            </span>
                            <span className="lc-legend-sep" aria-hidden>
                              ·
                            </span>
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
                          {alltime?.trend_direction && alltime?.trend_direction !== 'stable' && (
                            <div className="lc-trend-insight">
                              <span className={`lc-trend-badge lc-trend-badge--${alltime.trend_direction}`}>
                                {alltime.trend_direction === 'improving' ? '↑' : '↓'}
                              </span>
                              <span>
                                {alltime.trend_direction === 'improving'
                                  ? '学习效果在提升'
                                  : '学习效果有下滑，建议加强复习'}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </section>
                </div>
              </div>
              <div className="stats-main-right-bottom">
                <div className="stats-main-cell stats-main-cell--chapter">
                    <section className="stats-section stats-section--chapter-cell" aria-labelledby="stats-chapter-detail-title">
                      <h2 id="stats-chapter-detail-title" className="stats-section-title">章节正确率（细项）</h2>
                      <p className="stats-section-hint">按章节汇总的答题与词数</p>
                      {chartLoading ? (
                        <div className="stats-chart-loading"><div className="loading-spinner" /></div>
                      ) : chapterBreakdown.length === 0 ? (
                        <div className="stats-empty stats-empty--chapter-cell">
                          <p>暂无章节数据</p>
                          <a className="stats-go-practice" onClick={() => navigate('/')}>去练习 →</a>
                        </div>
                      ) : (
                        <div className="mode-breakdown-table-wrap stats-table-scroll--in-cell">
                          <table className="stats-data-table stats-table--compact">
                            <thead>
                              <tr>
                                <th>词书</th>
                                <th>章节</th>
                                <th>已学词数</th>
                                <th>答对</th>
                                <th>答错</th>
                                <th>正确率</th>
                              </tr>
                            </thead>
                            <tbody>
                              {chapterBreakdown.map(row => (
                                <tr key={`${row.book_id}-${row.chapter_id}`}>
                                  <td>{row.book_title}</td>
                                  <td>{row.chapter_title}</td>
                                  <td>{row.words_learned}</td>
                                  <td>{row.correct}</td>
                                  <td>{row.wrong}</td>
                                  <td>{fmtPct(row.accuracy)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </section>
                </div>
                <div className="stats-main-cell stats-main-cell--chapter-mode">
                    <section className="stats-section stats-section--chapter-cell" aria-labelledby="stats-chapter-mode-title">
                      <h2 id="stats-chapter-mode-title" className="stats-section-title">章节 × 模式 正确率</h2>
                      <p className="stats-section-hint">同一章节在不同练习模式下的正确率（独立统计）</p>
                      {chartLoading ? (
                        <div className="stats-chart-loading"><div className="loading-spinner" /></div>
                      ) : chapterModeStats.length === 0 ? (
                        <div className="stats-empty stats-empty--chapter-cell"><p>暂无分模式章节数据</p></div>
                      ) : (
                        <div className="mode-breakdown-table-wrap stats-table-scroll--in-cell">
                          <table className="stats-data-table stats-table--compact">
                            <thead>
                              <tr>
                                <th>词书</th>
                                <th>章节</th>
                                <th>模式</th>
                                <th>答对</th>
                                <th>答错</th>
                                <th>正确率</th>
                              </tr>
                            </thead>
                            <tbody>
                              {chapterModeStats.map((row, i) => (
                                <tr key={`${row.book_id}-${row.chapter_id}-${row.mode}-${i}`}>
                                  <td>{row.book_title}</td>
                                  <td>{row.chapter_title}</td>
                                  <td>{MODE_LABELS[row.mode] || row.mode}</td>
                                  <td>{row.correct}</td>
                                  <td>{row.wrong}</td>
                                  <td>{row.accuracy}%</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </section>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
