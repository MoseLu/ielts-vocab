import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface ProgressData {
  day: number
  correct_count: number
}

interface ChartDataPoint {
  day: number
  learned: number
}

interface StudySession {
  date: string
  duration: number
}

interface DayProgress {
  updatedAt?: string
  correctCount?: number
}

interface BookProgressData {
  title?: string
  correctCount?: number
  wrongCount?: number
  totalWords?: number
}

interface ChapterStat {
  bookId: string
  title: string
  correct: number
  wrong: number
  total: number
  accuracy: number | null
}

export default function StatsPage() {
  const navigate = useNavigate()
  const [progressData, setProgressData] = useState<ProgressData[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      fetch('/api/progress', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => res.json())
        .then((data: ProgressData[] | unknown) => {
          setProgressData(Array.isArray(data) ? data : [])
          setLoading(false)
        })
        .catch(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  // Compute stats from localStorage + API
  const wrongWords: unknown[] = (() => {
    try { return JSON.parse(localStorage.getItem('wrong_words') || '[]') } catch { return [] }
  })()

  const dayProgress: Record<number, DayProgress> = (() => {
    try { return JSON.parse(localStorage.getItem('day_progress') || '{}') } catch { return {} }
  })()

  const bookProgress: unknown[] = (() => {
    try { return JSON.parse(localStorage.getItem('my_books') || '[]') } catch { return [] }
  })()

  // Calculate today's stats
  const today = new Date().toISOString().slice(0, 10)
  const todayWords = Object.values(dayProgress).reduce<number>((sum, d) => {
    if (d.updatedAt && d.updatedAt.slice(0, 10) === today) {
      return sum + (d.correctCount || 0)
    }
    return sum
  }, 0)

  // Total learned words (correct counts across all days)
  const totalWords = progressData.reduce((sum, p) => sum + (p.correct_count || 0), 0)

  // Total session time from localStorage (in minutes)
  const sessions: StudySession[] = (() => {
    try { return JSON.parse(localStorage.getItem('study_sessions') || '[]') } catch { return [] }
  })()
  const todayTime = sessions
    .filter(s => s.date === today)
    .reduce((sum, s) => sum + (s.duration || 0), 0)
  const totalTime = sessions.reduce((sum, s) => sum + (s.duration || 0), 0)

  // Build chart data — 30 days
  const chartData: ChartDataPoint[] = Array.from({ length: 30 }, (_, i) => {
    const dayNum = i + 1
    const fromApi = progressData.find(p => p.day === dayNum)
    const fromLocal = dayProgress[dayNum]
    const learned = fromApi ? fromApi.correct_count : (fromLocal ? fromLocal.correctCount ?? 0 : 0)
    return { day: dayNum, learned }
  })

  const maxLearned = Math.max(...chartData.map(d => d.learned), 10)

  // Chapter accuracy from book progress stored in localStorage
  const allBookProgress: Record<string, BookProgressData> = (() => {
    try { return JSON.parse(localStorage.getItem('all_book_progress') || '{}') } catch { return {} }
  })()

  const chapterStats: ChapterStat[] = Object.entries(allBookProgress).map(([bookId, data]) => ({
    bookId,
    title: data.title || bookId,
    correct: data.correctCount || 0,
    wrong: data.wrongCount || 0,
    total: data.totalWords || 0,
    accuracy: data.correctCount && data.wrongCount
      ? Math.round((data.correctCount / (data.correctCount + data.wrongCount)) * 100)
      : null
  })).filter(s => s.correct + s.wrong > 0)

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

  // Fill area
  const firstX = padL
  const lastX = padL + innerW
  const baseY = padT + innerH
  const fillPoints = `${firstX},${baseY} ${points} ${lastX},${baseY}`

  return (
    <div className="stats-page">
      <h1 className="stats-title">学习统计</h1>

      {/* Top stat cards */}
      <div className="stats-cards">
        <div className="stats-card">
          <div className="stats-card-value">{todayWords}</div>
          <div className="stats-card-label">今日学习词数</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-value">{formatTime(todayTime)}</div>
          <div className="stats-card-label">今日时长</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-value">{totalWords}</div>
          <div className="stats-card-label">累计学习词数</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-value">{formatTime(totalTime)}</div>
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
  )
}

