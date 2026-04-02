// ── Dictation Mode Component ───────────────────────────────────────────────────

import React, { useRef, useEffect, useState, useCallback } from 'react'
import type { DictationModeProps, LastState } from './types'
import { playExampleAudio, stopAudio } from './utils'

type DictationSubMode = 'word' | 'example'

const ANSWER_REVEAL_PLAY_COUNT = 3

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

/** Build the sentence display with the target word replaced by blank underscores */
function buildBlankSentence(sentence: string, targetWord: string): React.ReactNode {
  // Case-insensitive replacement to find the word in context
  const regex = new RegExp(`(${targetWord})`, 'gi')
  const parts = sentence.split(regex)
  return parts.map((part, i) => {
    if (part.toLowerCase() === targetWord.toLowerCase()) {
      return (
        <span key={i} className="example-blank-word">
          {targetWord.split('').map((_, j) => <span key={j} className="letter-hint-blank">_</span>)}
        </span>
      )
    }
    return <span key={i}>{part}</span>
  })
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
  onGoBack,
  onStartRecording,
  onStopRecording,
  onPlayWord,
}: DictationModeProps) {
  const spellingRef = useRef<HTMLInputElement>(null)
  const [dictationSubMode, setDictationSubMode] = useState<DictationSubMode>('example')
  const [manualReplayCount, setManualReplayCount] = useState(0)

  const hasExamples = Boolean(currentWord.examples && currentWord.examples.length > 0)
  const activeSubMode: DictationSubMode = hasExamples ? dictationSubMode : 'word'

  useEffect(() => {
    if (spellingResult === null) {
      setTimeout(() => spellingRef.current?.focus(), 400)
    }
  }, [spellingResult, currentWord.word])

  useEffect(() => {
    setDictationSubMode('example')
    setManualReplayCount(0)
  }, [currentWord.word])

  const handlePlayWord = useCallback(() => {
    onPlayWord(currentWord.word)
  }, [onPlayWord, currentWord.word])

  const handlePlayExample = useCallback(() => {
    const example = currentWord.examples?.[0]
    if (!example) return
    playExampleAudio(example.en, currentWord.word, settings)
  }, [currentWord.examples, currentWord.word, settings])

  const isExampleMode = activeSubMode === 'example'
  const currentExample = currentWord.examples?.[0]
  const sentenceText = currentExample?.en ?? ''
  const shouldRevealAnswer = manualReplayCount >= ANSWER_REVEAL_PLAY_COUNT
  const remainingReplayCount = Math.max(ANSWER_REVEAL_PLAY_COUNT - manualReplayCount, 0)

  const handleReplayClick = useCallback(() => {
    if (isExampleMode) {
      handlePlayExample()
    } else {
      handlePlayWord()
    }

    setManualReplayCount(count => Math.min(count + 1, ANSWER_REVEAL_PLAY_COUNT))
  }, [handlePlayExample, handlePlayWord, isExampleMode])

  useEffect(() => {
    if (!isExampleMode || !sentenceText) return
    const timerId = window.setTimeout(() => {
      handlePlayExample()
    }, 280)
    return () => {
      window.clearTimeout(timerId)
      stopAudio()
    }
  }, [currentWord.word, isExampleMode, sentenceText, handlePlayExample])

  useEffect(() => {
    if (spellingResult !== 'wrong') return
    const timerId = window.setTimeout(() => {
      if (isExampleMode && sentenceText) {
        handlePlayExample()
        return
      }
      handlePlayWord()
    }, 320)
    return () => window.clearTimeout(timerId)
  }, [spellingResult, isExampleMode, sentenceText, handlePlayExample, handlePlayWord])

  return (
    <div className="practice-page">
      <PrevWordBlock previousWord={previousWord} lastState={lastState} onGoBack={onGoBack} />

      <div className="dictation-container">
        {hasExamples && !spellingResult && (
          <div className="dictation-submode-toggle">
            <button
              className={`submode-btn ${activeSubMode === 'word' ? 'active' : ''}`}
              onClick={() => setDictationSubMode('word')}
            >
              单词拼写
            </button>
            <button
              className={`submode-btn ${activeSubMode === 'example' ? 'active' : ''}`}
              onClick={() => setDictationSubMode('example')}
            >
              例句填空
            </button>
          </div>
        )}

        <div className="dictation-play-area">
          <h2 className="dictation-mode-title">
            {isExampleMode ? '根据语境填写单词' : '根据发音写出单词'}
          </h2>
          <button
            className="play-btn-large"
            onClick={handleReplayClick}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
            </svg>
          </button>
          <p className="dictation-hint">
            {isExampleMode ? '听例句，写出空缺的单词' : '听发音，拼写单词'}
          </p>
          <p className={`dictation-replay-hint${shouldRevealAnswer ? ' revealed' : ''}`}>
            {shouldRevealAnswer
              ? '已显示答案，可直接输入后提交'
              : manualReplayCount === 0
                ? `可重复播放，手动播放 ${ANSWER_REVEAL_PLAY_COUNT} 次后显示答案`
                : `已手动播放 ${manualReplayCount}/${ANSWER_REVEAL_PLAY_COUNT} 次，再点 ${remainingReplayCount} 次显示答案`}
          </p>
        </div>

        <div className="dictation-content-area">
          <div className={`dictation-letter-hint${isExampleMode ? ' dictation-item-hidden' : ''}`}>
            {currentWord.word.split('').map((ch, i) => (
              ch === ' ' ? <span key={i} className="letter-hint-space" /> : <span key={i} className="letter-hint-blank">_</span>
            ))}
          </div>

          {sentenceText && (
            <div className={`dictation-example-area${!isExampleMode ? ' dictation-item-hidden' : ''}`}>
              <div className="dictation-example-sentence">
                {buildBlankSentence(sentenceText, currentWord.word)}
              </div>
              <div className="dictation-example-definition">
                <span className="word-pos-tag">{currentWord.pos}</span>
                {currentWord.definition}
              </div>
            </div>
          )}
        </div>

        {shouldRevealAnswer && !spellingResult && (
          <div className="spelling-answer">
            {isExampleMode
              ? <>正确答案：<strong>{currentWord.word}</strong>{currentExample?.zh ? <span className="spelling-answer-sentence"> — {currentExample.zh}</span> : null}</>
              : <>正确答案：<strong>{currentWord.word}</strong></>}
          </div>
        )}

        <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
          <input
            ref={spellingRef}
            type="text"
            className="spelling-input"
            value={spellingInput}
            onChange={e => onSpellingInputChange(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') onSpellingSubmit() }}
            placeholder={isExampleMode ? '输入空缺的单词...' : '输入你听到的单词...'}
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

      <BottomBar progressValue={progressValue} total={total} queueIndex={0} />
    </div>
  )
}
