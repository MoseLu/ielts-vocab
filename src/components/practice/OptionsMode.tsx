// ── Options Mode Component (Listening / Meaning / Smart) ───────────────────────

import React from 'react'
import type { OptionsModeProps, OptionItem, LastState } from './types'
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
            {mode === 'meaning' && (
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

interface OptionsModePropsExtended extends OptionsModeProps {
  queueIndex: number
}

export default function OptionsMode({
  currentWord,
  previousWord,
  lastState,
  mode,
  options,
  selectedAnswer,
  showResult,
  correctIndex,
  progressValue,
  total,
  queueIndex,
  onOptionSelect,
  onSkip,
  onGoBack,
  onPlayWord,
}: OptionsModePropsExtended) {
  const showWord = mode === 'meaning' || mode === 'smart'
  const showAudio = mode === 'listening' || mode === 'smart'

  return (
    <div className="practice-page">
      <PrevWordBlock previousWord={previousWord} lastState={lastState} onGoBack={onGoBack} />

      <div className="practice-main">
        <WordDisplay
          currentWord={currentWord}
          mode={mode}
          showWord={showWord}
          showAudio={showAudio}
          onPlayWord={onPlayWord}
        />

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
      </div>

      <BottomBar progressValue={progressValue} total={total} queueIndex={queueIndex} />
    </div>
  )
}
