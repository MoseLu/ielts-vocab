// ── App Router ─────────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth, useToast, ToastProvider, AIChatProvider } from './contexts'
import { SettingsProvider } from './contexts'
import Header from './components/Header'
import LeftSidebar from './components/LeftSidebar'
import AuthPage from './components/AuthPage'
import HomePage from './components/HomePage'
import PracticePage from './components/practice/PracticePage'
import VocabBookPage from './components/VocabBookPage'
import ErrorsPage from './components/ErrorsPage'
import StatsPage from './components/StatsPage'
import ProfilePage from './components/ProfilePage'
import AIChatPanel from './components/AIChatPanel'
import VocabTestPage from './components/VocabTestPage'
import Toast from './components/Toast'

interface AppRoutesProps {
  mode: string
  currentDay: number | null
  onModeChange: (m: string) => void
  onDayChange: (day: number) => void
}

function AppRoutes({ mode, currentDay, onModeChange, onDayChange }: AppRoutesProps) {
  const { user, logout } = useAuth()
  const { toast } = useToast()
  const location = useLocation()
  const isPractice = location.pathname === '/practice'

  return (
    <div className="app">
      {!isPractice && (
        <Header
          user={user}
          currentDay={currentDay}
          mode={mode as any}
          onLogout={() => logout()}
          onModeChange={onModeChange}
          onDayChange={onDayChange}
          onUserUpdate={() => {}}
        />
      )}

      <div className={isPractice ? 'practice-fullscreen' : 'app-body'}>
        {user && !isPractice && <LeftSidebar />}
        <main className={isPractice ? 'practice-fullscreen-main' : 'main'}>
          <Routes>
            <Route
              path="/login"
              element={
                user ? (
                  <Navigate to="/" replace />
                ) : (
                  <AuthPage />
                )
              }
            />

            <Route
              path="/"
              element={
                user ? (
                  <VocabBookPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/plan"
              element={
                user ? (
                  <HomePage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/practice"
              element={
                user ? (
                  <PracticePage
                    currentDay={currentDay ?? undefined}
                    mode={mode as any}
                    onModeChange={onModeChange}
                    onDayChange={onDayChange}
                    showToast={() => {}}
                  />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/errors"
              element={
                user ? (
                  <ErrorsPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/stats"
              element={
                user ? (
                  <StatsPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/profile"
              element={
                user ? (
                  <ProfilePage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/vocab-test"
              element={
                user ? (
                  <VocabTestPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
          </Routes>
        </main>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}

      {user && <AIChatPanel />}
    </div>
  )
}

export default function App() {
  const [mode, setMode] = useState<string>(() => localStorage.getItem('current_mode') || 'listening')
  const [currentDay, setCurrentDay] = useState<number | null>(() => {
    const saved = localStorage.getItem('current_day')
    return saved ? parseInt(saved, 10) : null
  })

  useEffect(() => {
    ;(window as any).__currentMode = mode
  }, [mode])

  useEffect(() => {
    ;(window as any).__currentDay = currentDay
  }, [currentDay])

  const handleModeChange = (m: string) => {
    setMode(m)
    localStorage.setItem('current_mode', m)
  }

  const handleDayChange = (day: number) => {
    setCurrentDay(day)
    localStorage.setItem('current_day', day.toString())
  }

  return (
    <Router>
      <AIChatProvider>
        <SettingsProvider>
          <AuthProvider>
            <ToastProvider>
              <AppRoutes
                mode={mode}
                currentDay={currentDay}
                onModeChange={handleModeChange}
                onDayChange={handleDayChange}
              />
            </ToastProvider>
          </AuthProvider>
        </SettingsProvider>
      </AIChatProvider>
    </Router>
  )
}
