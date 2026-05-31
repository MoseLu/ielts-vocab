import { useCallback, useEffect, useState } from 'react'
import type { AppSettings, RadioQuickSettings } from '../../../features/practice/types'
import { APP_SETTINGS_CHANGED_EVENT, readAppSettingsFromStorage, writeAppSettingsToStorage } from '../../../lib/appSettings'

export function usePracticePageSettings() {
  const [settings, setSettings] = useState<AppSettings>(() => readAppSettingsFromStorage())

  useEffect(() => {
    const handleSettingsChanged = (event: Event) => {
      const detail = (event as CustomEvent<AppSettings>).detail
      setSettings(detail ?? readAppSettingsFromStorage())
    }

    window.addEventListener(APP_SETTINGS_CHANGED_EVENT, handleSettingsChanged)
    return () => window.removeEventListener(APP_SETTINGS_CHANGED_EVENT, handleSettingsChanged)
  }, [])

  const handleRadioSettingChange = useCallback((key: keyof RadioQuickSettings, value: string | boolean) => {
    setSettings(prev => writeAppSettingsToStorage({ ...prev, [key]: value }))
  }, [])

  return {
    settings,
    radioQuickSettings: {
      playbackSpeed: String(settings.playbackSpeed ?? '1.0'),
      playbackCount: String(settings.playbackCount ?? '1'),
      loopMode: Boolean(settings.loopMode ?? false),
      interval: String(settings.interval ?? '2'),
    },
    handleRadioSettingChange,
  }
}
