import React from 'react'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ size = 'md', className = '' }: SpinnerProps) {
  const dim = { sm: 16, md: 24, lg: 32 }[size]

  return (
    <svg
      className={`loading-spin ${className}`}
      width={dim}
      height={dim}
      fill="none"
      viewBox="0 0 24 24"
      style={{ color: 'var(--accent)' }}
    >
      <circle
        style={{ opacity: 0.22 }}
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3.5"
      />
      <path
        style={{ opacity: 0.92 }}
        fill="currentColor"
        d="M12 2a10 10 0 0 1 10 10h-3.5A6.5 6.5 0 0 0 12 5.5V2Z"
      />
    </svg>
  )
}

interface LoadingProps {
  text?: string
  fullScreen?: boolean
  page?: boolean
  level?: 'component' | 'page' | 'global'
}

export function Loading({ text = 'Loading...', fullScreen = false, page = false, level }: LoadingProps) {
  const resolvedLevel = level ?? (fullScreen ? 'global' : page ? 'page' : 'component')
  const content = (
    <div className="loading-content" role="status" aria-live="polite">
      <div className="loading-spinner-shell">
        <Spinner size="lg" />
      </div>
      {text && <p className="loading-text">{text}</p>}
    </div>
  )

  if (fullScreen) {
    return (
      <div className="loading-fullscreen loading-state loading-state--global">
        {content}
      </div>
    )
  }

  return <div className={`loading-state loading-state--${resolvedLevel}`}>{content}</div>
}

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}

export function Skeleton({
  className = '',
  variant = 'text',
  width,
  height,
}: SkeletonProps) {
  const baseStyles = 'animate-pulse bg-secondary/20'

  const variants = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  }

  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height

  return (
    <div
      className={`${baseStyles} ${variants[variant]} ${className}`}
      style={style}
    />
  )
}
