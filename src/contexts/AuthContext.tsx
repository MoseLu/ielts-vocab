// ── Auth Context ────────────────────────────────────────────────────────────────

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { User } from '../types'
import { STORAGE_KEYS } from '../constants'
import { apiFetch, safeParse, LoginSchema, RegisterSchema, AuthResponseSchema, UserSchema } from '../lib'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, username: string) => Promise<void>
  logout: () => void
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)
    const savedUser = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (token && savedUser) {
      // Validate stored user with Zod
      const parsed = safeParse(UserSchema, JSON.parse(savedUser))
      if (parsed.success) {
        setUser(parsed.data)
      } else {
        // Corrupted storage — clear it
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN)
        localStorage.removeItem(STORAGE_KEYS.AUTH_USER)
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    // Validate form input with Zod
    const formResult = safeParse(LoginSchema, { email, password })
    if (!formResult.success) {
      throw new Error(formResult.errors.join('；'))
    }

    const raw = await apiFetch<unknown>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })

    // Validate API response with Zod
    const responseResult = safeParse(AuthResponseSchema, raw)
    if (!responseResult.success) {
      throw new Error('服务器响应格式错误')
    }

    const { user: validatedUser, token } = responseResult.data

    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(validatedUser))
    setUser(validatedUser)
  }, [])

  const register = useCallback(async (email: string, password: string, username: string) => {
    // Validate form input with Zod
    const formResult = safeParse(RegisterSchema, { email, password, username, confirmPassword: password })
    if (!formResult.success) {
      throw new Error(formResult.errors.join('；'))
    }

    const raw = await apiFetch<unknown>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, username }),
    })

    // Validate API response with Zod
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
    setUser(null)
  }, [])

  const updateUser = useCallback((updatedUser: User) => {
    setUser(updatedUser)
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(updatedUser))
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
      updateUser,
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
