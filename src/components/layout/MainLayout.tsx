// ── Main Layout ────────────────────────────────────────────────────────────────

import React from 'react'
import { useAuth } from '../../contexts'
import Header from './navigation/Header'
import LeftSidebar from './navigation/LeftSidebar'

interface MainLayoutProps {
  children: React.ReactNode
  showHeader?: boolean
  showSidebar?: boolean
}

export function MainLayout({
  children,
  showHeader = true,
  showSidebar = true,
}: MainLayoutProps) {
  const { user } = useAuth()

  return (
    <div className="app">
      {showHeader && (
        <Header
          user={user}
          currentDay={null}
          onLogout={() => {
            localStorage.removeItem('auth_token')
            localStorage.removeItem('auth_user')
          }}
        />
      )}
      <div className="app-body">
        {showSidebar && <LeftSidebar />}
        <main className="main">
          {children}
        </main>
      </div>
    </div>
  )
}

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="auth-layout">
      <div className="auth-layout__inner">
        {children}
      </div>
    </div>
  )
}

interface PracticeLayoutProps {
  children: React.ReactNode
}

export function PracticeLayout({ children }: PracticeLayoutProps) {
  return (
    <div className="practice-fullscreen">
      <main className="practice-fullscreen-main">
        {children}
      </main>
    </div>
  )
}
