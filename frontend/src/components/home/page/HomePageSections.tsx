import type { CSSProperties, MouseEvent } from 'react'
import type { Book } from '../../../types'
import {
  getStepStateLabel,
  getTaskStateLabel,
  type DailyPlanTask,
  type StudyBookCard,
} from './homePageModels'

export function TodoTaskRow({
  task,
}: {
  task: DailyPlanTask
}) {
  const isCompleted = task.status === 'completed'
  const taskSteps = task.steps ?? []

  return (
    <li className={`study-todo-item${isCompleted ? ' is-completed' : ''}`}>
      <div className="study-todo-card-head">
        <div className="study-todo-heading">
          <input
            type="checkbox"
            className="study-todo-check"
            checked={isCompleted}
            readOnly
            tabIndex={-1}
            aria-hidden="true"
          />
          <div className="study-todo-main">
            <div className="study-todo-title-row">
              <div className="study-todo-title-main">
                <h3>{task.title}</h3>
                <span className="study-todo-subtitle">{task.description}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="study-todo-head-side">
          <div className="study-todo-title-meta">
            <span className={`study-todo-progress${isCompleted ? ' is-completed' : ''}`}>
              {task.badge}
            </span>
            <span className={`study-todo-state${isCompleted ? ' is-completed' : ''}`}>
              {getTaskStateLabel(task)}
            </span>
          </div>
        </div>
      </div>

      {taskSteps.length > 0 && (
        <ul className="study-todo-steps" aria-label={`${task.title}执行步骤`}>
          {taskSteps.map(step => (
            <li key={step.id} className={`study-todo-step is-${step.status}`}>
              <div className="study-todo-step-main">
                <input
                  type="checkbox"
                  className="study-todo-step-check"
                  checked={step.status === 'completed'}
                  readOnly
                  tabIndex={-1}
                  aria-hidden="true"
                />
                <span className="study-todo-step-label">{step.label}</span>
              </div>
              <span className={`study-todo-step-state is-${step.status}`}>
                {getStepStateLabel(step)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

function getHomeBookDisplayTitle(title: string) {
  return title === '雅思综合词汇5000+' ? '雅思综合词汇' : title
}

export function MyBookCard({
  card,
  onSelect,
  onRemove,
}: {
  card: StudyBookCard
  onSelect: (book: Book) => void
  onRemove: (bookId: string, event: MouseEvent<HTMLButtonElement>) => void
}) {
  const displayTitle = getHomeBookDisplayTitle(card.book.title)

  return (
    <div
      key={card.book.id}
      className="study-book-card study-book-card-main"
      onClick={() => onSelect(card.book)}
    >
      {!card.book.is_auto_favorites && (
        <button
          className="study-book-remove"
          onClick={(event) => onRemove(card.book.id, event)}
          title="移除"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}

      <div className="study-book-icon-row">
        <div className="study-book-icon study-book-icon--accent">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
        </div>

        <div className="study-book-header">
          <h3 className="study-book-title" title={displayTitle}>{displayTitle}</h3>
          <div className="study-book-badges">
            {card.book.is_paid && (
              <span className="study-book-badge study-book-badge--success">已购</span>
            )}
            {card.book.is_auto_favorites && (
              <span className="study-book-badge study-book-badge--neutral">系统</span>
            )}
            {card.isActive && <span className="study-book-state study-book-state--active">进行中</span>}
            {card.isComplete && <span className="study-book-state study-book-state--complete">已完成</span>}
          </div>
        </div>
      </div>

      <div className="study-book-progress-text">
        {card.displayCurrentCount} / {card.displayTotalCount} {card.displayUnit}
      </div>
      <div
        className="study-book-progress-bar"
        role="progressbar"
        aria-label={`${displayTitle} 学习进度`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={card.progressPercent}
      >
        <div
          className="study-book-progress-fill"
          style={{ '--progress-percent': `${card.progressPercent}%` } as CSSProperties}
        />
      </div>
      <div className="study-book-stats">
        <span>{card.progressPercent}% 完成</span>
        {card.isComplete ? (
          <span className="study-book-status-complete">主线已完成</span>
        ) : (
          <span>剩余 {card.displayRemainingCount} {card.displayUnit}</span>
        )}
      </div>
    </div>
  )
}
