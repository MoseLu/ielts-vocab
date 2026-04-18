import { useCallback, useEffect, useState } from 'react'

const CLASSIC_PRACTICE_MODES = new Set([
  'smart',
  'quickmemory',
  'listening',
  'meaning',
  'dictation',
  'radio',
])

export function normalizePracticeDay(value: number | string | null | undefined): number | null {
  const numericValue = typeof value === 'number'
    ? value
    : value == null
      ? Number.NaN
      : Number.parseInt(value, 10)

  return Number.isInteger(numericValue) && numericValue > 0
    ? numericValue
    : null
}

function readStoredDay() {
  const saved = localStorage.getItem('current_day')
  const normalizedDay = normalizePracticeDay(saved)

  if (saved != null && normalizedDay == null) {
    localStorage.removeItem('current_day')
  }

  return normalizedDay
}

export function usePracticeRuntimeState() {
  const readStoredMode = () => {
    const savedMode = localStorage.getItem('current_mode') || 'listening'
    return CLASSIC_PRACTICE_MODES.has(savedMode) ? savedMode : 'listening'
  }
  const [mode, setMode] = useState<string>(
    readStoredMode,
  )
  const [currentDay, setCurrentDay] = useState<number | null>(readStoredDay)

  const handleModeChange = useCallback((nextMode: string) => {
    const normalizedMode = CLASSIC_PRACTICE_MODES.has(nextMode) ? nextMode : 'listening'
    setMode(normalizedMode)
    localStorage.setItem('current_mode', normalizedMode)
  }, [])

  const handleExternalModeChange = useCallback((nextMode: string) => {
    if (!CLASSIC_PRACTICE_MODES.has(nextMode)) {
      return
    }
    setMode(nextMode)
    localStorage.setItem('current_mode', nextMode)
  }, [])

  const handleDayChange = useCallback((day: number) => {
    const normalizedDay = normalizePracticeDay(day)

    if (normalizedDay == null) {
      setCurrentDay(null)
      localStorage.removeItem('current_day')
      return
    }

    setCurrentDay(normalizedDay)
    localStorage.setItem('current_day', normalizedDay.toString())
  }, [])

  useEffect(() => {
    ;(window as typeof window & { __currentMode?: string }).__currentMode = mode
  }, [mode])

  useEffect(() => {
    ;(window as typeof window & { __currentDay?: number | null }).__currentDay = currentDay
  }, [currentDay])

  useEffect(() => {
    const handlePracticeModeRequest = (event: Event) => {
      const requestedMode = (event as CustomEvent<{ mode?: string }>).detail?.mode
      if (requestedMode) {
        handleExternalModeChange(requestedMode)
      }
    }

    window.addEventListener('practice-mode-request', handlePracticeModeRequest)
    return () => {
      window.removeEventListener('practice-mode-request', handlePracticeModeRequest)
    }
  }, [handleExternalModeChange])

  return {
    mode,
    currentDay,
    handleModeChange,
    handleDayChange,
  }
}
