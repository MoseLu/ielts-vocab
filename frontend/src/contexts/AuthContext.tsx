// ── Auth Context ────────────────────────────────────────────────────────────────
// Token is stored exclusively in HttpOnly cookies (managed by the server).
// Only the user object is kept in localStorage for fast UI hydration on reload.
// On page load we call GET /api/auth/me to validate the cookie and get fresh data.

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import type { User } from '../types'
import { STORAGE_KEYS } from '../constants'
import {
  apiFetch,
  apiRequest,
  refreshAuthSession,
  safeParse,
  LoginSchema,
  RegisterSchema,
  UserSchema,
  setAuthSessionActive,
} from '../lib'
import { useToast } from './ToastContext'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isAdmin: boolean
  isLoading: boolean
  login: (identifier: string, password: string) => Promise<void>
  register: (username: string, password: string, email?: string) => Promise<void>
  logout: () => Promise<void>
  updateUser: (user: User) => void
  sendBindEmailCode: (email: string) => Promise<void>
  bindEmail: (email: string, code: string) => Promise<void>
  sendForgotPasswordCode: (email: string) => Promise<void>
  resetPassword: (email: string, code: string, password: string) => Promise<void>
}

interface AuthSessionProbeResponse {
  user: unknown | null
  access_expires_in?: number
  authenticated?: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const _refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { showToast } = useToast()

