import { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import PracticePage from '../components/practice/PracticePage'
import type { PracticeMode } from '../features/practice/types'
import { AuthenticatedRoute } from './routeGuards'

const PRACTICE_ROUTE_QUERY_MODES = new Set<PracticeMode>([
  'smart',
  'listening',
  'meaning',
  'dictation',
  'follow',
  'radio',
  'quickmemory',
])

function normalizePracticeRouteMode(value: string | null): PracticeMode | null {
  return PRACTICE_ROUTE_QUERY_MODES.has(value as PracticeMode)
    ? value as PracticeMode
    : null
}

export function PracticeRouteElement({
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
        mode={routeMode ?? (mode as PracticeMode)}
        onModeChange={nextMode => onModeChange(nextMode)}
        onDayChange={onDayChange}
        showToast={showToast}
      />
    </AuthenticatedRoute>
  )
}
