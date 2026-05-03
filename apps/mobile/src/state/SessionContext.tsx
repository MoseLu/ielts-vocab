import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { CORE_STORAGE_KEYS, readJson, UserSchema, type AppUser } from '@ielts-vocab/app-core'
import { mobileApiClient, mobileAuthClient } from '../api/mobileApi'
import { asyncAppStorage } from '../storage/mobileStorage'

type SessionContextValue = {
  isAuthenticated: boolean
  isLoading: boolean
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
  user: AppUser | null
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function hydrateSession() {
      const cachedUser = await readJson<AppUser | null>(asyncAppStorage, CORE_STORAGE_KEYS.authUser, null)
      if (active && cachedUser) setUser(cachedUser)
      try {
        const payload = await mobileApiClient.json<{ user?: unknown }>('/api/auth/me')
        const parsedUser = UserSchema.safeParse(payload.user)
        if (active) setUser(parsedUser.success ? parsedUser.data : null)
      } catch {
        if (active && !cachedUser) setUser(null)
      } finally {
        if (active) setIsLoading(false)
      }
    }
    void hydrateSession()
    return () => {
      active = false
    }
  }, [])

  const value = useMemo<SessionContextValue>(() => ({
    isAuthenticated: Boolean(user),
    isLoading,
    async login(identifier, password) {
      setIsLoading(true)
      try {
        const session = await mobileAuthClient.login(identifier, password)
        setUser(session.user)
      } finally {
        setIsLoading(false)
      }
    },
    async logout() {
      setIsLoading(true)
      try {
        await mobileAuthClient.logout()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    },
    user,
  }), [isLoading, user])

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
  const value = useContext(SessionContext)
  if (!value) throw new Error('useSession must be used inside SessionProvider')
  return value
}
