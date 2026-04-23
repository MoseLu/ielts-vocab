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
const ExamAttemptPage = lazy(() => import('../components/exams/page/ExamAttemptPage'))
const ExamsLibraryPage = lazy(() => import('../components/exams/page/ExamsLibraryPage'))
const GameCampaignPage = lazy(() => import('../components/game/page/GameCampaignPage'))
const HomePage = lazy(() => import('../components/home/page/HomePage'))
const LearningJournalPage = lazy(() => import('../components/journal/page/LearningJournalPage'))
const BottomNav = lazy(() => import('../components/layout/navigation/BottomNav'))
const GlobalWordSearch = lazy(() => import('../components/layout/navigation/GlobalWordSearch'))
const Header = lazy(() => import('../components/layout/navigation/Header'))
const LeftSidebar = lazy(() => import('../components/layout/navigation/LeftSidebar'))
const SelectionWordLookup = lazy(() => import('../components/layout/navigation/SelectionWordLookup'))
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

function normalizeHeaderMode(mode: string): PracticeMode {
  return ['smart', 'listening', 'meaning', 'dictation', 'follow', 'radio'].includes(mode)
    ? (mode as PracticeMode)
    : 'smart'
}

function PracticeRouteElement({
  isAuthenticated,
  user,
  currentDay,
  mode,
  onModeChange,
  onDayChange,
  showToast,
}: {
  isAuthenticated: boolean
  user: unknown
  currentDay: number | null
  mode: string
  onModeChange: (mode: string) => void
  onDayChange: (day: number) => void
  showToast: (message: string, type?: 'info' | 'success' | 'error') => void
}) {
  const location = useLocation()
  const searchParams = new URLSearchParams(location.search)
  if (searchParams.get('mode') === 'game') {
    searchParams.delete('mode')
    const query = searchParams.toString()
    return <Navigate to={`/game${query ? `?${query}` : ''}`} replace />
  }

  return (
    <AuthenticatedRoute isAuthenticated={isAuthenticated}>
      <PracticePage
        user={user ?? undefined}
        currentDay={currentDay ?? undefined}
        mode={mode as PracticeMode}
        onModeChange={nextMode => onModeChange(nextMode)}
        onDayChange={onDayChange}
        showToast={showToast}
      />
    </AuthenticatedRoute>
  )
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
  const isGame = location.pathname.startsWith('/game')
  const isExamAttemptSurface = /^\/exams\/\d+$/.test(location.pathname)
  const isPracticeSurface = isPractice || isGame || isExamAttemptSurface
  const isSpecialPage = SPECIAL_PAGES.includes(location.pathname)
  const shouldShowBottomNav = Boolean(user) && !isPracticeSurface && !isSpecialPage
  const [chromeReady, setChromeReady] = useState(false)

  useEffect(() => {
    if (!user || isSpecialPage) {
      setChromeReady(false)
      return
    }

    if (!isPracticeSurface) {
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
  }, [isPracticeSurface, isSpecialPage, user])

  if (isLoading) {
    return <Loading fullScreen />
  }

  return (
    <div className="app">
      <ScrollToTop />

      {!isPracticeSurface && !isSpecialPage && (
        <ChromeSlot>
          <Header
            user={user}
            currentDay={currentDay}
            mode={normalizeHeaderMode(mode)}
            onLogout={logout}
            onModeChange={nextMode => onModeChange(nextMode)}
            onDayChange={onDayChange}
            onUserUpdate={() => {}}
          />
        </ChromeSlot>
      )}

      <div className={isPracticeSurface || isSpecialPage ? 'practice-fullscreen' : 'app-body'}>
        {user && !isPracticeSurface && !isSpecialPage && (
          <ChromeSlot>
            <LeftSidebar />
          </ChromeSlot>
        )}

        <main className={isPracticeSurface || isSpecialPage ? 'practice-fullscreen-main' : 'main'}>
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
                    <PracticeRouteElement
                      isAuthenticated={Boolean(user)}
                      user={user}
                      currentDay={currentDay}
                      mode={mode}
                      onModeChange={onModeChange}
                      onDayChange={onDayChange}
                      showToast={showToast}
                    />
                  )}
                />
                <Route
                  path="/game"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <GameCampaignPage surface="map" />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/game/mission"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <GameCampaignPage surface="mission" />
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
                  path="/exams"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <ExamsLibraryPage />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/exams/:paperId"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <ExamAttemptPage />
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
                  path="/speaking"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <Navigate to="/game" replace />
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
          <SelectionWordLookup />
        </ChromeSlot>
      )}
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
