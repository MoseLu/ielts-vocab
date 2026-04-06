import { useCallback, useEffect, useState } from 'react'

function readStoredDay() {
  const saved = localStorage.getItem('current_day')
  return saved ? parseInt(saved, 10) : null
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
    setCurrentDay(day)
    localStorage.setItem('current_day', day.toString())
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
