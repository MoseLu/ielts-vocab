import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

export function GuestOnlyRoute({
  isAuthenticated,
  children,
}: {
  isAuthenticated: boolean
  children: ReactNode
}) {
  return isAuthenticated ? <Navigate to="/plan" replace /> : <>{children}</>
}

export function AuthenticatedRoute({
  isAuthenticated,
  children,
}: {
  isAuthenticated: boolean
  children: ReactNode
}) {
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}
