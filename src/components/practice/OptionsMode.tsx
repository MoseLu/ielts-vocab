// ── Options Mode Component (Listening / Meaning / Smart) ───────────────────────

import React, { useRef, useEffect } from 'react'
import type { OptionsModeProps, OptionItem, LastState, SmartDimension } from './types'
import { syllabifyWord } from './utils'

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

interface OptionsGridProps {
  options: OptionItem[]
  selectedAnswer: number | null
  showResult: boolean
  correctIndex: number
  onOptionSelect: (idx: number) => void
}

function OptionsGrid({ options, selectedAnswer, showResult, correctIndex, onOptionSelect }: OptionsGridProps) {
  return (
    <div className="options-grid">
      {options.map((option, idx) => {
        let cls = 'option-btn'
        if (showResult) {
          if (idx === correctIndex) cls += ' correct'
          else if (idx === selectedAnswer) cls += ' wrong'
        } else if (selectedAnswer === idx) cls += ' selected'
        return (
          <button key={idx} className={cls} onClick={() => onOptionSelect(idx)} disabled={showResult}>
            <div className="option-header">
              <span className="option-pos">{option.pos}</span>
              <span className="option-key">快捷键: {idx + 1}</span>
            </div>
            <span className="option-text">{option.definition}</span>
          </button>
        )
      })}
    </div>
  )
}

interface WordDisplayProps {
  currentWord: { word: string; phonetic: string; pos: string }
  mode: string
  showWord: boolean
  showAudio: boolean
  onPlayWord: (word: string) => void
}

function WordDisplay({ currentWord, mode, showWord, showAudio, onPlayWord }: WordDisplayProps) {
  const wordDisplay = showWord
    ? syllabifyWord(currentWord.word, currentWord.phonetic).join(' ')
    : currentWord.word

  return (
    <div className="word-display-area">
      {showAudio && (
        <button className="play-btn-large" onClick={() => onPlayWord(currentWord.word)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
          </svg>
        </button>
      )}
      {showWord && (
        <div className="word-display">
          <div className="word-text">{wordDisplay}</div>
          <div className="word-phonetic-row">
            <span className="word-phonetic">{currentWord.phonetic}</span>
            {(mode === 'meaning' || (mode === 'smart')) && (
              <button className="play-btn-mini" onClick={() => onPlayWord(currentWord.word)} title="播放发音">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                </svg>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Smart mode dimension badge
const SMART_DIM_CONFIG: Record<SmartDimension, { label: string; icon: string; cls: string }> = {
  listening: { label: '听力', icon: '🔊', cls: 'smart-badge-listening' },
  meaning:   { label: '词义', icon: '📖', cls: 'smart-badge-meaning' },
  dictation: { label: '拼写', icon: '✍️', cls: 'smart-badge-dictation' },
}

interface SmartDimBadgeProps {
  dimension: SmartDimension
}

function SmartDimBadge({ dimension }: SmartDimBadgeProps) {
  const cfg = SMART_DIM_CONFIG[dimension]
  return (
    <div className={`smart-dim-badge ${cfg.cls}`}>
      <span className="smart-badge-icon">{cfg.icon}</span>
      <span className="smart-badge-label">{cfg.label}</span>
    </div>
  )
}

interface SmartDictationProps {
  currentWord: { word: string; definition: string; pos: string; phonetic: string }
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  onSpellingInputChange: (v: string) => void
  onSpellingSubmit: () => void
  onStartRecording: () => void
  onStopRecording: () => void
  onSkip: () => void
}

function SmartDictation({
  currentWord,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  onSpellingInputChange,
  onSpellingSubmit,
  onStartRecording,
  onStopRecording,
  onSkip,
}: SmartDictationProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (spellingResult === null) {
      setTimeout(() => inputRef.current?.focus(), 400)
    }
  }, [spellingResult])

  return (
    <div className="smart-dictation-area">
      <div className="dictation-letter-hint">
        {currentWord.word.split('').map((ch, i) =>
          ch === ' '
            ? <span key={i} className="letter-hint-space" />
            : <span key={i} className="letter-hint-blank">_</span>
        )}
      </div>

      {spellingResult === 'wrong' && (
        <div className="spelling-answer">
          正确答案：<strong>{currentWord.word}</strong>
          <div className="spelling-answer-def">
            <span className="word-pos-tag">{currentWord.pos}</span>{currentWord.definition}
          </div>
        </div>
      )}
      {spellingResult === 'correct' && (
        <div className="spelling-answer correct-answer">正确！</div>
      )}

      <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
        <input
          ref={inputRef}
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

      {!spellingResult && (
        <button className="skip-btn" onClick={onSkip}>
          不知道 <span className="shortcut-hint">快捷键: 5</span>
        </button>
      )}
    </div>
  )
}

interface OptionsModePropsExtended extends OptionsModeProps {
  queueIndex: number
}

export default function OptionsMode({
  currentWord,
  previousWord,
  lastState,
  mode,
  smartDimension = 'meaning',
  options,
  selectedAnswer,
  showResult,
  correctIndex,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  progressValue,
  total,
  queueIndex,
  onOptionSelect,
  onSkip,
  onGoBack,
  onSpellingSubmit,
  onSpellingInputChange,
  onStartRecording,
  onStopRecording,
  onPlayWord,
}: OptionsModePropsExtended) {
  // Effective display flags
  // For smart mode, determined by current dimension
  let showWord: boolean
  let showAudio: boolean

  if (mode === 'smart') {
    showWord = smartDimension === 'meaning'
    showAudio = smartDimension === 'listening' || smartDimension === 'dictation'
  } else {
    showWord = mode === 'meaning'
    showAudio = mode === 'listening'
  }

  const isSmartDictation = mode === 'smart' && smartDimension === 'dictation'

  return (
    <div className="practice-page">
      <PrevWordBlock previousWord={previousWord} lastState={lastState} onGoBack={onGoBack} />

      <div className="practice-main">
        {mode === 'smart' && <SmartDimBadge dimension={smartDimension} />}

        <WordDisplay
          currentWord={currentWord}
          mode={mode}
          showWord={showWord}
          showAudio={showAudio}
          onPlayWord={onPlayWord}
        />

        {isSmartDictation ? (
          <SmartDictation
            currentWord={currentWord}
            spellingInput={spellingInput}
            spellingResult={spellingResult}
            speechConnected={speechConnected}
            speechRecording={speechRecording}
            onSpellingInputChange={onSpellingInputChange}
            onSpellingSubmit={onSpellingSubmit}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
            onSkip={onSkip}
          />
        ) : (
          <>
            <OptionsGrid
              options={options}
              selectedAnswer={selectedAnswer}
              showResult={showResult}
              correctIndex={correctIndex}
              onOptionSelect={onOptionSelect}
            />

            <div className="options-footer">
              <button className="skip-btn" onClick={onSkip}>
                不知道 <span className="shortcut-hint">快捷键: 5</span>
              </button>
              <button
                className="replay-btn"
                onClick={() => onPlayWord(currentWord.word)}
                title="再读一遍，快捷键 Tab"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                </svg>
              </button>
            </div>
          </>
        )}
      </div>

      <BottomBar progressValue={progressValue} total={total} queueIndex={queueIndex} />
    </div>
  )
}
