import React from 'react'

interface EmptyStateProps {
  title: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  icon?: React.ReactNode
  page?: boolean
  className?: string
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  page = false,
  className = '',
}: EmptyStateProps) {
  const classes = ['empty-state', page ? 'empty-state--page' : '', className].filter(Boolean).join(' ')

  return (
    <div className={classes}>
      {icon ? <div className="empty-state-icon">{icon}</div> : null}
      <div className="empty-state-title">{title}</div>
      {description ? <div className="empty-state-description">{description}</div> : null}
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  )
}
