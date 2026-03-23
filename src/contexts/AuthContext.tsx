// ── Auth Context ────────────────────────────────────────────────────────────────
// Token is stored exclusively in HttpOnly cookies (managed by the server).
// Only the user object is kept in localStorage for fast UI hydration on reload.
// On page load we call GET /api/auth/me to validate the cookie and get fresh data.

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { User } from '../types'
import { STORAGE_KEYS } from '../constants'
import { apiFetch, safeParse, LoginSchema, RegisterSchema, UserSchema } from '../lib'

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

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Persist only user data (not the token) for instant hydration
  const _saveUser = (u: User) => {
    setUser(u)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(u))
  }

  const _clearUser = () => {
    setUser(null)
    localStorage.removeItem(STORAGE_KEYS.AUTH_USER)
    localStorage.removeItem('my_books')
  }

  // On mount: validate cookie with the server; fall back to cached user while loading
  useEffect(() => {
    const cached = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (cached) {
      try {
        const raw = JSON.parse(cached)
        const parsed = safeParse(UserSchema, raw)
        setUser(parsed.success ? parsed.data : {
          id: raw.id ?? 0, email: raw.email || '', username: raw.username,
          avatar_url: raw.avatar_url ?? null, is_admin: raw.is_admin ?? false,
          created_at: raw.created_at,
        })
      } catch { /* ignore */ }
    }

    // Verify the cookie is still valid and pull fresh user data
    apiFetch<{ user: unknown }>('/api/auth/me')
      .then(data => {
        const parsed = safeParse(UserSchema, data.user)
        if (parsed.success) _saveUser(parsed.data)
      })
      .catch(() => {
        // Cookie invalid / expired — clear stale user
        _clearUser()
      })
      .finally(() => setIsLoading(false))
  }, [])

  // Listen for session-expired events fired by apiFetch after a failed refresh
  useEffect(() => {
    const handler = () => _clearUser()
    window.addEventListener('auth:session-expired', handler)
    return () => window.removeEventListener('auth:session-expired', handler)
  }, [])

  const login = useCallback(async (identifier: string, password: string) => {
    const formResult = safeParse(LoginSchema, { identifier, password })
    if (!formResult.success) throw new Error(formResult.errors.join('；'))

    const raw = await apiFetch<{ user: unknown }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: identifier, password }),
    })

    // Server sets HttpOnly cookies — we only persist the user object
    const parsed = safeParse(UserSchema, raw.user)
    if (!parsed.success) throw new Error('服务器响应格式错误')
    _saveUser(parsed.data)
  }, [])

  const register = useCallback(async (username: string, password: string, email?: string) => {
    const formResult = safeParse(RegisterSchema, {
      username, email: email || '', password, confirmPassword: password,
    })
    if (!formResult.success) throw new Error(formResult.errors.join('；'))

    const raw = await apiFetch<{ user: unknown }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email: email || '' }),
    })

    const parsed = safeParse(UserSchema, raw.user)
    if (!parsed.success) throw new Error('服务器响应格式错误')
    _saveUser(parsed.data)
  }, [])

  const logout = useCallback(async () => {
    // Ask the server to revoke tokens and clear cookies
    await apiFetch('/api/auth/logout', { method: 'POST' }).catch(() => {})
    _clearUser()
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
