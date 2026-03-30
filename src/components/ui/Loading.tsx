import React, { type ReactNode } from 'react'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ size = 'md', className = '' }: SpinnerProps) {
  const dim = { sm: 16, md: 24, lg: 32 }[size]

  return (
    <svg
      className={`loading-spin ${className}`.trim()}
      width={dim}
      height={dim}
      fill="none"
      viewBox="0 0 24 24"
      style={{ color: 'var(--accent)' }}
      aria-hidden="true"
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

interface MicroLoadingProps {
  text?: string
  className?: string
  tone?: 'default' | 'accent'
}

export function MicroLoading({
  text = '加载中...',
  className = '',
  tone = 'default',
}: MicroLoadingProps) {
  return (
    <span
      className={`micro-loading micro-loading--${tone} ${className}`.trim()}
      role="status"
      aria-live="polite"
    >
      <Spinner size="sm" className="micro-loading__spinner" />
      {text && <span className="micro-loading__text">{text}</span>}
    </span>
  )
}

interface LoadingProps {
  text?: string
  fullScreen?: boolean
  page?: boolean
  level?: 'component' | 'page' | 'global'
}

export function Loading({ text = '加载中...', fullScreen = false, page = false, level }: LoadingProps) {
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
  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height

  return (
    <div
      className={`ui-skeleton ui-skeleton--${variant} ${className}`.trim()}
      style={style}
      aria-hidden="true"
    />
  )
}

export type PageSkeletonVariant = 'books' | 'stats' | 'journal' | 'admin' | 'practice' | 'quiz'

interface PageSkeletonProps {
  variant?: PageSkeletonVariant
  className?: string
  itemCount?: number
  metricCount?: number
  bookMinWidth?: number
}

function renderBooksSkeleton(itemCount: number, bookMinWidth: number) {
  return (
    <div
      className="page-skeleton-grid page-skeleton-grid--books"
      style={{ ['--page-skeleton-book-min-width' as string]: `${bookMinWidth}px` }}
    >
      {Array.from({ length: itemCount }, (_, index) => (
        <div key={index} className="page-skeleton-card page-skeleton-card--book">
          <div className="page-skeleton-row page-skeleton-row--book-head">
            <Skeleton variant="rectangular" width={48} height={48} />
            <div className="page-skeleton-stack page-skeleton-stack--book-title">
              <Skeleton width="62%" height={18} />
              <Skeleton width="34%" height={14} />
            </div>
          </div>
          <Skeleton width="38%" height={14} />
          <Skeleton variant="rectangular" width="100%" height={10} />
          <div className="page-skeleton-row page-skeleton-row--spread">
            <Skeleton width="28%" height={14} />
            <Skeleton width="22%" height={14} />
          </div>
        </div>
      ))}
    </div>
  )
}

function renderStatsSkeleton(metricCount: number) {
  return (
    <>
      <div className="page-skeleton-intro">
        <Skeleton width="72%" height={14} />
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--metrics">
        {Array.from({ length: metricCount }, (_, index) => (
          <div key={index} className="page-skeleton-card page-skeleton-card--metric">
            <Skeleton width="38%" height={28} />
            <Skeleton width="54%" height={13} />
          </div>
        ))}
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--stats-panels">
        <div className="page-skeleton-panel page-skeleton-panel--wide">
          <Skeleton width="34%" height={18} />
          <Skeleton width="58%" height={13} />
          <div className="page-skeleton-chart page-skeleton-chart--donut" />
        </div>
        <div className="page-skeleton-panel">
          <Skeleton width="30%" height={18} />
          <Skeleton width="46%" height={13} />
          <div className="page-skeleton-chart" />
        </div>
        <div className="page-skeleton-panel">
          <Skeleton width="40%" height={18} />
          <Skeleton width="56%" height={13} />
          <div className="page-skeleton-table">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} width="100%" height={16} />
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

function renderAdminSkeleton() {
  return (
    <>
      <div className="page-skeleton-intro">
        <Skeleton width="42%" height={14} />
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--metrics">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="page-skeleton-card page-skeleton-card--metric">
            <Skeleton width="34%" height={28} />
            <Skeleton width="48%" height={13} />
          </div>
        ))}
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--admin-panels">
        <div className="page-skeleton-panel page-skeleton-panel--wide">
          <Skeleton width="28%" height={18} />
          <Skeleton width="44%" height={13} />
          <div className="page-skeleton-chart" />
        </div>
        <div className="page-skeleton-panel">
          <Skeleton width="30%" height={18} />
          <div className="page-skeleton-table">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} width="100%" height={16} />
            ))}
          </div>
        </div>
        <div className="page-skeleton-panel">
          <Skeleton width="36%" height={18} />
          <div className="page-skeleton-stack">
            {Array.from({ length: 4 }, (_, index) => (
              <Skeleton key={index} width="100%" height={16} />
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

function renderJournalSkeleton(itemCount: number) {
  return (
    <>
      <div className="page-skeleton-row page-skeleton-row--journal-topbar">
        <div className="page-skeleton-tabs">
          <Skeleton variant="rectangular" width={112} height={34} />
          <Skeleton variant="rectangular" width={112} height={34} />
        </div>
        <Skeleton variant="rectangular" width={136} height={36} />
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--journal">
        <div className="page-skeleton-panel page-skeleton-panel--sidebar">
          {Array.from({ length: itemCount }, (_, index) => (
            <div key={index} className="page-skeleton-sidebar-item">
              <Skeleton width="62%" height={15} />
              <Skeleton width="34%" height={12} />
            </div>
          ))}
        </div>
        <div className="page-skeleton-panel page-skeleton-panel--document">
          <Skeleton width="28%" height={28} />
          <Skeleton width="18%" height={12} />
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} width={index === 7 ? '48%' : '100%'} height={14} />
          ))}
        </div>
      </div>
    </>
  )
}

