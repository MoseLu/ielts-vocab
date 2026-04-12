import { useCallback, useEffect, useState } from 'react'

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
  const [mode, setMode] = useState<string>(
    () => localStorage.getItem('current_mode') || 'listening',
  )
  const [currentDay, setCurrentDay] = useState<number | null>(readStoredDay)

  const handleModeChange = useCallback((nextMode: string) => {
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
        handleModeChange(requestedMode)
      }
    }

    window.addEventListener('practice-mode-request', handlePracticeModeRequest)
    return () => {
      window.removeEventListener('practice-mode-request', handlePracticeModeRequest)
    }
  }, [handleModeChange])

  return {
    mode,
    currentDay,
    handleModeChange,
    handleDayChange,
  }
}
