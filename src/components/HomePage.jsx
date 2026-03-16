import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

// Chapter selection modal
function ChapterModal({ progress, currentDay, onSelectDay, onClose }) {
  const days = Array.from({ length: 30 }, (_, i) => i + 1)

  const getDayProgress = (day) => progress[day] || {}

  const lastActiveDay = (() => {
    for (let d = 30; d >= 1; d--) {
      if (progress[d]?.correctCount > 0) return d
    }
    return currentDay || 1
  })()

  return (
    <div className="chapter-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="chapter-modal">
        {/* Modal Header */}
        <div className="chapter-modal-header">
          <div className="chapter-modal-info">
            <h2 className="chapter-modal-title">雅思标准词汇 · 30天计划</h2>
            <p className="chapter-modal-subtitle">30章节 &nbsp; 3000词</p>
          </div>
          <div className="chapter-modal-actions">
            <button
              className="chapter-continue-btn"
              onClick={() => { onSelectDay(lastActiveDay); onClose() }}
            >
              继续学习 · Day {lastActiveDay}
            </button>
            <button className="chapter-modal-close" onClick={onClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Chapter Grid */}
        <div className="chapter-modal-body">
          <div className="chapter-grid">
            {days.map(day => {
              const dp = getDayProgress(day)
              const isCompleted = dp.completed
              const isActive = day === lastActiveDay
              const hasProgress = dp.correctCount > 0

              return (
                <div
                  key={day}
                  className={`chapter-card${isActive ? ' current' : ''}${isCompleted ? ' completed' : ''}`}
                  onClick={() => { onSelectDay(day); onClose() }}
                >
                  <div className="chapter-card-name">超核心词汇 Day {day}</div>
                  <div className="chapter-card-count">100词</div>
                  {isCompleted ? (
                    <div className="chapter-card-status done">已完成</div>
                  ) : hasProgress ? (
                    <div className="chapter-card-status inprogress">未完成</div>
                  ) : null}
                  {isActive && !isCompleted && (
                    <div className="chapter-card-recent">最近学习</div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

function HomePage({ user, currentDay, onDayChange }) {
  const navigate = useNavigate()
  const [progress, setProgress] = useState({})
  const [showChapterModal, setShowChapterModal] = useState(false)

  useEffect(() => {
    const savedProgress = localStorage.getItem('day_progress')
    if (savedProgress) {
      try { setProgress(JSON.parse(savedProgress)) } catch (e) {}
    }
  }, [])

  const handleSelectDay = (day) => {
    onDayChange(day)
    navigate('/practice')
  }

  const completedDays = Object.entries(progress).filter(([, p]) => p.completed).length
  const totalWords = completedDays * 100
  const wrongWords = JSON.parse(localStorage.getItem('wrong_words') || '[]')

  // Find last active day
  const lastActiveDay = (() => {
    for (let d = 30; d >= 1; d--) {
      if (progress[d]?.correctCount > 0) return d
    }
    return currentDay || 1
  })()

  return (
    <div className="study-center-page">
      <div className="study-center-grid">

        {/* Main book card - 30 day plan */}
        <div
          className="study-book-card study-book-card-main"
          onClick={() => setShowChapterModal(true)}
        >
          <div className="study-book-header">
            <h3 className="study-book-title">雅思标准词汇3000</h3>
            <span className="study-book-subtitle">（30天计划）</span>
          </div>
          <div className="study-book-progress-text">
            {totalWords} / 3000
          </div>
          <div className="study-book-progress-bar">
            <div
              className="study-book-progress-fill"
              style={{ width: `${Math.round(totalWords / 3000 * 100)}%` }}
            />
          </div>
          <div className="study-book-stats">
            <span>{completedDays} / 30 天</span>
            <span>{wrongWords.length > 0 ? `${wrongWords.length} 错词` : ''}</span>
          </div>
        </div>

        {/* Quick start card */}
        <div
          className="study-book-card study-book-card-cta"
          onClick={() => { onDayChange(lastActiveDay); navigate('/practice') }}
        >
          <div className="study-cta-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" />
            </svg>
          </div>
          <div className="study-cta-text">
            <div className="study-cta-title">继续学习</div>
            <div className="study-cta-subtitle">Day {lastActiveDay} · 100词</div>
          </div>
        </div>

        {/* Wrong words review card */}
        <div className="study-book-card study-book-card-review">
          <div className="study-review-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="9" y1="13" x2="15" y2="13" />
              <line x1="9" y1="17" x2="15" y2="17" />
            </svg>
          </div>
          <div className="study-review-info">
            <div className="study-review-title">错词本</div>
            <div className="study-review-count">
              {wrongWords.length > 0 ? `${wrongWords.length} 个待复习` : '暂无错词'}
            </div>
          </div>
        </div>

        {/* Stats card */}
        <div className="study-book-card study-book-card-stats">
          <div className="study-stats-row">
            <div className="study-stat-item">
              <span className="study-stat-num">{completedDays}</span>
              <span className="study-stat-label">完成天数</span>
            </div>
            <div className="study-stat-item">
              <span className="study-stat-num">{totalWords.toLocaleString()}</span>
              <span className="study-stat-label">已学词数</span>
            </div>
            <div className="study-stat-item">
              <span className="study-stat-num">{30 - completedDays}</span>
              <span className="study-stat-label">剩余天数</span>
            </div>
          </div>
        </div>

        {/* Go to vocab library card */}
        <div
          className="study-add-card"
          onClick={() => navigate('/')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>自定义词书</span>
        </div>

      </div>

      {/* Chapter Modal */}
      {showChapterModal && (
        <ChapterModal
          progress={progress}
          currentDay={currentDay}
          onSelectDay={handleSelectDay}
          onClose={() => setShowChapterModal(false)}
        />
      )}
    </div>
  )
}

export default HomePage