function renderPracticeSkeleton() {
  return (
    <div className="page-skeleton-practice">
      <div className="page-skeleton-practice-head">
        <Skeleton width={180} height={36} />
        <Skeleton width={120} height={18} />
      </div>
      <div className="page-skeleton-practice-stage">
        <Skeleton width="42%" height={22} />
        <Skeleton width="28%" height={16} />
        <Skeleton variant="rectangular" width="100%" height={74} />
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--practice-options">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="page-skeleton-card page-skeleton-card--option">
            <Skeleton width="22%" height={12} />
            <Skeleton width="92%" height={16} />
            <Skeleton width="74%" height={16} />
          </div>
        ))}
      </div>
    </div>
  )
}

function renderQuizSkeleton() {
  return (
    <div className="page-skeleton-quiz">
      <div className="page-skeleton-row page-skeleton-row--spread">
        <Skeleton variant="circular" width={40} height={40} />
        <Skeleton width={120} height={24} />
        <Skeleton width={56} height={20} />
      </div>
      <Skeleton variant="rectangular" width="100%" height={8} />
      <div className="page-skeleton-quiz-card">
        <Skeleton width="18%" height={14} />
        <Skeleton width="44%" height={34} />
        <Skeleton width="26%" height={16} />
      </div>
      <div className="page-skeleton-grid page-skeleton-grid--quiz-options">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="page-skeleton-card page-skeleton-card--option">
            <Skeleton width="86%" height={16} />
            <Skeleton width="68%" height={16} />
          </div>
        ))}
      </div>
    </div>
  )
}

export function PageSkeleton({
  variant = 'books',
  className = '',
  itemCount = variant === 'books' ? 4 : variant === 'journal' ? 4 : 4,
  metricCount = variant === 'stats' ? 9 : 4,
  bookMinWidth = 260,
}: PageSkeletonProps) {
  const body = variant === 'stats'
    ? renderStatsSkeleton(metricCount)
    : variant === 'journal'
      ? renderJournalSkeleton(itemCount)
      : variant === 'admin'
        ? renderAdminSkeleton()
        : variant === 'practice'
          ? renderPracticeSkeleton()
          : variant === 'quiz'
            ? renderQuizSkeleton()
            : renderBooksSkeleton(itemCount, bookMinWidth)

  return (
    <div
      className={`page-skeleton page-skeleton--${variant} ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-label="Loading page content"
    >
      <div className="page-skeleton-body">
        {body}
      </div>
    </div>
  )
}

interface PageReadyProps {
  ready: boolean
  children: ReactNode
  fallback?: ReactNode
}

export function PageReady({ ready, children, fallback }: PageReadyProps) {
  if (ready) {
    return <>{children}</>
  }

  return <>{fallback ?? <PageSkeleton />}</>
}
