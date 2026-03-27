// ── Dictation Mode Component ───────────────────────────────────────────────────

import React, { useRef, useEffect, useState } from 'react'
import type { DictationModeProps, LastState } from './types'
import { stopAudio } from './utils'

type DictationSubMode = 'word' | 'example'

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
  onSkip,
  onGoBack,
  onStartRecording,
  onStopRecording,
  onPlayWord,
}: DictationModeProps) {
  const spellingRef = useRef<HTMLInputElement>(null)
  // Default to example mode — falls back to word mode when no examples available
  const [dictationSubMode, setDictationSubMode] = useState<DictationSubMode>('example')

  // Determine if current word has examples for fill-in-blank mode
  const hasExamples = Boolean(currentWord.examples && currentWord.examples.length > 0)
  const activeSubMode: DictationSubMode = hasExamples ? dictationSubMode : 'word'

  useEffect(() => {
    if (spellingResult === null) {
      setTimeout(() => spellingRef.current?.focus(), 400)
    }
  }, [spellingResult, currentWord.word])

  // Reset to example mode on each new word (if examples are available)
  useEffect(() => {
    setDictationSubMode('example')
  }, [currentWord.word])

  const handlePlayWord = () => {
    onPlayWord(currentWord.word)
  }

  // Cache for TTS audio blob URLs (sentence text → blob URL)
  const [ttsAudioCache, setTtsAudioCache] = useState<Record<string, string>>({})
  // Track current TTS request to handle concurrent calls
  const ttsAbortRef = useRef<AbortController | null>(null)

  const handlePlayExample = () => {
    const example = currentWord.examples?.[0]
    if (!example) return

    // Stop any in-progress audio
    stopAudio()

    const sentence = example.en

    // If we already have a cached blob URL, play it directly
    if (ttsAudioCache[sentence]) {
      const audio = new Audio(ttsAudioCache[sentence])
      audio.play()
      return
    }

    // Cancel any pending TTS request
    if (ttsAbortRef.current) {
      ttsAbortRef.current.abort()
    }

    const controller = new AbortController()
    ttsAbortRef.current = controller

    // Call MiniMax TTS API
    fetch('/api/tts/example-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sentence, word: currentWord.word }),
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) throw new Error(`TTS error ${res.status}`)
        return res.blob()
      })
      .then(blob => {
        const url = URL.createObjectURL(blob)
        setTtsAudioCache(prev => ({ ...prev, [sentence]: url }))
        const audio = new Audio(url)
        audio.play()
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        console.warn('[DictationMode] TTS failed, falling back to speechSynthesis:', err)
        // Fallback: browser speechSynthesis
        if (!window.speechSynthesis) return
        window.speechSynthesis.cancel()
        const utterance = new SpeechSynthesisUtterance(sentence)
        utterance.lang = 'en-US'
        utterance.rate = parseFloat(String(settings.playbackSpeed ?? '0.8'))
        window.speechSynthesis.speak(utterance)
      })
  }

  const isExampleMode = activeSubMode === 'example'
  const currentExample = currentWord.examples?.[0]
  const sentenceText = currentExample?.en ?? ''

  return (
    <div className="practice-page">
      <PrevWordBlock previousWord={previousWord} lastState={lastState} onGoBack={onGoBack} />

      <div className="dictation-container">
        {/* Sub-mode toggle — only visible when examples are available */}
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
            onClick={isExampleMode ? handlePlayExample : handlePlayWord}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
            </svg>
          </button>
          <p className="dictation-hint">
            {isExampleMode ? '听例句，写出空缺的单词' : '听发音，拼写单词'}
          </p>
        </div>

        {/* Content area — grid-stacked to prevent height jumping on mode switch */}
        <div className="dictation-content-area">
          {/* Word spelling mode — original letter hint */}
          <div className={`dictation-letter-hint${isExampleMode ? ' dictation-item-hidden' : ''}`}>
            {currentWord.word.split('').map((ch, i) => (
              ch === ' ' ? <span key={i} className="letter-hint-space" /> : <span key={i} className="letter-hint-blank">_</span>
            ))}
          </div>

          {/* Example fill-in-the-blank mode */}
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

        {spellingResult === 'wrong' && (
          <div className="spelling-answer">
            {isExampleMode
              ? <>正确答案：<strong>{currentWord.word}</strong>
                {currentExample && <span className="spelling-answer-sentence"> — {currentExample.zh}</span>}
              </>
              : <>正确答案：<strong>{currentWord.word}</strong></>
            }
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

      <button className="skip-btn" onClick={() => {
        if (isExampleMode) {
          handlePlayExample()
          setTimeout(() => onSkip(), 800)
        } else {
          onSkip()
        }
      }}>不知道 <span className="shortcut-hint">(5)</span></button>
      <BottomBar progressValue={progressValue} total={total} queueIndex={0} />
    </div>
  )
}
