// ── Loading Components ─────────────────────────────────────────────────────────

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
        style={{ opacity: 0.25 }}
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        style={{ opacity: 0.75 }}
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

interface LoadingProps {
  text?: string
  fullScreen?: boolean
}

export function Loading({ text = '加载中...', fullScreen = false }: LoadingProps) {
  const content = (
    <div className="loading-content">
      <Spinner size="lg" />
      {text && <p style={{ color: 'var(--text-secondary)' }}>{text}</p>}
    </div>
  )

  if (fullScreen) {
    return (
      <div className="loading-fullscreen">
        {content}
      </div>
    )
  }

  return <div style={{ padding: '32px 0' }}>{content}</div>
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
