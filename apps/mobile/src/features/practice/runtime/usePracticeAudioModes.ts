import { useCallback, useEffect, useRef, useState } from 'react'
import type { MobileWord, PracticeMode } from '@ielts-vocab/app-core'
import { playRemoteAudio, stopRemoteAudio } from '../../../native/NativeAudioPlayer'

const AUTO_REPLAY_DELAY_MS = 280
const RADIO_NEXT_DELAY_MS = 3_200

type UsePracticeAudioModesParams = {
  currentWord?: MobileWord
  index: number
  mode: PracticeMode
  onRadioAdvance: () => Promise<void>
  setError: (message: string) => void
  setFeedback: (message: string) => void
}

function wordAudioPath(word: string) {
  const params = new URLSearchParams({ w: word, cache_only: '1' })
  return `/api/tts/word-audio?${params.toString()}`
}

function isAutoReplayMode(mode: PracticeMode) {
  return mode === 'listening' || mode === 'dictation'
}

export function usePracticeAudioModes({
  currentWord,
  index,
  mode,
  onRadioAdvance,
  setError,
  setFeedback,
}: UsePracticeAudioModesParams) {
  const [audioStatus, setAudioStatus] = useState('')
  const [radioInteractionCount, setRadioInteractionCount] = useState(0)
  const [radioPaused, setRadioPaused] = useState(false)
  const onRadioAdvanceRef = useRef(onRadioAdvance)
  const requestIdRef = useRef(0)
  const radioTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    onRadioAdvanceRef.current = onRadioAdvance
  }, [onRadioAdvance])

  const clearRadioTimer = useCallback(() => {
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    radioTimerRef.current = null
  }, [])

  const playWord = useCallback(async (source: 'auto' | 'manual' | 'radio' = 'manual') => {
    if (!currentWord) return
    const requestId = ++requestIdRef.current
    const label = source === 'auto' ? '自动播放中' : source === 'radio' ? '随身听播放中' : '正在播放'
    setError('')
    setAudioStatus(label)
    try {
      await playRemoteAudio(wordAudioPath(currentWord.word))
      if (requestIdRef.current === requestId) {
        setAudioStatus(source === 'auto' ? '已自动播放，可点播放发音重听' : '已播放')
      }
    } catch (err) {
      if (requestIdRef.current === requestId) {
        setAudioStatus('')
        setError(err instanceof Error ? err.message : '播放失败')
      }
    }
  }, [currentWord, setError])

  const recordRadioInteraction = useCallback((label: string) => {
    setRadioInteractionCount(count => {
      const nextCount = count + 1
      setFeedback(`随身听${label}已记录，本轮 ${nextCount} 次操作。`)
      return nextCount
    })
  }, [setFeedback])

  const scheduleRadioAdvance = useCallback(() => {
    clearRadioTimer()
    radioTimerRef.current = setTimeout(() => {
      void onRadioAdvanceRef.current()
    }, RADIO_NEXT_DELAY_MS)
  }, [clearRadioTimer])

  const playRadioCurrent = useCallback(() => {
    void playWord('radio').then(scheduleRadioAdvance)
  }, [playWord, scheduleRadioAdvance])

  useEffect(() => {
    setAudioStatus('')
    if (mode !== 'radio') {
      setRadioPaused(false)
      clearRadioTimer()
      void stopRemoteAudio().catch(() => undefined)
    }
  }, [clearRadioTimer, mode])

  useEffect(() => {
    if (!currentWord || !isAutoReplayMode(mode)) return
    const timer = setTimeout(() => {
      void playWord('auto')
    }, AUTO_REPLAY_DELAY_MS)
    return () => {
      clearTimeout(timer)
      requestIdRef.current += 1
      void stopRemoteAudio().catch(() => undefined)
    }
  }, [currentWord?.word, index, mode, playWord])

  useEffect(() => {
    if (!currentWord || mode !== 'radio' || radioPaused) return
    playRadioCurrent()
    return () => {
      clearRadioTimer()
      requestIdRef.current += 1
      void stopRemoteAudio().catch(() => undefined)
    }
  }, [clearRadioTimer, currentWord?.word, index, mode, playRadioCurrent, radioPaused])

  const pauseRadio = useCallback(async () => {
    if (mode !== 'radio') return
    clearRadioTimer()
    requestIdRef.current += 1
    await stopRemoteAudio().catch(() => undefined)
    setRadioPaused(true)
    setAudioStatus('随身听已暂停')
    recordRadioInteraction('暂停')
  }, [clearRadioTimer, mode, recordRadioInteraction])

  const resumeRadio = useCallback(() => {
    if (mode !== 'radio') return
    setRadioPaused(false)
    recordRadioInteraction('继续')
  }, [mode, recordRadioInteraction])

  const skipRadioNext = useCallback(async () => {
    if (mode !== 'radio') return
    clearRadioTimer()
    requestIdRef.current += 1
    await stopRemoteAudio().catch(() => undefined)
    recordRadioInteraction('下一词')
    await onRadioAdvanceRef.current()
  }, [clearRadioTimer, mode, recordRadioInteraction])

  return {
    audioStatus,
    pauseRadio,
    playWord,
    radioInteractionCount,
    radioPaused,
    resumeRadio,
    skipRadioNext,
  }
}
