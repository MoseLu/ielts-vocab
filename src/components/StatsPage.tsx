import { useNavigate } from 'react-router-dom'
import { useStats, useWrongWords } from '../features/vocabulary/hooks'

export default function StatsPage() {
  const navigate = useNavigate()
  const { todayWords, totalWords, chartData, maxLearned, chapterStats, loading } = useStats()
  const { words: wrongWords } = useWrongWords()

  const formatTime = (mins: number): string => {
    if (!mins) return '0分钟'
    if (mins < 60) return `${mins}分钟`
    return `${Math.floor(mins / 60)}小时${mins % 60 ? mins % 60 + '分钟' : ''}`
  }

  // SVG chart dimensions
  const chartW = 600
  const chartH = 120
  const padL = 10
  const padR = 10
  const padT = 10
  const padB = 20
  const innerW = chartW - padL - padR
  const innerH = chartH - padT - padB

  const points = chartData.map((d, i) => {
    const x = padL + (i / (chartData.length - 1)) * innerW
    const y = padT + innerH - (d.learned / maxLearned) * innerH
    return `${x},${y}`
  }).join(' ')

  const firstX = padL
  const lastX = padL + innerW
  const baseY = padT + innerH
  const fillPoints = `${firstX},${baseY} ${points} ${lastX},${baseY}`

  return (
    <div className="stats-page">
      <div className="page-content">
      {/* Top stat cards */}
      <div className="stats-cards">
        <div className="stats-card">
          <div className="stats-card-value">{todayWords}</div>
          <div className="stats-card-label">今日学习词数</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-value">{formatTime(0)}</div>
          <div className="stats-card-label">今日时长</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-value">{totalWords}</div>
          <div className="stats-card-label">累计学习词数</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-value">{formatTime(0)}</div>
          <div className="stats-card-label">累计时长</div>
        </div>
      </div>

      {/* Learning chart */}
      <div className="stats-section">
        <h2 className="stats-section-title">学习记录</h2>
        <div className="stats-chart-wrap">
          {loading ? (
            <div className="stats-chart-loading"><div className="loading-spinner"></div></div>
          ) : (
            <svg
              className="stats-chart-svg"
              viewBox={`0 0 ${chartW} ${chartH}`}
              preserveAspectRatio="none"
            >
              {/* Grid lines */}
              {[0.25, 0.5, 0.75, 1].map(ratio => (
                <line
                  key={ratio}
                  x1={padL} y1={padT + innerH - ratio * innerH}
                  x2={padL + innerW} y2={padT + innerH - ratio * innerH}
                  stroke="var(--border)" strokeWidth="0.5"
                />
              ))}

              {/* Fill area */}
              <polygon
                points={fillPoints}
                fill="rgba(255, 126, 54, 0.12)"
              />

              {/* Line */}
              <polyline
                points={points}
                fill="none"
                stroke="var(--accent)"
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
              />

              {/* Data dots */}
              {chartData.map((d, i) => {
                if (!d.learned) return null
                const x = padL + (i / (chartData.length - 1)) * innerW
                const y = padT + innerH - (d.learned / maxLearned) * innerH
                return <circle key={i} cx={x} cy={y} r="3" fill="var(--accent)" />
              })}

              {/* X axis labels (every 5 days) */}
              {chartData.filter((_, i) => i % 5 === 0 || i === 29).map((d, idx, arr) => {
                const origIdx = idx === arr.length - 1 ? 29 : idx * 5
                const x = padL + (origIdx / (chartData.length - 1)) * innerW
                return (
                  <text
                    key={origIdx}
                    x={x}
                    y={chartH - 4}
                    textAnchor="middle"
                    fontSize="9"
                    fill="var(--text-tertiary)"
                  >
                    Day {d.day}
                  </text>
                )
              })}
            </svg>
          )}
        </div>
        <div className="stats-chart-legend">
          <span className="legend-dot" style={{ background: 'var(--accent)' }}></span>
          <span>学习词数</span>
        </div>
      </div>

      {/* Chapter accuracy */}
      <div className="stats-section">
        <h2 className="stats-section-title">章节正确率</h2>
        {chapterStats.length === 0 ? (
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
