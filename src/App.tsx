// ── App Router ─────────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigationType } from 'react-router-dom'
import { AuthProvider, useAuth, useToast, ToastProvider, AIChatProvider } from './contexts'
import { SettingsProvider } from './contexts'
import Header from './components/Header'
import LeftSidebar from './components/LeftSidebar'
import BottomNav from './components/BottomNav'
import { Scrollbar } from './components/ui/Scrollbar'
import AuthPage from './components/AuthPage'
import { Loading } from './components/ui/Loading'
import HomePage from './components/HomePage'
import PracticePage from './components/practice/PracticePage'
import VocabBookPage from './components/VocabBookPage'
import ErrorsPage from './components/ErrorsPage'
import StatsPage from './components/StatsPage'
import ProfilePage from './components/ProfilePage'
import AIChatPanel from './components/AIChatPanel'
import VocabTestPage from './components/VocabTestPage'
import AdminDashboard from './components/AdminDashboard'
import LearningJournalPage from './components/LearningJournalPage'
import Toast from './components/Toast'

// Reset scroll to top on every PUSH navigation (tab switches, link clicks)
function ScrollToTop() {
  const { pathname } = useLocation()
  const navType = useNavigationType()
  useEffect(() => {
    if (navType !== 'POP') {
      const wrap = document.querySelector<HTMLElement>('.app-main-scroll-wrap')
      if (wrap) {
        wrap.scrollTo({ top: 0, left: 0, behavior: 'instant' })
      } else {
        window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
      }
    }
  }, [pathname, navType])
  return null
}

interface AppRoutesProps {
  mode: string
  currentDay: number | null
  onModeChange: (m: string) => void
  onDayChange: (day: number) => void
}

function AppRoutes({ mode, currentDay, onModeChange, onDayChange }: AppRoutesProps) {
  const { user, logout, isAdmin, isLoading } = useAuth()
  const { toast } = useToast()
  const location = useLocation()
  const isPractice = location.pathname === '/practice'

  // Wait for auth state to be determined before rendering routes.
  // Without this, user=null on first render causes premature redirects to /login,
  // then when cached user loads the /login route redirects to /, losing the original path.
  if (isLoading) {
    return <Loading fullScreen />
  }

  return (
    <div className="app">
      <ScrollToTop />
      {!isPractice && (
        <Header
          user={user}
          currentDay={currentDay}
          mode={mode as any}
          onLogout={() => { logout() }}
          onModeChange={onModeChange}
          onDayChange={onDayChange}
          onUserUpdate={() => {}}
        />
      )}

      <div className={isPractice ? 'practice-fullscreen' : 'app-body'}>
        {user && !isPractice && <LeftSidebar />}
        <main className={isPractice ? 'practice-fullscreen-main' : 'main'}>
          <Scrollbar className="app-main-scroll" wrapClassName="app-main-scroll-wrap">
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

              <Route
                path="/admin"
                element={
                  isAdmin ? (
                    <AdminDashboard />
                  ) : (
                    <Navigate to={user ? "/" : "/login"} replace />
                  )
                }
              />

              <Route
                path="/journal"
                element={
                  user ? (
                    <LearningJournalPage />
                  ) : (
                    <Navigate to="/login" replace />
                  )
                }
              />

              <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
            </Routes>
          </Scrollbar>
        </main>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}

      {user && !isPractice && <BottomNav />}
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
          <ToastProvider>
            <AuthProvider>
              <AppRoutes
                mode={mode}
                currentDay={currentDay}
                onModeChange={handleModeChange}
                onDayChange={handleDayChange}
              />
            </AuthProvider>
          </ToastProvider>
        </SettingsProvider>
      </AIChatProvider>
    </Router>
  )
}