  /** Schedule a proactive token refresh 60 s before the access token expires. */
  const _scheduleRefresh = useCallback((expiresInSeconds: number) => {
    if (_refreshTimer.current) clearTimeout(_refreshTimer.current)
    const delay = Math.max(0, (expiresInSeconds - 60) * 1000)
    _refreshTimer.current = setTimeout(async () => {
      try {
        const data = await apiFetch<{ user: unknown; access_expires_in?: number }>(
          '/api/auth/refresh', { method: 'POST' }
        )
        const parsed = safeParse(UserSchema, data.user)
        if (parsed.success) {
          setUser(parsed.data)
          localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(parsed.data))
        }
        if (data.access_expires_in) _scheduleRefresh(data.access_expires_in)
      } catch {
        // Proactive refresh failed — reactive refresh (on next 401) will take over
      }
    }, delay)
  }, [])

  // Persist only user data (not the token) for instant hydration
  const _saveUser = (u: User) => {
    setAuthSessionActive(true)
    setUser(u)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(u))
  }

  const _clearUser = () => {
    if (_refreshTimer.current) {
      clearTimeout(_refreshTimer.current)
      _refreshTimer.current = null
    }
    setAuthSessionActive(false)
    setUser(null)
    localStorage.removeItem(STORAGE_KEYS.AUTH_USER)
    localStorage.removeItem('my_books')
  }

  const _applySessionProbe = useCallback((data: AuthSessionProbeResponse) => {
    if (!data.user) {
      return false
    }
    const parsed = safeParse(UserSchema, data.user)
    if (!parsed.success) {
      return false
    }
    _saveUser(parsed.data)
    if (data.access_expires_in) _scheduleRefresh(data.access_expires_in)
    return true
  }, [_scheduleRefresh])

  // On mount: validate cookie with the server; fall back to cached user while loading
  useEffect(() => {
    const cached = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (!cached) {
      setAuthSessionActive(false)
      // No cached user means not logged in — skip server round-trip to avoid
      // a spurious 401 appearing in the browser console.
      setIsLoading(false)
      return
    }

    try {
      const raw = JSON.parse(cached)
      const parsed = safeParse(UserSchema, raw)
      setAuthSessionActive(true)
      setUser(parsed.success ? parsed.data : {
        id: raw.id ?? 0, email: raw.email || '', username: raw.username,
        avatar_url: raw.avatar_url ?? null, is_admin: raw.is_admin ?? false,
        created_at: raw.created_at,
      })
    } catch { /* ignore */ }

    // Verify the cookie is still valid and pull fresh user data
    apiFetch<AuthSessionProbeResponse>('/api/auth/me')
      .then(async data => {
        if (_applySessionProbe(data)) {
          return
        }

        const refreshResult = await refreshAuthSession()
        if (refreshResult === 'auth_failed') {
          _clearUser()
          return
        }

        if (refreshResult === 'temporarily_unavailable') {
          return
        }

        const recovered = await apiFetch<AuthSessionProbeResponse>('/api/auth/me')
        if (!_applySessionProbe(recovered)) {
          _clearUser()
        }
      })
      .catch((err: Error) => {
        // Only clear session on explicit auth failure (401 / token expired).
        // The 'auth:session-expired' event from apiFetch already handles the
        // 401 case, so this catch mainly guards transient network / server
        // errors — for those we keep the cached user so the UI doesn't
        // unexpectedly redirect to login when the backend restarts briefly.
        const isAuthFailure =
          err.message.includes('登录已过期') ||
          err.message.includes('session-expired')
        if (isAuthFailure) {
          _clearUser()
        }
      })
      .finally(() => setIsLoading(false))
  }, [_applySessionProbe])  // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for session-expired events fired by apiFetch after a failed refresh
  useEffect(() => {
    const handler = () => {
      _clearUser()
      showToast('登录已过期，请重新登录', 'error')
    }
    window.addEventListener('auth:session-expired', handler)
    return () => window.removeEventListener('auth:session-expired', handler)
  }, [showToast])

  const login = useCallback(async (identifier: string, password: string) => {
    const formResult = safeParse(LoginSchema, { identifier, password })
    if (!formResult.success) throw new Error(formResult.errors.join('；'))

    const raw = await apiFetch<{ user: unknown; access_expires_in?: number }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: identifier, password }),
    })

    // Server sets HttpOnly cookies — we only persist the user object
    const parsed = safeParse(UserSchema, raw.user)
    if (!parsed.success) throw new Error('服务器响应格式错误')
    _saveUser(parsed.data)
    if (raw.access_expires_in) _scheduleRefresh(raw.access_expires_in)
  }, [_scheduleRefresh])

  const register = useCallback(async (username: string, password: string, email?: string) => {
    const formResult = safeParse(RegisterSchema, {
      username, email: email || '', password, confirmPassword: password,
    })
    if (!formResult.success) throw new Error(formResult.errors.join('；'))

    const raw = await apiFetch<{ user: unknown; access_expires_in?: number }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email: email || '' }),
    })

    const parsed = safeParse(UserSchema, raw.user)
    if (!parsed.success) throw new Error('服务器响应格式错误')
    _saveUser(parsed.data)
    if (raw.access_expires_in) _scheduleRefresh(raw.access_expires_in)
  }, [_scheduleRefresh])

  const logout = useCallback(async () => {
    _clearUser()
    // Ask the server to revoke tokens and clear cookies, but do not trigger refresh logic
    await apiRequest('/api/auth/logout', {
      method: 'POST',
      skipAuthRefresh: true,
    }).catch(() => {})
  }, [])

  const updateUser = useCallback((updatedUser: User) => {
    _saveUser(updatedUser)
  }, [])

  const sendBindEmailCode = useCallback(async (email: string) => {
    await apiFetch<unknown>('/api/auth/send-code', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }, [])

  const bindEmail = useCallback(async (email: string, code: string) => {
    const raw = await apiFetch<{ user: unknown }>('/api/auth/bind-email', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    })
    const parsed = safeParse(UserSchema, raw.user)
    if (parsed.success) _saveUser(parsed.data)
  }, [])

  const sendForgotPasswordCode = useCallback(async (email: string) => {
    await apiFetch<unknown>('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }, [])

  const resetPassword = useCallback(async (email: string, code: string, password: string) => {
    await apiFetch<unknown>('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email, code, password }),
    })
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isAdmin: !!(user?.is_admin),
      isLoading,
      login,
      register,
      logout,
      updateUser,
      sendBindEmailCode,
      bindEmail,
      sendForgotPasswordCode,
      resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
