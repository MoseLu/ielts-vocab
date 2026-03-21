// ── Toast Context ───────────────────────────────────────────────────────────────

import React, { createContext, useContext, useState, useCallback } from 'react'
import { safeParse, ToastDataSchema, ToastTypeSchema } from '../lib'

interface ToastContextValue {
  toast: { message: string; type: 'info' | 'success' | 'error' } | null
  showToast: (message: string, type?: 'info' | 'success' | 'error') => void
  hideToast: () => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TOAST_DURATION = 3000

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<{ message: string; type: 'info' | 'success' | 'error' } | null>(null)

  const showToast = useCallback((message: string, type: 'info' | 'success' | 'error' = 'info') => {
    const result = safeParse(ToastDataSchema, { message, type })
    if (!result.success) return // Silently ignore invalid toast data

    setToast(result.data)
    setTimeout(() => setToast(null), TOAST_DURATION)
  }, [])

  const hideToast = useCallback(() => {
    setToast(null)
  }, [])

  return (
    <ToastContext.Provider value={{ toast, showToast, hideToast }}>
      {children}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}
