import type { ReactNode } from 'react'

interface PageProps {
  children: ReactNode
  className?: string
}

interface PageHeaderProps {
  children: ReactNode
  className?: string
}

interface PageContentProps {
  children: ReactNode
  className?: string
}

interface PageScrollProps {
  children: ReactNode
  className?: string
}

export function Page({ children, className = '' }: PageProps) {
  const classes = ['page', className].filter(Boolean).join(' ')
  return <section className={classes}>{children}</section>
}

export function PageHeader({ children, className = '' }: PageHeaderProps) {
  const classes = ['page__header', className].filter(Boolean).join(' ')
  return <div className={classes}>{children}</div>
}

export function PageContent({ children, className = '' }: PageContentProps) {
  const classes = ['page__content', className].filter(Boolean).join(' ')
  return <div className={classes}>{children}</div>
}

export function PageScroll({ children, className = '' }: PageScrollProps) {
  const classes = ['page__scroll', className].filter(Boolean).join(' ')
  return <div className={classes}>{children}</div>
}

export default Page
