// ── Radio Mode Component ────────────────────────────────────────────────────────

import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react'
import type { RadioModeProps, Word } from './types'
import { playWordAudio, preloadWordAudioBatch, stopAudio } from './utils'
import SettingsPanel from '../settings/SettingsPanel'
import {
  PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT,
  PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT,
  PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT,
} from './page/practiceGlobalShortcutEvents'

export default function RadioMode({
  vocabulary,
  queue,
  radioIndex: initialIndex,
  showSettings,
  settings,
  onNavigate,
  onCloseSettings,
  onIndexChange,
  onSessionInteraction,
  onProgressChange,
  isSessionActive,
  favoriteSlot,
  speakingSlot,
}: RadioModeProps) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex)
  const [radioPaused, setRadioPaused] = useState(false)
  const [radioStopped, setRadioStopped] = useState(false)
  const radioActiveRef = useRef(true)
  const radioTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const radioRepeatTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const radioIndexRef = useRef(initialIndex)
  const radioGenRef = useRef(0)
  const vocabRef = useRef<Word[]>([])
  const queueRef = useRef<number[]>([])

  // Keep refs in sync with latest props (including settings changes from toolbar)
  const settingsRef = useRef(settings)
  useEffect(() => {
    vocabRef.current = vocabulary
    queueRef.current = queue
  }, [vocabulary, queue])
  useEffect(() => { settingsRef.current = settings }, [settings])
  useEffect(() => {
    if (isSessionActive?.() === false) return
    onProgressChange?.(Math.min(queue.length, currentIndex + 1))
  }, [currentIndex, isSessionActive, queue.length, onProgressChange])
  useEffect(() => {
    onIndexChange?.(currentIndex)
  }, [currentIndex, onIndexChange])

  // Stable recursive callback — always reads latest values from refs
  const radioPlayFrom = useCallback((idx: number, repeat: number = 0) => {
    const q = queueRef.current
    const vocab = vocabRef.current
    const s = settingsRef.current
    const maxRepeat = Math.max(0, parseInt(String(s.playbackCount ?? '1')) - 1)
    const loopMode  = Boolean(s.loopMode)

    if (idx >= q.length) {
      if (loopMode) {
        radioIndexRef.current = 0
        setCurrentIndex(0)
        if (radioActiveRef.current) radioPlayFrom(0, 0)
      } else {
        radioActiveRef.current = false
      }
      return
    }
    radioIndexRef.current = idx
    setCurrentIndex(idx)
    const word = vocab[q[idx]]
    if (!word) { radioPlayFrom(idx + 1, 0); return }
    const upcomingWords = q
      .slice(idx + 1, idx + 4)
      .map(queueIndex => vocab[queueIndex]?.word?.trim())
      .filter((nextWord): nextWord is string => Boolean(nextWord))
    if (upcomingWords.length) {
      void preloadWordAudioBatch(upcomingWords)
    }

    const nextIdx = idx + 1
    // Capture the current generation — any callbacks from a previous word that
    // fire after this point must not execute (user may have skipped ahead).
    const gen = radioGenRef.current
    void playWordAudio(word.word, s, () => {
      if (!radioActiveRef.current) return
      if (radioGenRef.current !== gen) return // stale — word was skipped
      if (repeat < maxRepeat) {
        // Brief pause between repetitions of the same word
        radioRepeatTimerRef.current = setTimeout(() => {
          if (!radioActiveRef.current) return
          if (radioGenRef.current !== gen) return // stale
          radioPlayFrom(idx, repeat + 1)
        }, 500)
      } else {
        // Move to next word after interval
        radioTimerRef.current = setTimeout(() => {
          if (!radioActiveRef.current) return
          if (radioGenRef.current !== gen) return // stale
          radioPlayFrom(nextIdx, 0)
        }, parseFloat(String(s.interval ?? '2')) * 1000)
      }
    })
  }, []) // stable — all state accessed via refs

  // Start playback on mount
  useEffect(() => {
    radioActiveRef.current = true
    radioIndexRef.current = initialIndex
    setCurrentIndex(initialIndex)
    setRadioPaused(false)
    setRadioStopped(false)
    radioPlayFrom(initialIndex)
    return () => {
      radioActiveRef.current = false
      if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
      if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
      stopAudio()
    }
  }, [])

  const handleRadioSkipPrev = async () => {
    await onSessionInteraction?.()
    const newIdx = Math.max(0, radioIndexRef.current - 1)
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    radioIndexRef.current = newIdx
    setCurrentIndex(newIdx)
    if (!radioPaused && !radioStopped) {
      radioActiveRef.current = true
      radioPlayFrom(newIdx)
    }
  }

  const handleRadioSkipNext = async () => {
    await onSessionInteraction?.()
    const newIdx = Math.min(queueRef.current.length - 1, radioIndexRef.current + 1)
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    radioIndexRef.current = newIdx
    setCurrentIndex(newIdx)
    if (!radioPaused && !radioStopped) {
      radioActiveRef.current = true
      radioPlayFrom(newIdx)
    }
  }

  const handleRadioPause = async () => {
    await onSessionInteraction?.()
    radioActiveRef.current = false
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    setRadioPaused(true)
  }

  const handleRadioResume = async () => {
    await onSessionInteraction?.()
    radioActiveRef.current = true
    setRadioPaused(false)
    radioPlayFrom(radioIndexRef.current)
  }

  const handleRadioStop = async () => {
    await onSessionInteraction?.()
    radioActiveRef.current = false
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    setRadioStopped(true)
    setRadioPaused(false)
  }

  const handleRadioRestart = async () => {
    await onSessionInteraction?.()
    radioActiveRef.current = true
    radioIndexRef.current = 0
    setCurrentIndex(0)
    setRadioPaused(false)
    setRadioStopped(false)
    radioPlayFrom(0)
  }

  const replayCurrentWord = useCallback(async () => {
    if (radioStopped) return
    await onSessionInteraction?.()
    radioActiveRef.current = true
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    setRadioPaused(false)
    radioPlayFrom(radioIndexRef.current)
  }, [onSessionInteraction, radioPlayFrom, radioStopped])

  useEffect(() => {
    window.addEventListener(PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT, handleRadioSkipPrev)
    window.addEventListener(PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT, handleRadioSkipNext)
    window.addEventListener(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT, replayCurrentWord)
    return () => {
      window.removeEventListener(PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT, handleRadioSkipPrev)
      window.removeEventListener(PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT, handleRadioSkipNext)
      window.removeEventListener(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT, replayCurrentWord)
    }
  }, [handleRadioSkipNext, handleRadioSkipPrev, replayCurrentWord])

  const radioWord: Word | undefined = vocabulary[queue[currentIndex]]

  return (
    <div className="practice-page radio-mode">
      <section className="radio-stage" aria-live="polite">
        {(favoriteSlot || speakingSlot) ? (
          <div className="radio-stage-toolbar">
            <div className="radio-stage-toolbar__side">{favoriteSlot}</div>
            <div className="radio-stage-toolbar__side radio-stage-toolbar__side--end">{speakingSlot}</div>
          </div>
        ) : null}
        <h1 className="radio-stage-word">{radioWord?.word ?? '...'}</h1>
        <p className="radio-stage-phonetic">{radioWord?.phonetic ?? '/-/'}</p>
        <p className="radio-stage-definition">
          {radioWord?.pos ? <span className="word-pos-tag">{radioWord.pos}</span> : null}
          <span>{radioWord?.definition ?? ''}</span>
        </p>
      </section>

      <div className="radio-controls">
        <button className="radio-ctrl-btn" onClick={handleRadioSkipPrev} title="上一个">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="19 20 9 12 19 4 19 20"></polygon>
            <line x1="5" y1="19" x2="5" y2="5"></line>
          </svg>
        </button>

        {radioPaused || radioStopped ? (
          <button className="radio-ctrl-btn radio-play-btn" onClick={radioStopped ? handleRadioRestart : handleRadioResume} title="继续">
            <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          </button>
        ) : (
          <button className="radio-ctrl-btn radio-play-btn" onClick={handleRadioPause} title="暂停">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16"></rect>
              <rect x="14" y="4" width="4" height="16"></rect>
            </svg>
          </button>
        )}

        <button className="radio-ctrl-btn" onClick={handleRadioSkipNext} title="下一个">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="5 4 15 12 5 20 5 4"></polygon>
            <line x1="19" y1="5" x2="19" y2="19"></line>
          </svg>
        </button>

      </div>

      <div className="radio-progress-track">
        <div
          className="radio-progress-fill"
          style={{ '--progress-percent': `${((currentIndex + 1) / Math.max(queue.length, 1)) * 100}%` } as CSSProperties}
        />
      </div>
      <div className="radio-progress-label">{currentIndex + 1} / {queue.length}</div>

      <div className="radio-bottom-btns">
          <button className="radio-stop-btn" onClick={() => { void handleRadioStop() }}>停止</button>
        <button className="radio-home-btn" onClick={() => { void handleRadioStop(); onNavigate('/plan') }}>返回主页</button>
      </div>

      {showSettings && (
        <SettingsPanel showSettings={showSettings} onClose={onCloseSettings} />
      )}
    </div>
  )
}
