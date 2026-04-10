import type { ReactNode } from 'react'

type PracticeRoundSummaryStatTone = 'accent' | 'error' | 'warning' | 'success' | 'neutral'
type PracticeRoundSummaryActionTone = 'primary' | 'secondary'

export interface PracticeRoundSummaryStat {
  value: string | number
  label: string
  tone?: PracticeRoundSummaryStatTone
}

export interface PracticeRoundSummaryAction {
  label: string
  onClick: () => void
  tone?: PracticeRoundSummaryActionTone
}

interface PracticeRoundSummaryProps {
  contextLabel?: string
  title?: string
  stats: PracticeRoundSummaryStat[]
  note?: ReactNode
  chipTitle?: string
  chips?: string[]
  actions: PracticeRoundSummaryAction[]
  className?: string
}

function getToneClassName(tone?: PracticeRoundSummaryStatTone): string {
  return tone ? ` practice-round-summary__stat--${tone}` : ''
}

export function PracticeRoundSummary({
  contextLabel,
  title = '本轮完成',
  stats,
  note,
  chipTitle,
  chips,
  actions,
  className,
}: PracticeRoundSummaryProps) {
  const visibleChips = (chips ?? []).filter(Boolean)

  return (
    <div className={`practice-round-summary${className ? ` ${className}` : ''}`}>
      {contextLabel ? (
        <div className="practice-round-summary__eyebrow">{contextLabel}</div>
      ) : null}

      <div className="practice-round-summary__title">{title}</div>

      <div className="practice-round-summary__stats">
        {stats.map(stat => (
          <div
            key={`${stat.label}-${stat.value}`}
            className={`practice-round-summary__stat${getToneClassName(stat.tone)}`}
          >
            <span className="practice-round-summary__stat-value">{stat.value}</span>
            <span className="practice-round-summary__stat-label">{stat.label}</span>
          </div>
        ))}
      </div>

      {note ? (
        <div className="practice-round-summary__note">{note}</div>
      ) : null}

      {chipTitle && visibleChips.length > 0 ? (
        <div className="practice-round-summary__section">
          <div className="practice-round-summary__section-title">{chipTitle}</div>
          <div className="practice-round-summary__chips">
            {visibleChips.map(chip => (
              <span key={chip} className="practice-round-summary__chip">{chip}</span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="practice-round-summary__actions">
        {actions.map(action => (
          <button
            key={action.label}
            className={`practice-round-summary__action practice-round-summary__action--${action.tone ?? 'secondary'}`}
            onClick={action.onClick}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  )
}
