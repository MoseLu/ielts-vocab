import { Suspense, lazy, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth, useToast } from '../contexts'
import AuthPage from '../components/auth/page/AuthPage'
import PracticePage from '../components/practice/PracticePage'
import Toast from '../components/ui/Toast'
import { Loading } from '../components/ui/Loading'
import { ScrollToTop } from './ScrollToTop'
import type { PracticeMode } from '../components/layout/navigation/Header'

const AdminDashboard = lazy(() => import('../components/admin/page/AdminDashboard'))
const AIChatPanel = lazy(() => import('../components/ai-chat/page/AIChatPanel'))
const CreateCustomBookPage = lazy(() => import('../components/books/page/CreateCustomBookPage'))
const VocabBookPage = lazy(() => import('../components/books/page/VocabBookPage'))
const ErrorsPage = lazy(() => import('../components/errors/page/ErrorsPage'))
const HomePage = lazy(() => import('../components/home/page/HomePage'))
const LearningJournalPage = lazy(() => import('../components/journal/page/LearningJournalPage'))
const BottomNav = lazy(() => import('../components/layout/navigation/BottomNav'))
const GlobalWordSearch = lazy(() => import('../components/layout/navigation/GlobalWordSearch'))
const Header = lazy(() => import('../components/layout/navigation/Header'))
const LeftSidebar = lazy(() => import('../components/layout/navigation/LeftSidebar'))
const NotFoundPage = lazy(() => import('../components/not-found/page/NotFoundPage'))
const ConfusableMatchPage = lazy(() => import('../components/practice/ConfusableMatchPage'))
const ProfilePage = lazy(() => import('../components/profile/page/ProfilePage'))
const StatsPage = lazy(() => import('../components/stats/page/StatsPage'))
const TermsPage = lazy(() => import('../components/terms/page/TermsPage'))
const VocabTestPage = lazy(() => import('../components/vocab-test/page/VocabTestPage'))

interface AppRoutesProps {
  mode: string
  currentDay: number | null
  onModeChange: (mode: string) => void
  onDayChange: (day: number) => void
}

const SPECIAL_PAGES = ['/login', '/register', '/forgot-password', '/terms', '/404']
const CHROME_DEFER_MS = 1200

function GuestOnlyRoute({
  isAuthenticated,
  children,
}: {
  isAuthenticated: boolean
  children: React.ReactNode
}) {
  return isAuthenticated ? <Navigate to="/plan" replace /> : <>{children}</>
}

function AuthenticatedRoute({
  isAuthenticated,
  children,
}: {
  isAuthenticated: boolean
  children: React.ReactNode
}) {
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function RouteFallback() {
  return <Loading fullScreen />
}

function ChromeSlot({
  children,
}: {
  children: React.ReactNode
}) {
  return <Suspense fallback={null}>{children}</Suspense>
}

export function AppRoutes({
  mode,
  currentDay,
  onModeChange,
  onDayChange,
}: AppRoutesProps) {
  const { user, logout, isAdmin, isLoading } = useAuth()
  const { toast, showToast } = useToast()
  const location = useLocation()
  const isPractice = location.pathname.startsWith('/practice')
  const isSpecialPage = SPECIAL_PAGES.includes(location.pathname)
  const shouldShowBottomNav = Boolean(user) && !isPractice && !isSpecialPage
  const [chromeReady, setChromeReady] = useState(false)

  useEffect(() => {
    if (!user || isSpecialPage) {
      setChromeReady(false)
      return
    }

    if (!isPractice) {
      setChromeReady(true)
      return
    }

    setChromeReady(false)
    const timerId = window.setTimeout(() => {
      setChromeReady(true)
    }, CHROME_DEFER_MS)

    return () => {
      window.clearTimeout(timerId)
    }
  }, [isPractice, isSpecialPage, user])

  if (isLoading) {
    return <Loading fullScreen />
  }

  return (
    <div className="app">
      <ScrollToTop />

      {!isPractice && !isSpecialPage && (
        <ChromeSlot>
          <Header
            user={user}
            currentDay={currentDay}
            mode={mode as PracticeMode}
            onLogout={logout}
            onModeChange={nextMode => onModeChange(nextMode)}
            onDayChange={onDayChange}
            onUserUpdate={() => {}}
          />
        </ChromeSlot>
      )}

      <div className={isPractice || isSpecialPage ? 'practice-fullscreen' : 'app-body'}>
        {user && !isPractice && !isSpecialPage && (
          <ChromeSlot>
            <LeftSidebar />
          </ChromeSlot>
        )}

        <main className={isPractice || isSpecialPage ? 'practice-fullscreen-main' : 'main'}>
          <div className="main-view">
            <Suspense fallback={<RouteFallback />}>
              <Routes>
                <Route
                  path="/login"
                  element={(
                    <GuestOnlyRoute isAuthenticated={Boolean(user)}>
                      <AuthPage />
                    </GuestOnlyRoute>
                  )}
                />
                <Route
                  path="/register"
                  element={(
                    <GuestOnlyRoute isAuthenticated={Boolean(user)}>
                      <AuthPage />
                    </GuestOnlyRoute>
                  )}
                />
                <Route
                  path="/forgot-password"
                  element={(
                    <GuestOnlyRoute isAuthenticated={Boolean(user)}>
                      <AuthPage />
                    </GuestOnlyRoute>
                  )}
                />
                <Route path="/terms" element={<TermsPage />} />
                <Route path="/404" element={<NotFoundPage />} />
                <Route
                  path="/"
                  element={user ? <Navigate to="/plan" replace /> : <Navigate to="/login" replace />}
                />
                <Route
                  path="/plan"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <HomePage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/books"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <VocabBookPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/books/create"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <CreateCustomBookPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/practice"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <PracticePage
                        user={user ?? undefined}
                        currentDay={currentDay ?? undefined}
                        mode={mode as PracticeMode}
                        onModeChange={nextMode => onModeChange(nextMode)}
                        onDayChange={onDayChange}
                        showToast={showToast}
                      />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/practice/confusable"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <ConfusableMatchPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/errors"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <ErrorsPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/stats"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <StatsPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/profile"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <ProfilePage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/vocab-test"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <VocabTestPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/admin"
                  element={
                    isAdmin ? (
                      <AdminDashboard />
                    ) : (
                      <Navigate to={user ? '/plan' : '/login'} replace />
                    )
                  }
                />
                <Route
                  path="/journal"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <LearningJournalPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route path="*" element={<Navigate to="/404" replace />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}
      {user && !isSpecialPage && chromeReady && (
        <ChromeSlot>
          <GlobalWordSearch />
        </ChromeSlot>
      )}
      {shouldShowBottomNav && (
        <ChromeSlot>
          <BottomNav />
        </ChromeSlot>
      )}
      {user && !isSpecialPage && chromeReady && (
        <ChromeSlot>
          <AIChatPanel avoidBottomNav={shouldShowBottomNav} />
        </ChromeSlot>
      )}
    </div>
  )
}
