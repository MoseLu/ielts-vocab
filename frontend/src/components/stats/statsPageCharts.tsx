import { useEffect, useLayoutEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import type { EbbinghausStagePoint, PieSegment } from '../../features/vocabulary/hooks'
import { fmtDate, fmtDuration, MODE_LABELS, type ChartProps, type WrongTopDisplayItem } from './statsPageCore'

const PIE_COLORS = ['var(--chart-series-1)', 'var(--chart-series-2)', 'var(--chart-series-3)', 'var(--chart-series-4)', 'var(--chart-series-5)', 'var(--chart-series-6)', 'var(--chart-series-7)', 'var(--chart-series-8)']
const PIE_COLOR_CLASSES = ['stats-pie-dot--0', 'stats-pie-dot--1', 'stats-pie-dot--2', 'stats-pie-dot--3', 'stats-pie-dot--4', 'stats-pie-dot--5', 'stats-pie-dot--6', 'stats-pie-dot--7']
const WRONG_PIE_COLORS = ['var(--chart-wrong-1)', 'var(--chart-wrong-2)', 'var(--chart-wrong-3)', 'var(--chart-wrong-4)', 'var(--chart-wrong-5)', 'var(--chart-wrong-6)', 'var(--chart-wrong-7)', 'var(--chart-wrong-8)', 'var(--chart-wrong-9)', 'var(--chart-wrong-10)']
const WRONG_PIE_COLOR_CLASSES = ['stats-pie-dot--wrong-0', 'stats-pie-dot--wrong-1', 'stats-pie-dot--wrong-2', 'stats-pie-dot--wrong-3', 'stats-pie-dot--wrong-4', 'stats-pie-dot--wrong-5', 'stats-pie-dot--wrong-6', 'stats-pie-dot--wrong-7', 'stats-pie-dot--wrong-8', 'stats-pie-dot--wrong-9']
const EBB_TARGET = 'var(--chart-ebb-target)'
const EBB_ACTUAL = 'var(--chart-ebb-actual)'
const EBB_STANDARD_FORGETTING_REF: readonly number[] = [100, 92, 78, 65, 52, 42]
const EBB_TIP_HALF_W = 112

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

export function ModePieChart({ segments, variant = 'card' }: { segments: PieSegment[]; variant?: 'card' | 'strip' }) {
  const total = segments.reduce((sum, item) => sum + item.value, 0)
  if (total <= 0) return <div className="stats-pie-empty">暂无模式分布（需有带模式的练习会话）</div>

  const cx = 70
  const cy = 70
  const r = 58
  let angle = -Math.PI / 2
  const paths: ReactNode[] = []
  segments.forEach((seg, index) => {
    const a = (seg.value / total) * 2 * Math.PI
    const x1 = cx + r * Math.cos(angle)
    const y1 = cy + r * Math.sin(angle)
    angle += a
    const x2 = cx + r * Math.cos(angle)
    const y2 = cy + r * Math.sin(angle)
    const large = a > Math.PI ? 1 : 0
    paths.push(
      <path
        key={`${seg.mode}-${index}`}
        d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`}
        fill={PIE_COLORS[index % PIE_COLORS.length]}
        stroke="var(--bg-color)"
        strokeWidth="1.5"
      />,
    )
  })

  const wrapClass = variant === 'strip' ? 'stats-pie-wrap stats-pie-wrap--strip' : 'stats-pie-wrap stats-pie-wrap--mode'
  const svgClass = variant === 'strip' ? 'stats-pie-svg stats-pie-svg--strip' : 'stats-pie-svg stats-pie-svg--sm'
  const legendClass = variant === 'strip' ? 'stats-pie-legend stats-pie-legend--strip' : 'stats-pie-legend stats-pie-legend--compact'

  return (
    <div className={wrapClass}>
      <svg className={svgClass} viewBox="0 0 140 140" aria-hidden>
        {paths}
      </svg>
      <ul className={legendClass}>
        {segments.map((seg, index) => (
          <li key={seg.mode}>
            <span className={`stats-pie-dot ${PIE_COLOR_CLASSES[index % PIE_COLOR_CLASSES.length]}`} />
            <span className="stats-pie-label">{MODE_LABELS[seg.mode] || seg.mode}</span>
            <span className="stats-pie-val">{Math.round((seg.value / total) * 100)}%</span>
            <span className="stats-pie-sub">{seg.value} 词</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function WrongTopPieChart({ items }: { items: WrongTopDisplayItem[] }) {
  const total = items.reduce((sum, item) => sum + item.wrong_count, 0)
  if (total <= 0) return <div className="stats-pie-empty">暂无错词分布</div>

  const cx = 70
  const cy = 70
  const r = 58
  let angle = -Math.PI / 2
  const paths: ReactNode[] = []
  items.forEach((seg, index) => {
    const a = (seg.wrong_count / total) * 2 * Math.PI
    const x1 = cx + r * Math.cos(angle)
    const y1 = cy + r * Math.sin(angle)
    angle += a
    const x2 = cx + r * Math.cos(angle)
    const y2 = cy + r * Math.sin(angle)
    const large = a > Math.PI ? 1 : 0
    paths.push(
      <path
        key={`${seg.word}-${index}`}
        d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`}
        fill={WRONG_PIE_COLORS[index % WRONG_PIE_COLORS.length]}
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
        {items.map((item, index) => (
          <li key={`${item.word}-${index}`}>
            <span className={`stats-pie-dot ${WRONG_PIE_COLOR_CLASSES[index % WRONG_PIE_COLOR_CLASSES.length]}`} />
            <span className="stats-pie-label" title={item.word}>
              {item.word.length > 14 ? `${item.word.slice(0, 13)}…` : item.word}
            </span>
            <span className="stats-pie-val">{Math.round((item.wrong_count / total) * 100)}%</span>
            <span className="stats-pie-sub">{item.wrong_count} 次</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function EbbinghausDualChart({ stages, compact }: { stages: EbbinghausStagePoint[]; compact?: boolean }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
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
  const xOf = (index: number) => padL + (n <= 1 ? innerW / 2 : (index / (n - 1)) * innerW)
  const yOf = (pct: number) => padT + innerH - (pct / 100) * innerH

  const targetPts = stages.map((_, index) => `${xOf(index)},${yOf(refForgettingPct(index, n))}`).join(' ')
  const actualSegments: string[] = []
  let cur: string[] = []
  stages.forEach((stage, index) => {
    if (stage.actual_pct != null && stage.due_total > 0) {
      cur.push(`${xOf(index)},${yOf(stage.actual_pct)}`)
    } else if (cur.length > 0) {
      actualSegments.push(cur.join(' '))
      cur = []
    }
  })
  if (cur.length > 0) actualSegments.push(cur.join(' '))

  const hasActual = stages.some(stage => stage.due_total > 0 && stage.actual_pct != null)
  const stageLabel = (stage: EbbinghausStagePoint) => `${stage.interval_days}d`

  const onMove = (event: MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const svgX = ((event.clientX - rect.left) / rect.width) * W
    let bestIndex = 0
    let minDistance = Infinity
    stages.forEach((_, index) => {
      const distance = Math.abs(xOf(index) - svgX)
      if (distance < minDistance) {
        minDistance = distance
        bestIndex = index
      }
    })
    const threshold = innerW / Math.max((stages.length - 1) * 2, 6)
    const hit = minDistance < threshold ? bestIndex : null
    setHoverIdx(hit)
    if (hit != null) {
      const vw = typeof window !== 'undefined' ? window.innerWidth : 1200
      const x = Math.min(Math.max(event.clientX, EBB_TIP_HALF_W + 6), vw - EBB_TIP_HALF_W - 6)
      setTipPos({ x, y: rect.top + 4 })
    } else {
      setTipPos(null)
    }
  }

  const hi = hoverIdx != null ? stages[hoverIdx] : null

  useEffect(() => {
    const tooltipEl = tooltipRef.current
    if (!tooltipEl || !tipPos) return
    tooltipEl.style.setProperty('--ebb-tooltip-left', `${tipPos.x}px`)
    tooltipEl.style.setProperty('--ebb-tooltip-top', `${tipPos.y}px`)
  }, [tipPos])

  return (
    <div className={`ebb-chart-wrap${compact ? ' ebb-chart-wrap--compact' : ''}`} onMouseLeave={() => { setHoverIdx(null); setTipPos(null) }}>
      <svg ref={svgRef} className="ebb-chart-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" onMouseMove={onMove}>
        {[0, 25, 50, 75, 100].map(pct => (
          <g key={pct}>
            <line x1={padL} y1={yOf(pct)} x2={W - padR} y2={yOf(pct)} stroke="var(--border)" strokeWidth="1" strokeDasharray={pct === 0 || pct === 100 ? '0' : '4 4'} opacity={0.7} />
            <text x={padL - 4} y={yOf(pct) + 4} textAnchor="end" fontSize="9" fill="var(--text-tertiary)">{pct}%</text>
          </g>
        ))}
        <polyline fill="none" stroke={EBB_TARGET} strokeWidth="2.5" strokeDasharray="8 5" points={targetPts} />
        {actualSegments.map((pts, index) => <polyline key={index} fill="none" stroke={EBB_ACTUAL} strokeWidth="2.5" points={pts} />)}
        {stages.map((stage, index) => (
          <g key={stage.stage}>
            <circle cx={xOf(index)} cy={yOf(refForgettingPct(index, n))} r="4" fill={EBB_TARGET} opacity={0.95} />
            {stage.actual_pct != null && stage.due_total > 0 && <circle cx={xOf(index)} cy={yOf(stage.actual_pct)} r="5" fill={EBB_ACTUAL} stroke="var(--bg-color)" strokeWidth="1.5" />}
            <text x={xOf(index)} y={H - 6} textAnchor="middle" fontSize="9" fill="var(--text-tertiary)">{stageLabel(stage)}</text>
          </g>
        ))}
      </svg>
      {hi && hoverIdx != null && tipPos != null && (
        <div ref={tooltipRef} className="ebb-chart-tooltip ebb-chart-tooltip--fixed">
          <div className="ebb-chart-tooltip-title">第 {hoverIdx + 1} 轮复习 · 间隔 {hi.interval_days} 天</div>
          <div className="ebb-chart-tooltip-row">
            <span className="ebb-dot ebb-dot--target" />
            标准遗忘参考（该轮）<strong>{Math.round(refForgettingPct(hoverIdx, n))}%</strong>
          </div>
          <div className="ebb-chart-tooltip-row">
            <span className="ebb-dot ebb-dot--actual" />
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
      {!hasActual && <p className="ebb-chart-note">当前各轮暂无到期样本，仅显示蓝线参考；有到期词后出现橙线。</p>}
    </div>
  )
}

export function LearningChart({ data, metric, range, compact }: ChartProps) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<{ idx: number; x: number; y: number } | null>(null)
  const [chartSize, setChartSize] = useState<{ width: number; height: number }>({
    width: 560,
    height: compact ? 180 : 160,
  })

  const W = chartSize.width
  const H = chartSize.height
  const padL = 44
  const padR = 12
  const padT = compact ? 8 : 12
  const padB = compact ? 24 : 32
  const innerW = W - padL - padR
  const innerH = H - padT - padB

  useLayoutEffect(() => {
    const wrapEl = wrapRef.current
    if (!wrapEl) return

    const syncChartSize = () => {
      const nextWidth = Math.max(Math.round(wrapEl.clientWidth), 320)
      const nextHeight = compact
        ? Math.max(Math.round(wrapEl.clientHeight), 180)
        : 160

      setChartSize(prev => (
        prev.width === nextWidth && prev.height === nextHeight
          ? prev
          : { width: nextWidth, height: nextHeight }
      ))
    }

    syncChartSize()

    const resizeObserver = new ResizeObserver(syncChartSize)
    resizeObserver.observe(wrapEl)
    window.addEventListener('resize', syncChartSize)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', syncChartSize)
    }
  }, [compact])

  const getValue = (item: any): number | null => {
    if (metric === 'words') return item.words_studied
    if (metric === 'accuracy') return item.accuracy
    if (metric === 'duration') return item.duration_seconds > 0 ? Math.round(item.duration_seconds / 60) : 0
    return null
  }
  const isChartPointVisible = (value: number | null): boolean => {
    if (value == null) return false
    return metric === 'accuracy' || value > 0
  }

  const values = data.map(getValue)
  const validValues = values.filter((value): value is number => isChartPointVisible(value))
  const maxVal = validValues.length > 0 ? Math.max(...validValues) : (metric === 'accuracy' ? 100 : 10)
  const yMax = metric === 'accuracy' ? 100 : maxVal === 0 ? 10 : Math.ceil(maxVal * 1.15)

  const xOf = (index: number) => padL + (data.length <= 1 ? innerW / 2 : (index / (data.length - 1)) * innerW)
  const yOf = (value: number | null) => value == null ? padT + innerH : padT + innerH - (value / yMax) * innerH

  const segments: string[][] = []
  let cur: string[] = []
  data.forEach((item, index) => {
    const value = getValue(item)
    if (isChartPointVisible(value)) {
      cur.push(`${xOf(index)},${yOf(value)}`)
    } else if (cur.length > 0) {
      segments.push(cur)
      cur = []
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
  const yLabels = Array.from({ length: ySteps + 1 }, (_, index) => {
    const val = (yMax * index) / ySteps
    if (metric === 'accuracy') return `${Math.round(val)}%`
    if (metric === 'duration') return val >= 60 ? `${Math.round(val / 60)}h` : `${Math.round(val)}m`
    return `${Math.round(val)}`
  })

  const xStep = range === 7 ? 1 : range === 14 ? 2 : 5
  const xLabels = data.reduce<{ i: number; label: string }[]>((acc, item, index) => {
    if (index % xStep === 0 || index === data.length - 1) {
      acc.push({ i: index, label: fmtDate(item.date, range) })
    }
    return acc
  }, [])

  const handleMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const svgX = ((event.clientX - rect.left) / rect.width) * W
    let closest = 0
    let minDist = Infinity
    data.forEach((_, index) => {
      const dx = Math.abs(xOf(index) - svgX)
      if (dx < minDist) {
        minDist = dx
        closest = index
      }
    })
    if (minDist < innerW / data.length + 4) {
      const value = getValue(data[closest])
      setTooltip({ idx: closest, x: xOf(closest), y: yOf(value) })
    } else {
      setTooltip(null)
    }
  }

  const tooltipData = tooltip != null ? data[tooltip.idx] : null
  const tooltipVal = tooltipData ? getValue(tooltipData) : null
  const tooltipLabel = tooltipVal == null
    ? '--'
    : metric === 'accuracy'
      ? `${tooltipVal}%`
      : metric === 'duration'
        ? fmtDuration(tooltipData?.duration_seconds ?? 0)
        : `${tooltipVal} 词`

  useEffect(() => {
    const tooltipEl = tooltipRef.current
    if (!tooltipEl || !tooltip) return
    tooltipEl.style.setProperty('--lc-tooltip-left', `${(tooltip.x / W) * 100}%`)
    tooltipEl.style.setProperty('--lc-tooltip-top', `${((tooltip.y - padT) / (H - padT - padB)) * 100}%`)
  }, [tooltip, W, H, padT, padB])

  return (
    <div ref={wrapRef} className={`lc-wrap${compact ? ' lc-wrap--compact' : ''}`} onMouseLeave={() => setTooltip(null)}>
      <svg ref={svgRef} className="lc-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" onMouseMove={handleMouseMove}>
        {Array.from({ length: ySteps + 1 }, (_, index) => {
          const ratio = index / ySteps
          const y = padT + innerH - ratio * innerH
          return (
            <g key={index}>
              <line x1={padL} y1={y} x2={padL + innerW} y2={y} stroke="var(--border)" strokeWidth="0.5" strokeDasharray={index === 0 ? undefined : '3,3'} />
              <text x={padL - 4} y={y + 4} textAnchor="end" fontSize="9" fill="var(--text-tertiary)">{yLabels[index]}</text>
            </g>
          )
        })}
        {fillPoints && <polygon points={fillPoints} fill="var(--chart-accent-fill)" />}
        {segments.map((segment, index) => (
          <polyline key={index} points={segment.join(' ')} fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {data.map((item, index) => {
          const value = getValue(item)
          if (!isChartPointVisible(value)) return null
          return (
            <circle
              key={index}
              cx={xOf(index)}
              cy={yOf(value)}
              r={tooltip?.idx === index ? 5 : 3}
              fill="var(--accent)"
              stroke="var(--bg-color)"
              strokeWidth={tooltip?.idx === index ? 2 : 0}
            />
          )
        })}
        {xLabels.map(({ i, label }) => (
          <text key={i} x={xOf(i)} y={H - 6} textAnchor="middle" fontSize="9" fill="var(--text-tertiary)">
            {label}
          </text>
        ))}
        {tooltip && <line x1={tooltip.x} y1={padT} x2={tooltip.x} y2={padT + innerH} stroke="var(--accent)" strokeWidth="1" strokeDasharray="3,2" opacity="0.5" />}
      </svg>
      {tooltip && tooltipData && (
        <div ref={tooltipRef} className="lc-tooltip">
          <div className="lc-tooltip-date">{tooltipData.date}</div>
          <div className="lc-tooltip-val">{tooltipLabel}</div>
          {metric !== 'accuracy' && tooltipData.sessions > 0 && <div className="lc-tooltip-sub">{tooltipData.sessions} 次练习</div>}
          {metric === 'words' && tooltipData.sessions > 0 && <div className="lc-tooltip-sub">{tooltipData.accuracy != null ? `正确率 ${tooltipData.accuracy}%` : ''}</div>}
        </div>
      )}
    </div>
  )
}
