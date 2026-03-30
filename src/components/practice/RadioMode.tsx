// ── Radio Mode Component ────────────────────────────────────────────────────────

import React, { useState, useEffect, useRef, useCallback } from 'react'
import type { RadioModeProps, Word } from './types'
import { syllabifyWord, playWordAudio, stopAudio } from './utils'
import SettingsPanel from '../SettingsPanel'

export default function RadioMode({
  vocabulary,
  queue,
  radioIndex: initialIndex,
  showSettings,
  settings,
  onNavigate,
  onCloseSettings,
  onModeChange,
  onSessionInteraction,
  onProgressChange,
}: RadioModeProps) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex)
  const [radioPaused, setRadioPaused] = useState(false)
  const [radioStopped, setRadioStopped] = useState(false)
  const [radioHovered, setRadioHovered] = useState(false)
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
    onProgressChange?.(Math.min(queue.length, currentIndex + 1))
  }, [currentIndex, queue.length, onProgressChange])

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

    const nextIdx = idx + 1
    // Capture the current generation — any callbacks from a previous word that
    // fire after this point must not execute (user may have skipped ahead).
    const gen = radioGenRef.current
    playWordAudio(word.word, s, () => {
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

  const handleRadioSkipPrev = () => {
    onSessionInteraction?.()
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

  const handleRadioSkipNext = () => {
    onSessionInteraction?.()
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

  const handleRadioPause = () => {
    onSessionInteraction?.()
    radioActiveRef.current = false
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    setRadioPaused(true)
  }

  const handleRadioResume = () => {
    onSessionInteraction?.()
    radioActiveRef.current = true
    setRadioPaused(false)
    radioPlayFrom(radioIndexRef.current)
  }

  const handleRadioStop = () => {
    onSessionInteraction?.()
    radioActiveRef.current = false
    radioGenRef.current++
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    if (radioRepeatTimerRef.current) clearTimeout(radioRepeatTimerRef.current)
    stopAudio()
    setRadioStopped(true)
    setRadioPaused(false)
  }

  const handleRadioRestart = () => {
    onSessionInteraction?.()
    radioActiveRef.current = true
    radioIndexRef.current = 0
    setCurrentIndex(0)
    setRadioPaused(false)
    setRadioStopped(false)
    radioPlayFrom(0)
  }

  const radioWord: Word | undefined = vocabulary[queue[currentIndex]]
  const syllables = radioWord ? syllabifyWord(radioWord.word, radioWord.phonetic) : []

  return (
    <div className="practice-page radio-mode">
      <div
        className="radio-card"
        onMouseEnter={() => setRadioHovered(true)}
        onMouseLeave={() => setRadioHovered(false)}
      >
        <div className={`radio-row radio-row-word ${radioHovered ? 'revealed' : ''}`}>
          {radioHovered ? (
            <div className="radio-word-syllables">
              {syllables.map((syl, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <span className="radio-syl-dot">·</span>}
                  <span>{syl}</span>
                </React.Fragment>
              ))}
            </div>
          ) : (
            <div className="radio-word-blank">
              <span className="radio-blank-line" style={{ width: `${Math.min(Math.max((radioWord?.word?.length ?? 0) * 18, 80), 300)}px` }} />
            </div>
          )}
        </div>

        <div className={`radio-row radio-row-phonetic ${radioHovered ? 'revealed' : ''}`}>
          {radioHovered ? radioWord?.phonetic : '★ ★ ★'}
        </div>

        <div className={`radio-row radio-row-def ${radioHovered ? 'revealed' : ''}`}>
          {radioHovered
            ? <><span className="word-pos-tag">{radioWord?.pos}</span>{radioWord?.definition}</>
            : '★ ★ ★'
          }
        </div>
      </div>

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

        <button className="radio-ctrl-btn radio-star-btn" title="收藏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
        </button>
      </div>

      <div className="radio-progress-bar">
        <div className="radio-progress-fill" style={{ width: `${(currentIndex / Math.max(queue.length - 1, 1)) * 100}%` }} />
      </div>
      <div className="radio-progress-label">{currentIndex + 1} / {queue.length}</div>

      <div className="radio-bottom-btns">
        <button className="radio-stop-btn" onClick={handleRadioStop}>停止</button>
        <button className="radio-home-btn" onClick={() => { handleRadioStop(); onNavigate('/') }}>返回主页</button>
      </div>

      {onModeChange && (
        <div className="radio-mode-switcher">
          {(['smart', 'listening', 'meaning', 'dictation'] as const).map(m => (
            <button
              key={m}
              className="radio-mode-btn"
              onClick={() => onModeChange(m)}
            >
              {m === 'smart' ? '智能' : m === 'listening' ? '听力' : m === 'meaning' ? '看词选义' : '听写'}
            </button>
          ))}
        </div>
      )}

      {showSettings && (
        <SettingsPanel showSettings={showSettings} onClose={onCloseSettings} />
      )}
    </div>
  )
}
