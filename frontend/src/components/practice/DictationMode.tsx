// ── Dictation Mode Component ───────────────────────────────────────────────────

import { useRef, useEffect, useState, useCallback } from 'react'
import type { DictationModeProps, LastState } from './types'
import { buildBlankSentence } from './exampleSentence'
import { playExampleAudio, stopAudio } from './utils'
import {
  DictationErrorFeedback,
  DictationLiveStage,
} from './dictation/DictationModeFeedback'

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
  const safeTotal = Math.max(total, 1)
  const safeCurrent = Math.min(queueIndex + 1, safeTotal)

  return (
    <div className="dictation-progress">
      <div className="dictation-progress-meta">
        <span className="dictation-progress-label">练习进度</span>
        <span className="dictation-progress-count">{safeCurrent}/{safeTotal}</span>
      </div>
      <div className="dictation-progress-track">
        <div className="dictation-progress-fill" style={{ width: `${progressValue * 100}%` }}>
          <div className="dictation-progress-dot" />
        </div>
      </div>
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
  queueIndex,
  previousWord,
  lastState,
  spellingLocked = false,
  spellingFeedbackDismissing = false,
  spellingFeedbackSnapshot = null,
  favoriteSlot,
  speakingSlot,
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
  const wrongReplayNote = isExampleMode && sentenceText
    ? '系统正在重播例句，稍后重新填写。'
    : '系统正在重播发音，稍后重新拼写。'
  const hasHeaderActions = Boolean(favoriteSlot) || Boolean(speakingSlot)
  const wrongSubmittedAnswer = spellingFeedbackSnapshot ?? (spellingInput.trim() ? spellingInput : '未输入内容')
  const allowEditingWhileWrong = spellingResult === 'wrong' && (spellingLocked || spellingFeedbackDismissing)
  const disableSpellingInput = spellingResult === 'correct' || (spellingResult === 'wrong' && !allowEditingWhileWrong)
  const showSpellingActions = spellingResult === null
  const showHeader = hasExamples || hasHeaderActions
  const modeTitle = isExampleMode ? '根据语境填写单词' : '根据发音写出单词'
  const modeHint = isExampleMode ? '听例句，写出空缺的单词' : '听发音，拼写单词'
  const modeBadge = isExampleMode ? '例句填空' : '单词拼写'
  const replayButtonLabel = isExampleMode ? '重播例句，点击例句或按 Alt' : '重播发音，快捷键 Tab'

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
    <div className="practice-page practice-page--dictation">
      <PrevWordBlock previousWord={previousWord} lastState={lastState} onGoBack={onGoBack} />

      <div className="dictation-shell">
        <div className="dictation-card">
          {showHeader ? (
            <div className="dictation-card-header">
              <div className="dictation-card-header__side">
                {favoriteSlot ? (
                  <div className="dictation-card-header__action">{favoriteSlot}</div>
                ) : null}
              </div>
              <div className="dictation-card-header__center">
                {hasExamples ? (
                  <div className="dictation-submode-toggle">
                    <button
                      className={`submode-btn ${activeSubMode === 'word' ? 'active' : ''}`}
                      onClick={() => setDictationSubMode('word')}
                      disabled={spellingResult !== null}
                    >
                      单词拼写
                    </button>
                    <button
                      className={`submode-btn ${activeSubMode === 'example' ? 'active' : ''}`}
                      onClick={() => setDictationSubMode('example')}
                      disabled={spellingResult !== null}
                    >
                      例句填空
                    </button>
                  </div>
                ) : (
                  <div className="dictation-card-header__spacer" />
                )}
              </div>
              <div className="dictation-card-header__side dictation-card-header__side--action">
                {speakingSlot ? (
                  <div className="dictation-card-header__action">{speakingSlot}</div>
                ) : null}
              </div>
            </div>
          ) : null}

          <div className={`dictation-stage dictation-stage--${isExampleMode ? 'example' : 'word'}`}>
            <div className="dictation-play-panel">
              <span className="dictation-mode-badge">{modeBadge}</span>
              <h2 className="dictation-mode-title">{modeTitle}</h2>
              <p className="dictation-hint">{modeHint}</p>
              <button
                className="play-btn-large dictation-play-btn"
                onClick={handleReplayClick}
                title={replayButtonLabel}
                aria-label={replayButtonLabel}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                </svg>
              </button>
              <p className={`dictation-replay-hint${shouldRevealAnswer ? ' revealed' : ''}`}>
                {shouldRevealAnswer
                  ? '已显示答案，可直接输入后提交'
                  : manualReplayCount === 0
                    ? `可重复播放，手动播放 ${ANSWER_REVEAL_PLAY_COUNT} 次后显示答案`
                    : `已手动播放 ${manualReplayCount}/${ANSWER_REVEAL_PLAY_COUNT} 次，再点 ${remainingReplayCount} 次显示答案`}
              </p>
            </div>

            <div className="dictation-content-card">
              {sentenceText && isExampleMode && (
                <div className="dictation-example-area">
                  <div className="dictation-example-meta">
                    <span className="dictation-example-label">语境线索</span>
                    {(currentWord.pos || currentWord.definition) ? (
                      <div className="dictation-example-definition">
                        {currentWord.pos ? <span className="word-pos-tag">{currentWord.pos}</span> : null}
                        {currentWord.definition}
                      </div>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    className="dictation-example-sentence dictation-example-sentence--interactive"
                    title="点击例句重播"
                    onClick={handleReplayClick}
                  >
                    {buildBlankSentence(sentenceText, currentWord.word)}
                  </button>
                </div>
              )}

              <div className={`dictation-response-stage${spellingFeedbackDismissing ? ' is-dismissing' : ''}`}>
                {spellingResult === 'wrong' ? (
                  <DictationErrorFeedback
                    correctWord={currentWord.word}
                    phonetic={currentWord.phonetic}
                    submittedAnswer={wrongSubmittedAnswer}
                    translation={isExampleMode ? currentExample?.zh : undefined}
                    replayNote={wrongReplayNote}
                  />
                ) : (
                  <DictationLiveStage
                    targetWord={currentWord.word}
                    spellingInput={spellingInput}
                    shouldRevealAnswer={shouldRevealAnswer}
                    revealDetail={isExampleMode ? currentExample?.zh : undefined}
                    isExampleMode={isExampleMode}
                  />
                )}
              </div>
            </div>
          </div>

          <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
            <input
              ref={spellingRef}
              type="text"
              className="spelling-input"
              value={spellingInput}
              onChange={e => onSpellingInputChange(e.target.value)}
              onKeyDown={e => {
                if (e.key !== 'Enter') return
                e.preventDefault()
                if (e.repeat) return
                onSpellingSubmit('enter')
              }}
              placeholder={isExampleMode ? '输入空缺的单词...' : '输入你听到的单词...'}
              disabled={disableSpellingInput}
              autoComplete="off"
              spellCheck={false}
            />
            {showSpellingActions && (
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
            {showSpellingActions && (
              <button className="spelling-submit-btn" onClick={() => onSpellingSubmit('button')} title="确认">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </button>
            )}
          </div>

          <BottomBar progressValue={progressValue} total={total} queueIndex={queueIndex} />
        </div>
      </div>
    </div>
  )
}
