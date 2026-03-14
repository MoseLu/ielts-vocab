import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function HomePage({ user, currentDay, onDayChange }) {
  const navigate = useNavigate()
  const [progress, setProgress] = useState({})
  const [activeSection, setActiveSection] = useState('learn')

  useEffect(() => {
    const savedProgress = localStorage.getItem('day_progress')
    if (savedProgress) {
      try { setProgress(JSON.parse(savedProgress)) } catch (e) {}
    }
  }, [])

  const handleDayClick = (day) => {
    onDayChange(day)
    navigate('/practice')
  }

  const completedDays = Object.entries(progress).filter(([, p]) => p.completed).length
  const totalWords = completedDays * 100
  const overallPct = Math.round(completedDays / 30 * 100)
  const wrongWords = JSON.parse(localStorage.getItem('wrong_words') || '[]')

  const tabs = [
    { key: 'learn', label: '今日学习' },
    { key: 'review', label: '复习计划' },
    { key: 'wrong', label: wrongWords.length > 0 ? `错词本 · ${wrongWords.length}` : '错词本' },
    { key: 'stats', label: '学习统计' },
  ]

  return (
    <div className="home-page">

      {/* Banner */}
      <div className="home-banner">
        <div className="home-banner-left">
          <div className="home-banner-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
            </svg>
            IELTS Vocabulary · 30天计划
          </div>
          <h1 className="home-welcome">你好，{user?.username || '同学'}</h1>
          <p className="home-subtitle">
            {completedDays === 0
              ? '每天100词，30天掌握3000核心词汇，从今天开始'
              : completedDays < 30
              ? `已坚持 ${completedDays} 天，还剩 ${30 - completedDays} 天，继续保持！`
              : '恭喜完成全部30天学习计划！'}
          </p>
          <div className="home-stats-row">
            <div className="home-stat">
              <span className="home-stat-num">{completedDays}</span>
              <span className="home-stat-label">完成天数</span>
            </div>
            <div className="home-stat-divider"></div>
            <div className="home-stat">
              <span className="home-stat-num">{totalWords.toLocaleString()}</span>
              <span className="home-stat-label">已学单词</span>
            </div>
            <div className="home-stat-divider"></div>
            <div className="home-stat">
              <span className="home-stat-num">{wrongWords.length}</span>
              <span className="home-stat-label">待复习</span>
            </div>
          </div>
        </div>

        <div className="home-banner-right">
          <div className="home-progress-ring">
            <svg viewBox="0 0 96 96" className="progress-ring-svg">
              <circle cx="48" cy="48" r="38" fill="none" stroke="rgba(255,126,54,0.15)" strokeWidth="7" />
              <circle
                cx="48" cy="48" r="38" fill="none"
                stroke="var(--accent)" strokeWidth="7"
                strokeDasharray={`${2 * Math.PI * 38}`}
                strokeDashoffset={`${2 * Math.PI * 38 * (1 - completedDays / 30)}`}
                strokeLinecap="round"
                transform="rotate(-90 48 48)"
                style={{ transition: 'stroke-dashoffset 0.6s ease' }}
              />
            </svg>
            <div className="progress-ring-text">
              <span className="progress-ring-num">{overallPct}%</span>
              <span className="progress-ring-label">总进度</span>
            </div>
          </div>
          <div className="home-current-day">
            {currentDay ? `Day ${currentDay}` : '选择单元'}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="home-tabs">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`home-tab${activeSection === t.key ? ' active' : ''}`}
            onClick={() => setActiveSection(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Section Content */}
      <div className="home-section">

        {activeSection === 'learn' && <>
          <div className="home-section-header">
            <h2 className="home-section-title">选择学习单元</h2>
            <span className="home-section-desc">每天100词 · 共30天</span>
          </div>
          <div className="day-grid">
            {Array.from({ length: 30 }, (_, i) => {
              const day = i + 1
              const isActive = currentDay === day
              const dayProgress = progress[day] || {}
              const isCompleted = dayProgress.completed
              const correctCount = dayProgress.correctCount || 0
              return (
                <div
                  key={day}
                  className={`day-card${isActive ? ' active' : ''}${isCompleted ? ' completed' : ''}`}
                  onClick={() => handleDayClick(day)}
                >
                  <div className="day-number">Day {day}</div>
                  <div className="day-words">100 词</div>
                  <div className="day-progress-bar">
                    <div className="day-progress-fill" style={{ width: `${Math.min(correctCount, 100)}%` }}></div>
                  </div>
                  <div className="day-progress-text">
                    {isCompleted ? '✓' : correctCount > 0 ? `${correctCount}%` : ''}
                  </div>
                </div>
              )
            })}
          </div>
        </>}

        {activeSection === 'review' && <>
          <div className="home-section-header">
            <h2 className="home-section-title">复习计划</h2>
            <span className="home-section-desc">艾宾浩斯遗忘曲线</span>
          </div>
          <div className="home-empty-state">
            <div className="home-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
            </div>
            <p className="home-empty-text">完成第一天的学习后，复习计划将自动生成</p>
            <button className="home-empty-btn" onClick={() => setActiveSection('learn')}>开始学习</button>
          </div>
        </>}

        {activeSection === 'wrong' && <>
          <div className="home-section-header">
            <h2 className="home-section-title">错词本</h2>
            <span className="home-section-desc">{wrongWords.length} 个待复习</span>
          </div>
          {wrongWords.length === 0 ? (
            <div className="home-empty-state">
              <div className="home-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
              </div>
              <p className="home-empty-text">太棒了！错词本还是空的</p>
            </div>
          ) : (
            <div className="wrong-words-list">
              {wrongWords.slice(0, 20).map((w, i) => (
                <div key={i} className="wrong-word-item">
                  <div className="wrong-word-text">
                    <span className="wrong-word-en">{w.word}</span>
                    <span className="wrong-word-phonetic">{w.phonetic}</span>
                  </div>
                  <div className="wrong-word-def">
                    <span className="wrong-word-pos">{w.pos}</span>
                    <span>{w.definition}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>}

        {activeSection === 'stats' && <>
          <div className="home-section-header">
            <h2 className="home-section-title">学习统计</h2>
            <span className="home-section-desc">数据概览</span>
          </div>
          <div className="stats-grid">
            {[
              { num: totalWords.toLocaleString(), label: '总学习词数', bg: 'var(--accent-light)', color: 'var(--accent)' },
              { num: completedDays, label: '完成天数', bg: '#F0FDF4', color: '#10B981' },
              { num: wrongWords.length, label: '错词数量', bg: '#FEF2F2', color: '#EF4444' },
              { num: 30 - completedDays, label: '剩余天数', bg: '#EFF6FF', color: '#3B82F6' },
            ].map((s, i) => (
              <div key={i} className="stats-card">
                <div className="stats-card-bar" style={{ background: s.bg }}>
                  <span className="stats-card-num" style={{ color: s.color }}>{s.num}</span>
                </div>
                <div className="stats-card-label">{s.label}</div>
              </div>
            ))}
          </div>
        </>}

      </div>
    </div>
  )
}

export default HomePage
