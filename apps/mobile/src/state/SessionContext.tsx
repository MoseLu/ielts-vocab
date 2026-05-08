import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { AppUser } from '@ielts-vocab/app-core'
import { mobileApiClient, mobileAuthClient } from '../api/mobileApi'
import { hydrateStoredSession } from './sessionHydration'
import { asyncAppStorage } from '../storage/mobileStorage'

type SessionContextValue = {
  isAuthenticated: boolean
  isHydrating: boolean
  isLoading: boolean
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
  user: AppUser | null
  wechatLogin: (code: string, state?: string) => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null)
  const [isHydrating, setIsHydrating] = useState(true)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    let active = true
    async function hydrateSession() {
      try {
        const hydratedUser = await hydrateStoredSession(asyncAppStorage, mobileApiClient)
        if (active) setUser(hydratedUser)
      } finally {
        if (active) setIsHydrating(false)
      }
    }
    void hydrateSession()
    return () => {
      active = false
    }
  }, [])

  const value = useMemo<SessionContextValue>(() => ({
    isAuthenticated: Boolean(user),
    isHydrating,
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
    async wechatLogin(code, state) {
      setIsLoading(true)
      try {
        const session = await mobileAuthClient.wechatLogin(code, state)
        setUser(session.user)
      } finally {
        setIsLoading(false)
      }
    },
  }), [isHydrating, isLoading, user])

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
  const value = useContext(SessionContext)
  if (!value) throw new Error('useSession must be used inside SessionProvider')
  return value
}
