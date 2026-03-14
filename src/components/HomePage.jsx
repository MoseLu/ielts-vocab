import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function HomePage({ user, currentDay, onDayChange }) {
  const navigate = useNavigate()
  const [progress, setProgress] = useState({})
  const [activeSection, setActiveSection] = useState('learn')

  useEffect(() => {
    // Load progress from localStorage
    const savedProgress = localStorage.getItem('day_progress')
    if (savedProgress) {
      try {
        setProgress(JSON.parse(savedProgress))
      } catch (e) {
        // ignore
      }
    }
  }, [])

  const handleDayClick = (day) => {
    onDayChange(day)
    navigate('/practice')
  }

  const getCompletedDays = () => {
    return Object.entries(progress).filter(([, p]) => p.completed).length
  }

  const totalWords = getCompletedDays() * 100

  return (
    <div className="home-page">
      {/* Welcome Banner */}
      <div className="home-banner">
        <div className="home-banner-content">
          <h1 className="home-welcome">你好，{user?.username || '同学'} 👋</h1>
          <p className="home-subtitle">坚持每天学习100个词汇，30天掌握雅思核心词汇</p>
          <div className="home-stats-row">
            <div className="home-stat">
              <span className="home-stat-num">{getCompletedDays()}</span>
              <span className="home-stat-label">已完成天数</span>
            </div>
            <div className="home-stat-divider"></div>
            <div className="home-stat">
              <span className="home-stat-num">{totalWords}</span>
              <span className="home-stat-label">已学单词</span>
            </div>
            <div className="home-stat-divider"></div>
            <div className="home-stat">
              <span className="home-stat-num">{30 - getCompletedDays()}</span>
              <span className="home-stat-label">剩余天数</span>
            </div>
          </div>
        </div>
        <div className="home-banner-progress">
          <div className="home-progress-ring">
            <svg viewBox="0 0 80 80" className="progress-ring-svg">
              <circle cx="40" cy="40" r="32" fill="none" stroke="var(--accent-light)" strokeWidth="6" />
              <circle
                cx="40" cy="40" r="32" fill="none"
                stroke="var(--accent)" strokeWidth="6"
                strokeDasharray={`${2 * Math.PI * 32}`}
                strokeDashoffset={`${2 * Math.PI * 32 * (1 - getCompletedDays() / 30)}`}
                strokeLinecap="round"
                transform="rotate(-90 40 40)"
                style={{ transition: 'stroke-dashoffset 0.5s ease' }}
              />
            </svg>
            <div className="progress-ring-text">
              <span className="progress-ring-num">{Math.round(getCompletedDays() / 30 * 100)}%</span>
              <span className="progress-ring-label">总进度</span>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Menu Cards */}
      <div className="home-menu-grid">
        <div
          className={`home-menu-card ${activeSection === 'learn' ? 'active' : ''}`}
          onClick={() => setActiveSection('learn')}
        >
          <div className="home-menu-icon" style={{ background: 'var(--accent-light)', color: 'var(--accent)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
            </svg>
          </div>
          <div className="home-menu-info">
            <div className="home-menu-title">今日学习</div>
            <div className="home-menu-desc">选择学习日期，开始单词学习</div>
          </div>
          <svg className="home-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div
          className={`home-menu-card ${activeSection === 'review' ? 'active' : ''}`}
          onClick={() => setActiveSection('review')}
        >
          <div className="home-menu-icon" style={{ background: '#EFF6FF', color: '#3B82F6' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </div>
          <div className="home-menu-info">
            <div className="home-menu-title">复习计划</div>
            <div className="home-menu-desc">艾宾浩斯遗忘曲线智能复习</div>
          </div>
          <svg className="home-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div
          className={`home-menu-card ${activeSection === 'wrong' ? 'active' : ''}`}
          onClick={() => setActiveSection('wrong')}
        >
          <div className="home-menu-icon" style={{ background: '#FEF2F2', color: '#EF4444' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="12" y1="18" x2="12" y2="12"></line>
              <line x1="9" y1="15" x2="15" y2="15"></line>
            </svg>
          </div>
          <div className="home-menu-info">
            <div className="home-menu-title">错词本</div>
            <div className="home-menu-desc">
              {(() => {
                const wrongWords = JSON.parse(localStorage.getItem('wrong_words') || '[]')
                return `${wrongWords.length} 个待复习单词`
              })()}
            </div>
          </div>
          <svg className="home-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div
          className={`home-menu-card ${activeSection === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveSection('stats')}
        >
          <div className="home-menu-icon" style={{ background: '#F0FDF4', color: '#10B981' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
          </div>
          <div className="home-menu-info">
            <div className="home-menu-title">学习统计</div>
            <div className="home-menu-desc">查看详细学习数据与趋势</div>
          </div>
          <svg className="home-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>
      </div>

      {/* Section Content */}
      {activeSection === 'learn' && (
        <div className="home-section">
          <div className="home-section-header">
            <h2 className="home-section-title">选择学习单元</h2>
            <span className="home-section-desc">每天100个单词，30天掌握3000词汇</span>
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
                  className={`day-card ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                  onClick={() => handleDayClick(day)}
                >
                  <div className="day-card-top">
                    <span className="day-number">Day {day}</span>
                    {isCompleted && (
                      <svg className="day-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                    )}
                    {isActive && !isCompleted && (
                      <span className="day-badge">进行中</span>
                    )}
                  </div>
                  <div className="day-words">100 词</div>
                  {correctCount > 0 && (
                    <div className="day-progress-bar">
                      <div
                        className="day-progress-fill"
                        style={{ width: `${Math.min(correctCount / 100 * 100, 100)}%` }}
                      ></div>
                    </div>
                  )}
                  <div className="day-progress-text">
                    {isCompleted ? '已完成' : correctCount > 0 ? `${correctCount}/100` : '未开始'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {activeSection === 'review' && (
        <div className="home-section">
          <div className="home-section-header">
            <h2 className="home-section-title">复习计划</h2>
            <span className="home-section-desc">根据艾宾浩斯遗忘曲线自动安排复习</span>
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
            <button
              className="home-empty-btn"
              onClick={() => setActiveSection('learn')}
            >
              开始学习
            </button>
          </div>
        </div>
      )}

      {activeSection === 'wrong' && (
        <div className="home-section">
          <div className="home-section-header">
            <h2 className="home-section-title">错词本</h2>
            <span className="home-section-desc">记录你答错的单词，集中攻克难点</span>
          </div>
          {(() => {
            const wrongWords = JSON.parse(localStorage.getItem('wrong_words') || '[]')
            if (wrongWords.length === 0) {
              return (
                <div className="home-empty-state">
                  <div className="home-empty-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                      <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                  </div>
                  <p className="home-empty-text">太棒了！你的错词本还是空的</p>
                </div>
              )
            }
            return (
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
            )
          })()}
        </div>
      )}

      {activeSection === 'stats' && (
        <div className="home-section">
          <div className="home-section-header">
            <h2 className="home-section-title">学习统计</h2>
            <span className="home-section-desc">你的学习数据概览</span>
          </div>
          <div className="stats-grid">
            <div className="stats-card">
              <div className="stats-card-icon" style={{ background: 'var(--accent-light)', color: 'var(--accent)' }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                </svg>
              </div>
              <div className="stats-card-num">{totalWords}</div>
              <div className="stats-card-label">总学习词数</div>
            </div>
            <div className="stats-card">
              <div className="stats-card-icon" style={{ background: '#F0FDF4', color: '#10B981' }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </div>
              <div className="stats-card-num">{getCompletedDays()}</div>
              <div className="stats-card-label">完成天数</div>
            </div>
            <div className="stats-card">
              <div className="stats-card-icon" style={{ background: '#FEF2F2', color: '#EF4444' }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </div>
              <div className="stats-card-num">
                {JSON.parse(localStorage.getItem('wrong_words') || '[]').length}
              </div>
              <div className="stats-card-label">错词数量</div>
            </div>
            <div className="stats-card">
              <div className="stats-card-icon" style={{ background: '#EFF6FF', color: '#3B82F6' }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <div className="stats-card-num">{30 - getCompletedDays()}</div>
              <div className="stats-card-label">剩余天数</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default HomePage
