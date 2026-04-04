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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-accent/5 to-accent/10">
      <div className="w-full max-w-md p-6">
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
