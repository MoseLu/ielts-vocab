import { useState } from 'react'
import type { BookEntryMode } from '../../../lib'

// Type definitions
interface Book {
  id: string
  title: string
  word_count: number
  practice_mode?: string
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
  onStart: (plan: StudyPlan | null, entryMode?: BookEntryMode) => void
}

const DAILY_OPTIONS: number[] = [10, 20, 30, 50, 100]
const ENTRY_MODE_META: Record<BookEntryMode, { title: string; description: string }> = {
  practice: {
    title: '常规练习',
    description: '进入单项练习入口，再按具体模式推进。',
  },
  game: {
    title: '游戏闯关',
    description: '进入独立的五维闯关入口，把认义听说写串成一条主线。',
  },
}

function PlanModal({ book, progress, onClose, onStart }: PlanModalProps) {
  const currentIndex = progress?.current_index || 0
  const remainingWords = book.word_count - currentIndex
  const progressPercent = Math.round((currentIndex / book.word_count) * 100)
  const [entryMode, setEntryMode] = useState<BookEntryMode>('practice')
  const supportsGameEntry = book.practice_mode !== 'match'
  const activeEntryMode: BookEntryMode = supportsGameEntry ? entryMode : 'practice'

  const handleSelectPlan = (dailyCount: number) => {
    const plan: StudyPlan = {
      bookId: book.id,
      dailyCount,
      totalDays: Math.ceil(remainingWords / dailyCount),
      startIndex: currentIndex
    }
    onStart(plan, activeEntryMode)
  }

  const handleContinue = () => {
    onStart(null, activeEntryMode) // null means continue with existing progress
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
            {supportsGameEntry && (
              <>
                <div className="plan-entry-switch" role="tablist" aria-label="学习入口">
                  {(Object.entries(ENTRY_MODE_META) as [BookEntryMode, { title: string; description: string }][]).map(([mode, meta]) => (
                    <button
                      key={mode}
                      type="button"
                      role="tab"
                      aria-selected={activeEntryMode === mode}
                      className={`plan-entry-switch__option${activeEntryMode === mode ? ' is-active' : ''}`}
                      onClick={() => setEntryMode(mode)}
                    >
                      {meta.title}
                    </button>
                  ))}
                </div>
                <p className="plan-entry-note">{ENTRY_MODE_META[activeEntryMode].description}</p>
              </>
            )}
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
              <progress className="plan-progress-fill" max="100" value={progressPercent} />
            </div>
            <button className="plan-continue-btn" onClick={handleContinue}>
              {activeEntryMode === 'game' ? '继续闯关' : '继续学习'}
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
