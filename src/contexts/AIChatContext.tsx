import React, { createContext, useContext, useState, useCallback } from 'react'
import type { LearningContext } from '../types'

// ── Global store for cross-module context logging ────────────────────────────────
// Any component can import this and call setGlobalLearningContext(ctx)
// The AIChatPanel will pick it up via its useAIChat hook and include it in requests.

let _currentContext: LearningContext = {}

export function setGlobalLearningContext(ctx: Partial<LearningContext>) {
  _currentContext = { ..._currentContext, ...ctx }
  // Also push into the React state so useAIChat's buildContext picks it up immediately
  _setContextRef(_currentContext)
}

export function clearGlobalLearningContext() {
  _currentContext = {}
  _setContextRef({})
}

export function getGlobalLearningContext(): LearningContext {
  return _currentContext
}

// Internal ref to the React state setter — set by the provider on mount
let _setContextRef: ((ctx: LearningContext) => void) | null = null

interface AIChatContextValue {
  context: LearningContext
  setContext: (ctx: Partial<LearningContext>) => void
}

const AIChatContext = createContext<AIChatContextValue | null>(null)

export function AIChatProvider({ children }: { children: React.ReactNode }) {
  const [context, setContextState] = useState<LearningContext>({})

  // Register the setter so setGlobalLearningContext can trigger re-renders
  _setContextRef = (ctx: LearningContext) => {
    setContextState(ctx)
  }

  const setContext = useCallback((ctx: Partial<LearningContext>) => {
    const next = { ..._currentContext, ...ctx }
    _currentContext = next
    setContextState(next)
  }, [])

  return (
    <AIChatContext.Provider value={{ context, setContext }}>
      {children}
    </AIChatContext.Provider>
  )
}

export function useAIChatContext() {
  const ctx = useContext(AIChatContext)
  if (!ctx) throw new Error('useAIChatContext must be used within AIChatProvider')
  return ctx
}
