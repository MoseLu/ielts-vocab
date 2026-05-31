import { useEffect, useRef } from 'react'
import {
  prepareWordAudioPlayback,
  preloadWordAudioBatch,
  playWordAudio as playWordUtil,
  stopAudio as stopAudioUtil,
} from '../../../features/practice/audio/practiceAudio'
import type {
  AppSettings,
  PracticeMode,
  SmartDimension,
  Word,
} from '../../../features/practice/types'

const PRACTICE_AUTOPLAY_PRELOAD_OPTIONS = { includeBuffer: true, sourcePreference: 'buffer' as const }
const PRACTICE_AUTOPLAY_PLAYBACK_OPTIONS = { sourcePreference: 'buffer' as const }

function shouldUseBufferAutoplay(mode: PracticeMode | undefined, smartDimension: SmartDimension): boolean {
  return mode === 'listening'
    || mode === 'dictation'
    || (mode === 'smart' && (smartDimension === 'listening' || smartDimension === 'dictation'))
}

export function usePracticePageAudioEffects({
  currentWord,
  mode,
  queue,
  queueIndex,
  settings,
  smartDimension,
  vocabulary,
}: {
  currentWord: Word | undefined
  mode?: PracticeMode
  queue: number[]
  queueIndex: number
  settings: AppSettings
  smartDimension: SmartDimension
  vocabulary: Word[]
}) {
  const autoPlayTimerRef = useRef<number | null>(null)
  const autoPlayStartedKeyRef = useRef<string | null>(null)
  const upcomingWords = queue
    .slice(queueIndex + 1, queueIndex + 4)
    .map(index => vocabulary[index]?.word?.trim())
    .filter((word): word is string => Boolean(word))
  const upcomingWordsKey = upcomingWords.join('|')

  useEffect(() => {
    if (mode === 'quickmemory' || mode === 'test') return
    const activeWord = currentWord?.word?.trim()
    if (!activeWord) return

    const preloadOptions = shouldUseBufferAutoplay(mode, smartDimension)
      ? PRACTICE_AUTOPLAY_PRELOAD_OPTIONS
      : undefined
    void prepareWordAudioPlayback(activeWord, preloadOptions).catch(() => {})
    if (upcomingWords.length) {
      void preloadWordAudioBatch(upcomingWords, upcomingWords.length, preloadOptions).catch(() => {})
    }
  }, [currentWord?.word, mode, smartDimension, upcomingWordsKey, upcomingWords.length])

  useEffect(() => {
    if (!currentWord) return
    const shouldAutoPlay = shouldUseBufferAutoplay(mode, smartDimension)
    if (!shouldAutoPlay) return

    const isDictation = mode === 'dictation' || (mode === 'smart' && smartDimension === 'dictation')
    if (isDictation && currentWord.examples?.[0]?.en) return

    if (autoPlayTimerRef.current != null) {
      window.clearTimeout(autoPlayTimerRef.current)
      autoPlayTimerRef.current = null
    }

    const autoPlayKey = `${mode}:${smartDimension}:${queueIndex}:${currentWord.word}`
    if (autoPlayStartedKeyRef.current === autoPlayKey) return

    let cancelled = false
    autoPlayTimerRef.current = window.setTimeout(() => {
      autoPlayTimerRef.current = null
      void (async () => {
        const prepared = await prepareWordAudioPlayback(currentWord.word, PRACTICE_AUTOPLAY_PRELOAD_OPTIONS).catch(() => false)
        if (cancelled || !prepared) return
        autoPlayStartedKeyRef.current = autoPlayKey
        playWordUtil(currentWord.word, settings, undefined, PRACTICE_AUTOPLAY_PLAYBACK_OPTIONS)
      })()
    }, 280)

    return () => {
      cancelled = true
      if (autoPlayTimerRef.current != null) {
        window.clearTimeout(autoPlayTimerRef.current)
        autoPlayTimerRef.current = null
      }
    }
  }, [currentWord, mode, queueIndex, settings, smartDimension])

  useEffect(() => {
    autoPlayStartedKeyRef.current = null
    return () => {
      stopAudioUtil()
      if (autoPlayTimerRef.current != null) {
        window.clearTimeout(autoPlayTimerRef.current)
        autoPlayTimerRef.current = null
      }
    }
  }, [currentWord?.word, mode, queueIndex])
}
