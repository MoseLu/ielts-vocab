import { Suspense, lazy, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { useAuth, useToast } from '../contexts'
import AuthPage from '../components/auth/page/AuthPage'
import CreateCustomBookPage from '../components/books/page/CreateCustomBookPage'
import ErrorsPage from '../components/errors/page/ErrorsPage'
import PracticePage from '../components/practice/PracticePage'
import Toast from '../components/ui/Toast'
import { Loading } from '../components/ui/Loading'
import { ScrollToTop } from './ScrollToTop'
import LeftSidebar from '../components/layout/navigation/LeftSidebar'
import AdminDashboard from '../components/admin/page/AdminDashboard'
import ExamsLibraryPage from '../components/exams/page/ExamsLibraryPage'
import GameCampaignPage from '../components/game/page/GameCampaignPage'
import HomePage from '../components/home/page/HomePage'
import LearningJournalPage from '../components/journal/page/LearningJournalPage'
import NotFoundPage from '../components/not-found/page/NotFoundPage'
import ConfusableMatchPage from '../components/practice/ConfusableMatchPage'
import ProfilePage from '../components/profile/page/ProfilePage'
import StatsPage from '../components/stats/page/StatsPage'
import TermsPage from '../components/terms/page/TermsPage'
import VocabBookPage from '../components/books/page/VocabBookPage'
import VocabTestPage from '../components/vocab-test/page/VocabTestPage'
import { prdUiAsset } from '../components/practice/page/game-mode/prdUiAssets'
import { GAME_THEME_SELECT_CARD_URLS } from '../lib/gameThemeCardAssets'
import type { PracticeMode as HeaderPracticeMode } from '../components/layout/navigation/Header'
import type { PracticeMode as PracticePageMode } from '../components/practice/types'

const AIChatPanel = lazy(() => import('../components/ai-chat/page/AIChatPanel'))
const ExamAttemptPage = lazy(() => import('../components/exams/page/ExamAttemptPage'))
const BottomNav = lazy(() => import('../components/layout/navigation/BottomNav'))
const GlobalWordSearch = lazy(() => import('../components/layout/navigation/GlobalWordSearch'))
const Header = lazy(() => import('../components/layout/navigation/Header'))
const SelectionWordLookup = lazy(() => import('../components/layout/navigation/SelectionWordLookup'))

interface AppRoutesProps {
  mode: string
  currentDay: number | null
  onModeChange: (mode: string) => void
  onDayChange: (day: number) => void
}

const SPECIAL_PAGES = ['/login', '/register', '/forgot-password', '/terms', '/404']
const CHROME_DEFER_MS = 1200
const DEFAULT_GAME_THEME_ID = 'study-campus'

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

function preloadImage(href: string, type?: string) {
  if (typeof document === 'undefined' || !href) return
  const existing = Array.from(
    document.head.querySelectorAll<HTMLLinkElement>('link[rel="preload"][as="image"]'),
  ).some(link => link.href === new URL(href, window.location.href).href)
  if (existing) return
  const link = document.createElement('link')
  link.rel = 'preload'
  link.as = 'image'
  link.href = href
  if (type) link.type = type
  document.head.appendChild(link)
}

function preloadGameRouteAssets(pathname: string) {
  if (pathname === '/game/themes') {
    GAME_THEME_SELECT_CARD_URLS.forEach(url => preloadImage(url, 'image/webp'))
  }
  if (pathname.includes('/mission')) {
    preloadImage(prdUiAsset.templates.wordMission, 'image/avif')
  }
  if (pathname === '/game' || /^\/game\/themes\/[^/]+$/.test(pathname)) {
    preloadImage(prdUiAsset.templates.wordChainMap, 'image/avif')
  }
}

function ChromeSlot({
  children,
}: {
  children: React.ReactNode
}) {
  return <Suspense fallback={null}>{children}</Suspense>
}

const PRACTICE_ROUTE_QUERY_MODES = new Set<PracticePageMode>([
  'smart',
  'listening',
  'meaning',
  'dictation',
  'follow',
  'radio',
  'quickmemory',
])

function normalizeHeaderMode(mode: string): HeaderPracticeMode {
  return ['smart', 'listening', 'meaning', 'dictation', 'follow', 'radio'].includes(mode)
    ? (mode as HeaderPracticeMode)
    : 'smart'
}

function normalizePracticeRouteMode(value: string | null): PracticePageMode | null {
  return PRACTICE_ROUTE_QUERY_MODES.has(value as PracticePageMode)
    ? value as PracticePageMode
    : null
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
  const routeMode = normalizePracticeRouteMode(searchParams.get('mode'))

  useEffect(() => {
    if (!routeMode || routeMode === mode) return
    onModeChange(routeMode)
  }, [mode, onModeChange, routeMode])

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
        mode={routeMode ?? (mode as PracticePageMode)}
        onModeChange={nextMode => onModeChange(nextMode)}
        onDayChange={onDayChange}
        showToast={showToast}
      />
    </AuthenticatedRoute>
  )
}

function GameRouteElement({ surface }: { surface: 'map' | 'mission' }) {
  const { themeId } = useParams()
  return <GameCampaignPage surface={surface} themeId={themeId} />
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
  const isLegacySpeakingRoute = location.pathname === '/speaking'
  const isPracticeSurface = isPractice || isGame || isExamAttemptSurface || isLegacySpeakingRoute
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

  useEffect(() => {
    preloadGameRouteAssets(location.pathname)
  }, [location.pathname])

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
          <LeftSidebar />
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
                      <GameCampaignPage surface="map" themeId={DEFAULT_GAME_THEME_ID} />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/game/themes"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <GameCampaignPage surface="themes" />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/game/themes/:themeId"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <GameRouteElement surface="map" />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/game/themes/:themeId/mission"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <GameRouteElement surface="mission" />
                    </AuthenticatedRoute>
                  )}
                />
                <Route
                  path="/game/mission"
                  element={(
                    <AuthenticatedRoute isAuthenticated={Boolean(user)}>
                      <GameCampaignPage surface="mission" themeId={DEFAULT_GAME_THEME_ID} />
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
