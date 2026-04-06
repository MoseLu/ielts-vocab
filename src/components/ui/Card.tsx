// ── Card Component ─────────────────────────────────────────────────────────────

import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
  onClick?: () => void
}

export function Card({
  children,
  className = '',
  padding = 'md',
  hover = false,
  onClick,
}: CardProps) {
  const cardClassName = [
    'ui-card',
    `ui-card--pad-${padding}`,
    (hover || onClick) ? 'ui-card--interactive' : '',
    className,
  ].filter(Boolean).join(' ')

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (!onClick) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onClick()
    }
  }

  return (
    <div
      className={cardClassName}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return (
    <div className={['ui-card__header', className].filter(Boolean).join(' ')}>
      {children}
    </div>
  )
}

interface CardContentProps {
  children: React.ReactNode
  className?: string
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return <div className={['ui-card__content', className].filter(Boolean).join(' ')}>{children}</div>
}

interface CardFooterProps {
  children: React.ReactNode
  className?: string
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return (
    <div className={['ui-card__footer', className].filter(Boolean).join(' ')}>
      {children}
    </div>
  )
}
