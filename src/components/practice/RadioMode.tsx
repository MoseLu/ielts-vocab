// ── Radio Mode Component ────────────────────────────────────────────────────────

import React, { useState, useEffect, useRef, useCallback } from 'react'
import type { RadioModeProps, PracticeMode, Word } from './types'
import { syllabifyWord, playWordAudio, stopAudio } from './utils'
import SettingsPanel from '../SettingsPanel'

export default function RadioMode({
  vocabulary,
  queue,
  radioIndex,
  showSettings,
  settings,
  onRadioSkipPrev,
  onRadioSkipNext,
  onRadioPause,
  onRadioResume,
  onRadioRestart,
  onRadioStop,
  onNavigate,
  onCloseSettings,
  onModeChange,
}: RadioModeProps) {
  const [radioPaused, setRadioPaused] = useState(false)
  const [radioStopped, setRadioStopped] = useState(false)
  const [radioHovered, setRadioHovered] = useState(false)
  const radioActiveRef = useRef(true)
  const radioTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const radioIndexRef = useRef(0)
  const vocabRef = useRef<Word[]>([])
  const queueRef = useRef<number[]>([])

  // Initialize refs
  useEffect(() => {
    vocabRef.current = vocabulary
    queueRef.current = queue
    radioIndexRef.current = radioIndex
  }, [vocabulary, queue, radioIndex])

  const radioPlayFrom = useCallback((idx: number) => {
    const q = queueRef.current
    const vocab = vocabRef.current
    if (idx >= q.length) { radioActiveRef.current = false; return }
    radioIndexRef.current = idx
    const word = vocab[q[idx]]
    if (!word) { radioPlayFrom(idx + 1); return }
    playWordAudio(word.word, settings, () => {
      if (!radioActiveRef.current) return
      radioTimerRef.current = setTimeout(() => {
        if (radioActiveRef.current) radioPlayFrom(radioIndexRef.current + 1)
      }, parseFloat(settings.interval || '2') * 1000)
    })
  }, [settings])

  useEffect(() => {
    radioActiveRef.current = true
    radioIndexRef.current = 0
    setRadioPaused(false)
    setRadioStopped(false)
    radioPlayFrom(0)
    return () => {
      radioActiveRef.current = false
      if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
      stopAudio()
    }
  }, [])

  const handleRadioPause = () => {
    radioActiveRef.current = false
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    stopAudio()
    setRadioPaused(true)
    onRadioPause()
  }

  const handleRadioResume = () => {
    radioActiveRef.current = true
    setRadioPaused(false)
    onRadioResume()
    radioPlayFrom(radioIndexRef.current)
  }

  const handleRadioStop = () => {
    radioActiveRef.current = false
    if (radioTimerRef.current) clearTimeout(radioTimerRef.current)
    stopAudio()
    setRadioStopped(true)
    setRadioPaused(false)
    onRadioStop()
  }

  const handleRadioRestart = () => {
    radioActiveRef.current = true
    radioIndexRef.current = 0
    setRadioPaused(false)
    setRadioStopped(false)
    onRadioRestart()
    radioPlayFrom(0)
  }

  const radioWord: Word | undefined = vocabulary[queue[radioIndex]]
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
        <button className="radio-ctrl-btn" onClick={onRadioSkipPrev} title="上一个">
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

        <button className="radio-ctrl-btn" onClick={onRadioSkipNext} title="下一个">
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
        <div className="radio-progress-fill" style={{ width: `${(radioIndex / Math.max(queue.length - 1, 1)) * 100}%` }} />
      </div>
      <div className="radio-progress-label">{radioIndex + 1} / {queue.length}</div>

      <div className="radio-bottom-btns">
        <button className="radio-stop-btn" onClick={handleRadioStop}>停止</button>
        <button className="radio-home-btn" onClick={() => { handleRadioStop(); onNavigate('/') }}>返回主页</button>
      </div>

      {/* Mode switcher */}
      <div className="radio-mode-switcher">
        {(['smart', 'listening', 'meaning', 'dictation'] as PracticeMode[]).map(m => (
          <button
            key={m}
            className="radio-mode-btn"
            onClick={() => onModeChange(m)}
          >
            {m === 'smart' ? '智能' : m === 'listening' ? '听力' : m === 'meaning' ? '看词选义' : '听写'}
          </button>
        ))}
      </div>

      {showSettings && (
        <SettingsPanel showSettings={showSettings} onClose={onCloseSettings} />
      )}
    </div>
  )
}
