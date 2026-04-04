// ── App Router ─────────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigationType } from 'react-router-dom'
import { AuthProvider, useAuth, useToast, ToastProvider, AIChatProvider } from './contexts'
import { SettingsProvider } from './contexts'
import Header from './components/Header'
import LeftSidebar from './components/LeftSidebar'
import BottomNav from './components/BottomNav'
import AuthPage from './components/AuthPage'
import { Loading } from './components/ui/Loading'
import HomePage from './components/HomePage'
import PracticePage from './components/practice/PracticePage'
import ConfusableMatchPage from './components/practice/ConfusableMatchPage'
import VocabBookPage from './components/VocabBookPage'
import ErrorsPage from './components/ErrorsPage'
import StatsPage from './components/StatsPage'
import ProfilePage from './components/ProfilePage'
import AIChatPanel from './components/AIChatPanel'
import VocabTestPage from './components/VocabTestPage'
import AdminDashboard from './components/AdminDashboard'
import LearningJournalPage from './components/LearningJournalPage'
import NotFoundPage from './components/NotFoundPage'
import TermsPage from './components/TermsPage'
import Toast from './components/Toast'

// Reset scroll to top on every PUSH navigation (tab switches, link clicks)
function ScrollToTop() {
  const { pathname } = useLocation()
  const navType = useNavigationType()
  useEffect(() => {
    if (navType !== 'POP') {
      const scrollTargets = document.querySelectorAll<HTMLElement>(
        '.page__scroll, .page-content, .page-shell-body, .stats-page-scroll, .errors-content-scroll, .journal-doc-list, .journal-doc-body, .journal-doc-main-scroll',
      )
      if (scrollTargets.length > 0) {
        scrollTargets.forEach(target => target.scrollTo({ top: 0, left: 0, behavior: 'instant' }))
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
  const isPractice = location.pathname.startsWith('/practice')
  const specialPages = ['/login', '/register', '/forgot-password', '/terms', '/404']
  const isSpecialPage = specialPages.includes(location.pathname)

  // Wait for auth state to be determined before rendering routes.
  // Without this, user=null on first render causes premature redirects to /login,
  // then when cached user loads the /login route redirects to /, losing the original path.
  if (isLoading) {
    return <Loading fullScreen />
  }

  return (
    <div className="app">
      <ScrollToTop />
      {!isPractice && !isSpecialPage && (
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

      <div className={isPractice || isSpecialPage ? 'practice-fullscreen' : 'app-body'}>
        {user && !isPractice && !isSpecialPage && <LeftSidebar />}
        <main className={isPractice || isSpecialPage ? 'practice-fullscreen-main' : 'main'}>
          <div className="main-view">
            <Routes>
              <Route
                path="/login"
                element={
                  user ? (
                    <Navigate to="/plan" replace />
                  ) : (
                    <AuthPage />
                  )
                }
              />

              <Route
                path="/register"
                element={
                  user ? (
                    <Navigate to="/plan" replace />
                  ) : (
                    <AuthPage />
                  )
                }
              />

              <Route
                path="/forgot-password"
                element={
                  user ? (
                    <Navigate to="/plan" replace />
                  ) : (
                    <AuthPage />
                  )
                }
              />

              <Route path="/terms" element={<TermsPage />} />

              <Route path="/404" element={<NotFoundPage />} />

              <Route
                path="/"
                element={
                  user ? (
                    <Navigate to="/plan" replace />
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
                path="/books"
                element={
                  user ? (
                    <VocabBookPage />
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
                    <Navigate to={user ? "/plan" : "/login"} replace />
                  )
                }
              />

              <Route
                path="/practice/confusable"
                element={
                  user ? (
                    <ConfusableMatchPage />
                  ) : (
                    <Navigate to="/login" replace />
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

              <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </div>
        </main>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}

      {user && !isPractice && !isSpecialPage && <BottomNav />}
      {user && !isSpecialPage && <AIChatPanel />}
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

  useEffect(() => {
    const handlePracticeModeRequest = (event: Event) => {
      const requestedMode = (event as CustomEvent<{ mode?: string }>).detail?.mode
      if (requestedMode) {
        handleModeChange(requestedMode)
      }
    }

    window.addEventListener('practice-mode-request', handlePracticeModeRequest)
    return () => {
      window.removeEventListener('practice-mode-request', handlePracticeModeRequest)
    }
  }, [])

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
