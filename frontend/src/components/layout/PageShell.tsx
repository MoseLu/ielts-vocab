import type { ReactNode } from 'react'

interface PageToolbarProps {
  children: ReactNode
  className?: string
}

export function PageToolbar({ children, className = '' }: PageToolbarProps) {
  const classes = ['page-shell-toolbar', className].filter(Boolean).join(' ')
  return <div className={classes}>{children}</div>
}

interface PageBodyProps {
  children: ReactNode
  className?: string
}

export function PageBody({ children, className = '' }: PageBodyProps) {
  const classes = ['page-shell-body', className].filter(Boolean).join(' ')
  return <div className={classes}>{children}</div>
}

interface PageShellProps {
  children: ReactNode
  className?: string
}

export function PageShell({ children, className = '' }: PageShellProps) {
  const classes = ['page-shell', className].filter(Boolean).join(' ')
  return <section className={classes}>{children}</section>
}

export default PageShell
