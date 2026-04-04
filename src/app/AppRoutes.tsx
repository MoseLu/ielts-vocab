import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth, useToast } from '../contexts'
import AdminDashboard from '../components/admin/page/AdminDashboard'
import AIChatPanel from '../components/ai-chat/page/AIChatPanel'
import AuthPage from '../components/auth/page/AuthPage'
import VocabBookPage from '../components/books/page/VocabBookPage'
import ErrorsPage from '../components/errors/page/ErrorsPage'
import HomePage from '../components/home/page/HomePage'
import LearningJournalPage from '../components/journal/page/LearningJournalPage'
import BottomNav from '../components/layout/navigation/BottomNav'
import Header, { type PracticeMode } from '../components/layout/navigation/Header'
import LeftSidebar from '../components/layout/navigation/LeftSidebar'
import NotFoundPage from '../components/not-found/page/NotFoundPage'
import PracticePage from '../components/practice/PracticePage'
import ConfusableMatchPage from '../components/practice/ConfusableMatchPage'
import ProfilePage from '../components/profile/page/ProfilePage'
import StatsPage from '../components/stats/page/StatsPage'
import TermsPage from '../components/terms/page/TermsPage'
import Toast from '../components/ui/Toast'
import { Loading } from '../components/ui/Loading'
import VocabTestPage from '../components/vocab-test/page/VocabTestPage'
import { ScrollToTop } from './ScrollToTop'

interface AppRoutesProps {
  mode: string
  currentDay: number | null
  onModeChange: (mode: string) => void
  onDayChange: (day: number) => void
}

const SPECIAL_PAGES = ['/login', '/register', '/forgot-password', '/terms', '/404']

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

export function AppRoutes({
  mode,
  currentDay,
  onModeChange,
  onDayChange,
}: AppRoutesProps) {
  const { user, logout, isAdmin, isLoading } = useAuth()
  const { toast } = useToast()
  const location = useLocation()
  const isPractice = location.pathname.startsWith('/practice')
  const isSpecialPage = SPECIAL_PAGES.includes(location.pathname)

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
          mode={mode as PracticeMode}
          onLogout={logout}
          onModeChange={nextMode => onModeChange(nextMode)}
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
                path="/practice"
                element={(
                  <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                    <PracticePage
                      currentDay={currentDay ?? undefined}
                      mode={mode as PracticeMode}
                      onModeChange={nextMode => onModeChange(nextMode)}
                      onDayChange={onDayChange}
                      showToast={() => {}}
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
          </div>
        </main>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}
      {user && !isPractice && !isSpecialPage && <BottomNav />}
      {user && !isSpecialPage && <AIChatPanel />}
    </div>
  )
}
