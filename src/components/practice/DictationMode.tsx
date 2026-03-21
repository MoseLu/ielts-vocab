// ── Dictation Mode Component ───────────────────────────────────────────────────

import React, { useRef, useEffect } from 'react'
import type { DictationModeProps, LastState } from './types'
import { playWord } from './utils'

interface PrevWordBlockProps {
  previousWord: LastState['prevWord']
  lastState: LastState | null
  onGoBack: () => void
}

function PrevWordBlock({ previousWord, lastState, onGoBack }: PrevWordBlockProps) {
  if (!previousWord) return null
  return (
    <div className="prev-word-inline">
      <button className="prev-back-btn" onClick={onGoBack} disabled={!lastState} title="返回上一个词">←</button>
      <div className="prev-word-info">
        <div className="prev-word-text">{previousWord.word}</div>
        <div className="prev-word-phonetic">{previousWord.phonetic}</div>
        <div className="prev-word-def"><span className="word-pos-tag">{previousWord.pos}</span>{previousWord.definition}</div>
      </div>
    </div>
  )
}

interface BottomBarProps {
  progressValue: number
  total: number
  queueIndex: number
}

function BottomBar({ progressValue, total, queueIndex }: BottomBarProps) {
  return (
    <div className="practice-bottom-bar">
      <div className="bottom-progress-track">
        <div className="bottom-progress-fill" style={{ width: `${progressValue * 100}%` }}>
          <div className="bottom-progress-dot"></div>
        </div>
      </div>
      <span className="bottom-progress-count">{queueIndex + 1}/{total}</span>
    </div>
  )
}

export default function DictationMode({
  currentWord,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  settings,
  progressValue,
  total,
  previousWord,
  lastState,
  onSpellingInputChange,
  onSpellingSubmit,
  onSkip,
  onGoBack,
  onStartRecording,
  onStopRecording,
  onPlayWord,
}: DictationModeProps) {
  const spellingRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (spellingResult === null) {
      setTimeout(() => spellingRef.current?.focus(), 400)
    }
  }, [spellingResult])

  const handlePlayWord = () => {
    onPlayWord(currentWord.word)
  }

  return (
    <div className="practice-page">
      <PrevWordBlock previousWord={previousWord} lastState={lastState} onGoBack={onGoBack} />

      <div className="dictation-container">
        <div className="dictation-play-area">
          <button className="play-btn-large" onClick={handlePlayWord}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
            </svg>
          </button>
          <p className="dictation-hint">听发音，拼写单词</p>
        </div>

        <div className="dictation-letter-hint">
          {currentWord.word.split('').map((ch, i) => (
            ch === ' ' ? <span key={i} className="letter-hint-space" /> : <span key={i} className="letter-hint-blank">_</span>
          ))}
        </div>

        {spellingResult === 'wrong' && (
          <div className="spelling-answer">正确答案：<strong>{currentWord.word}</strong></div>
        )}

        <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
          <input
            ref={spellingRef}
            type="text"
            className="spelling-input"
            value={spellingInput}
            onChange={e => onSpellingInputChange(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') onSpellingSubmit() }}
            placeholder="输入你听到的单词..."
            disabled={!!spellingResult}
            autoComplete="off"
            spellCheck={false}
          />
          {!spellingResult && (
            <button
              className={`mic-btn ${speechRecording ? 'recording' : ''} ${!speechConnected ? 'disconnected' : ''}`}
              onClick={speechRecording ? onStopRecording : onStartRecording}
              disabled={!speechConnected}
              title={speechRecording ? '停止录音' : speechConnected ? '语音输入' : '语音服务未连接'}
            >
              {!speechConnected ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="23"></line>
                  <line x1="8" y1="23" x2="16" y2="23"></line>
                  <line x1="4" y1="4" x2="20" y2="20" stroke="red" strokeWidth="2"></line>
                </svg>
              ) : speechRecording ? (
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="23"></line>
                  <line x1="8" y1="23" x2="16" y2="23"></line>
                </svg>
              )}
            </button>
          )}
          {!spellingResult && (
            <button className="spelling-submit-btn" onClick={onSpellingSubmit} title="确认">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </button>
          )}
        </div>
      </div>

      <button className="skip-btn" onClick={onSkip}>不知道 <span className="shortcut-hint">(5)</span></button>
      <BottomBar progressValue={progressValue} total={total} queueIndex={0} />
    </div>
  )
}
