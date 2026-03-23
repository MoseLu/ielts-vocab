// ── Auth Context ────────────────────────────────────────────────────────────────

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { User } from '../types'
import { STORAGE_KEYS } from '../constants'
import { apiFetch, safeParse, LoginSchema, RegisterSchema, AuthResponseSchema, UserSchema } from '../lib'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isAdmin: boolean
  isLoading: boolean
  login: (identifier: string, password: string) => Promise<void>
  register: (username: string, password: string, email?: string) => Promise<void>
  logout: () => void
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

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)
    const savedUser = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (!token) {
      setIsLoading(false)
      return
    }
    // Fetch latest user info from server (includes is_admin)
    apiFetch<{ user: unknown }>('/api/auth/me')
      .then(data => {
        const parsed = safeParse(UserSchema, data.user)
        if (parsed.success) {
          setUser(parsed.data)
          localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(parsed.data))
        } else if (savedUser) {
          // Fallback to localStorage if /me fails
          const raw = JSON.parse(savedUser)
          setUser({
            id: raw.id ?? 0,
            email: raw.email || '',
            username: raw.username,
            avatar_url: raw.avatar_url ?? null,
            is_admin: raw.is_admin ?? false,
            created_at: raw.created_at,
          })
        }
      })
      .catch(() => {
        // If /me fails, try localStorage fallback
        if (savedUser) {
          try {
            const raw = JSON.parse(savedUser)
            setUser({
              id: raw.id ?? 0,
              email: raw.email || '',
              username: raw.username,
              avatar_url: raw.avatar_url ?? null,
              is_admin: raw.is_admin ?? false,
              created_at: raw.created_at,
            })
          } catch {
            localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN)
            localStorage.removeItem(STORAGE_KEYS.AUTH_USER)
          }
        }
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (identifier: string, password: string) => {
    localStorage.removeItem('my_books')
    const formResult = safeParse(LoginSchema, { identifier, password })
    if (!formResult.success) {
      throw new Error(formResult.errors.join('；'))
    }

    const raw = await apiFetch<unknown>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: identifier, password }),
    })

    const responseResult = safeParse(AuthResponseSchema, raw)
    if (!responseResult.success) {
      throw new Error('服务器响应格式错误')
    }

    const { user: validatedUser, token } = responseResult.data
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(validatedUser))
    setUser(validatedUser)
  }, [])

  const register = useCallback(async (username: string, password: string, email?: string) => {
    localStorage.removeItem('my_books')
    const formResult = safeParse(RegisterSchema, { username, email: email || '', password, confirmPassword: password })
    if (!formResult.success) {
      throw new Error(formResult.errors.join('；'))
    }

    const raw = await apiFetch<unknown>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email: email || '' }),
    })

    const responseResult = safeParse(AuthResponseSchema, raw)
    if (!responseResult.success) {
      throw new Error('服务器响应格式错误')
    }

    const { user: validatedUser, token } = responseResult.data
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(validatedUser))
    setUser(validatedUser)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.AUTH_USER)
    localStorage.removeItem('my_books')
    setUser(null)
  }, [])

  const updateUser = useCallback((updatedUser: User) => {
    setUser(updatedUser)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(updatedUser))
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
    if (parsed.success) {
      setUser(parsed.data)
      localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(parsed.data))
    }
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
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
