import React from 'react'

// Type definitions
interface Book {
  id: string
  title: string
  word_count: number
  description?: string
}

interface BookProgress {
  current_index: number
}

interface StudyPlan {
  bookId: string
  dailyCount: number
  totalDays: number
  startIndex: number
}

interface PlanModalProps {
  book: Book
  progress?: BookProgress
  onClose: () => void
  onStart: (plan: StudyPlan | null) => void
}

const DAILY_OPTIONS: number[] = [10, 20, 30, 50, 100]

function PlanModal({ book, progress, onClose, onStart }: PlanModalProps) {
  const currentIndex = progress?.current_index || 0
  const remainingWords = book.word_count - currentIndex
  const progressPercent = Math.round((currentIndex / book.word_count) * 100)

  const handleSelectPlan = (dailyCount: number) => {
    const plan: StudyPlan = {
      bookId: book.id,
      dailyCount,
      totalDays: Math.ceil(remainingWords / dailyCount),
      startIndex: currentIndex
    }
    onStart(plan)
  }

  const handleContinue = () => {
    onStart(null) // null means continue with existing progress
  }

  return (
    <div className="plan-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="plan-modal">
        <div className="plan-modal-header">
          <div className="plan-modal-info">
            <h2 className="plan-modal-title">{book.title}</h2>
            <p className="plan-modal-subtitle">
              {book.word_count} 词
              {book.description && ` · ${book.description}`}
            </p>
          </div>
          <button className="plan-modal-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Progress section */}
        {currentIndex > 0 && (
          <div className="plan-modal-progress">
            <div className="plan-progress-header">
              <span>当前进度</span>
              <span>{currentIndex} / {book.word_count}</span>
            </div>
            <div className="plan-progress-bar">
              <div className="plan-progress-fill" style={{ width: `${progressPercent}%` }} />
            </div>
            <button className="plan-continue-btn" onClick={handleContinue}>
              继续学习
            </button>
          </div>
        )}

        {/* Plan options */}
        <div className="plan-modal-body">
          <div className="plan-section-title">
            {currentIndex > 0 ? '重新制定计划' : '选择学习计划'}
          </div>
          <div className="plan-options">
            {DAILY_OPTIONS.map((count: number) => {
              const days = Math.ceil(remainingWords / count)
              return (
                <div
                  key={count}
                  className="plan-option-card"
                  onClick={() => handleSelectPlan(count)}
                >
                  <div className="plan-option-daily">{count} 词/天</div>
                  <div className="plan-option-days">{days} 天完成</div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

export default PlanModal
