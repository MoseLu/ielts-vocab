// ── Settings Context ─────────────────────────────────────────────────────────────

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { AppSettings } from '../types'
import { DEFAULT_SETTINGS } from '../constants'
import { safeParse, AppSettingsSchema } from '../lib'
import { readAppSettingsFromStorage, writeAppSettingsToStorage } from '../lib/appSettings'

interface SettingsContextValue {
  settings: AppSettings
  updateSetting: <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(() => {
    const parsed = safeParse(AppSettingsSchema, readAppSettingsFromStorage())
    return parsed.success ? parsed.data : (DEFAULT_SETTINGS as AppSettings)
  })

  useEffect(() => {
    // Apply settings to document
    document.documentElement.setAttribute(
      'data-theme',
      settings.darkMode ? 'dark' : 'light'
    )
    document.documentElement.setAttribute(
      'data-font-size',
      settings.fontSize || 'medium'
    )
  }, [settings])

  const updateSetting = useCallback(<K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings(prev => {
      const newSettings = { ...prev, [key]: value }

      // Validate before persisting
      const parsed = safeParse(AppSettingsSchema, newSettings)
      if (parsed.success) {
        writeAppSettingsToStorage(parsed.data)
      }

      return newSettings
    })
  }, [])

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS as AppSettings)
    writeAppSettingsToStorage(DEFAULT_SETTINGS)
  }, [])

  return (
    <SettingsContext.Provider value={{ settings, updateSetting, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider')
  }
  return context
}
