// ── Dictation Mode Component ───────────────────────────────────────────────────

import React, { useRef, useEffect, useState, useCallback } from 'react'
import type { DictationModeProps, LastState } from './types'
import PracticeStageGuide from './PracticeStageGuide.tsx'
import { buildDictationStageGuide } from './practiceStageGuide'
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

interface DictationErrorFeedbackProps {
  correctWord: string
  phonetic?: string
  submittedAnswer: string
  translation?: string
  replayNote: string
}

type DictationComparisonOperation = 'match' | 'replace' | 'extra' | 'missing'
type DictationTypingCellState = 'filled' | 'empty' | 'extra' | 'space'

interface DictationComparisonCell {
  correctChar: string | null
  submittedChar: string | null
  operation: DictationComparisonOperation
}

interface DictationTypingCell {
  char: string
  state: DictationTypingCellState
}

function buildLetterComparison(correctWord: string, submittedAnswer: string): DictationComparisonCell[] {
  const correctChars = Array.from(correctWord)
  const submittedChars = Array.from(submittedAnswer)
  const submittedLength = submittedChars.length
  const correctLength = correctChars.length

  const distance = Array.from({ length: submittedLength + 1 }, () => Array<number>(correctLength + 1).fill(0))

  for (let i = 0; i <= submittedLength; i += 1) distance[i][0] = i
  for (let j = 0; j <= correctLength; j += 1) distance[0][j] = j

  for (let i = 1; i <= submittedLength; i += 1) {
    for (let j = 1; j <= correctLength; j += 1) {
      const submittedChar = submittedChars[i - 1]
      const correctChar = correctChars[j - 1]

      if (submittedChar.toLowerCase() === correctChar.toLowerCase()) {
        distance[i][j] = distance[i - 1][j - 1]
        continue
      }

      distance[i][j] = Math.min(
        distance[i - 1][j - 1] + 1,
        distance[i - 1][j] + 1,
        distance[i][j - 1] + 1,
      )
    }
  }

  const comparison: DictationComparisonCell[] = []
  let submittedIndex = submittedLength
  let correctIndex = correctLength

  while (submittedIndex > 0 || correctIndex > 0) {
    const submittedChar = submittedChars[submittedIndex - 1]
    const correctChar = correctChars[correctIndex - 1]

    if (
      submittedIndex > 0
      && correctIndex > 0
      && submittedChar.toLowerCase() === correctChar.toLowerCase()
      && distance[submittedIndex][correctIndex] === distance[submittedIndex - 1][correctIndex - 1]
    ) {
      comparison.push({
        correctChar,
        submittedChar,
        operation: 'match',
      })
      submittedIndex -= 1
      correctIndex -= 1
      continue
    }

    if (
      submittedIndex > 0
      && correctIndex > 0
      && distance[submittedIndex][correctIndex] === distance[submittedIndex - 1][correctIndex - 1] + 1
    ) {
      comparison.push({
        correctChar,
        submittedChar,
        operation: 'replace',
      })
      submittedIndex -= 1
      correctIndex -= 1
      continue
    }

    if (
      correctIndex > 0
      && distance[submittedIndex][correctIndex] === distance[submittedIndex][correctIndex - 1] + 1
    ) {
      comparison.push({
        correctChar,
        submittedChar: null,
        operation: 'missing',
      })
      correctIndex -= 1
      continue
    }

    comparison.push({
      correctChar: null,
      submittedChar,
      operation: 'extra',
    })
    submittedIndex -= 1
  }

  return comparison.reverse()
}

function buildTypingPreviewCells(targetWord: string, submittedAnswer: string): DictationTypingCell[] {
  const targetChars = Array.from(targetWord)
  const submittedChars = Array.from(submittedAnswer)
  const totalLength = Math.max(targetChars.length, submittedChars.length)
  const cells: DictationTypingCell[] = []

  for (let index = 0; index < totalLength; index += 1) {
    const targetChar = targetChars[index]
    const submittedChar = submittedChars[index]

    if (targetChar === ' ') {
      cells.push({ char: '', state: 'space' })
      continue
    }

    if (targetChar == null) {
      cells.push({ char: submittedChar ?? '', state: submittedChar ? 'extra' : 'empty' })
      continue
    }

    if (!submittedChar || submittedChar === ' ') {
      cells.push({ char: '', state: 'empty' })
      continue
    }

    cells.push({ char: submittedChar, state: 'filled' })
  }

  return cells
}

function renderComparisonWord(
  cells: DictationComparisonCell[],
  row: 'correct' | 'submitted',
  plainText: string,
) {
  return (
    <span className={`dictation-error-word dictation-error-word-${row}`} aria-label={plainText}>
      <span className="sr-only">{plainText}</span>
      <span className="dictation-error-letter-row" aria-hidden="true">
        {cells.map((cell, index) => {
          const char = row === 'correct'
            ? (cell.correctChar ?? '')
            : (cell.submittedChar ?? '○')

          const state = row === 'correct'
            ? (
                cell.operation === 'match'
                  ? 'is-match'
                  : cell.operation === 'extra'
                    ? 'is-ghost'
                    : 'is-focus'
              )
            : (
                cell.operation === 'match'
                  ? 'is-match'
                  : cell.operation === 'missing'
                    ? 'is-missing'
                    : cell.operation === 'extra'
                      ? 'is-extra'
                      : 'is-focus'
              )

          return (
            <span
              key={`${row}-${index}-${cell.correctChar ?? 'empty'}-${cell.submittedChar ?? 'empty'}`}
              className={`dictation-error-letter ${state}`}
              style={{ '--letter-order': index } as React.CSSProperties}
            >
              {char || '\u00A0'}
            </span>
          )
        })}
      </span>
    </span>
  )
}

function renderTypingPreviewWord(targetWord: string, plainText: string) {
  const cells = buildTypingPreviewCells(targetWord, plainText)

  return (
    <span className="dictation-live-preview-word" aria-label={plainText || '未输入内容'}>
      <span className="sr-only">{plainText || '未输入内容'}</span>
      <span className="dictation-live-letter-row" aria-hidden="true">
        {cells.map((cell, index) => (
          <span
            key={`preview-${index}-${cell.char || 'empty'}-${cell.state}`}
            className={`dictation-live-letter is-${cell.state}`}
          >
            {cell.char || '\u00A0'}
          </span>
        ))}
      </span>
    </span>
  )
}

function DictationErrorFeedback({
  correctWord,
  phonetic,
  submittedAnswer,
  translation,
  replayNote,
}: DictationErrorFeedbackProps) {
  const comparison = buildLetterComparison(correctWord, submittedAnswer)

  return (
    <div className="dictation-error-feedback" role="status" aria-live="polite">
      <div className="dictation-error-head">
        <span className="dictation-error-badge">拼写错误</span>
        <p className="dictation-error-support">红色字块是出错位置，空心圈表示漏写。</p>
      </div>

      <div className="dictation-error-stack">
        <div className="dictation-error-item dictation-error-item-correct">
          <span className="dictation-error-label">正确拼写</span>
          {renderComparisonWord(comparison, 'correct', correctWord)}
          {phonetic ? <span className="dictation-error-meta">{phonetic}</span> : null}
          {translation ? <span className="dictation-error-detail">例句释义：{translation}</span> : null}
        </div>

        <div className="dictation-error-item dictation-error-item-wrong">
          <span className="dictation-error-label">你的输入</span>
          {renderComparisonWord(comparison, 'submitted', submittedAnswer)}
        </div>
      </div>

      <div className="dictation-error-underline" aria-hidden="true" />

      <p className="dictation-error-note">{replayNote}</p>
    </div>
  )
}

interface DictationLiveStageProps {
  targetWord: string
  spellingInput: string
  shouldRevealAnswer: boolean
  revealDetail?: string
  isExampleMode: boolean
}

function DictationLiveStage({
  targetWord,
  spellingInput,
  shouldRevealAnswer,
  revealDetail,
  isExampleMode,
}: DictationLiveStageProps) {
  return (
    <div className="dictation-live-stage">
      {shouldRevealAnswer && (
        <div className="dictation-live-answer">
          <span className="dictation-live-answer-label">正确答案</span>
          <strong className="dictation-live-answer-word">{targetWord}</strong>
          {revealDetail ? <span className="dictation-live-answer-detail">{revealDetail}</span> : null}
        </div>
      )}

      <div className={`dictation-live-preview${spellingInput ? ' has-input' : ''}`}>
        <span className="dictation-live-preview-label">
          {isExampleMode ? '当前填写' : '当前拼写'}
        </span>
        {renderTypingPreviewWord(targetWord, spellingInput)}
      </div>
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
          {targetWord.split('').map((_, j) => <span key={j} className="example-blank-slot" />)}
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
  queueIndex,
  previousWord,
  lastState,
  errorMode = false,
  reviewMode = false,
  spellingLocked = false,
  spellingFeedbackDismissing = false,
  spellingFeedbackSnapshot = null,
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
  const stageGuide = buildDictationStageGuide({
    queueIndex,
    total,
    errorMode,
    reviewMode,
    isExampleMode,
    phase: spellingResult === null ? 'challenge' : 'review',
    isCorrect: spellingResult === 'correct',
  })
  const currentExample = currentWord.examples?.[0]
  const sentenceText = currentExample?.en ?? ''
  const shouldRevealAnswer = manualReplayCount >= ANSWER_REVEAL_PLAY_COUNT
  const remainingReplayCount = Math.max(ANSWER_REVEAL_PLAY_COUNT - manualReplayCount, 0)
  const wrongReplayNote = isExampleMode && sentenceText
    ? '系统正在重播例句，稍后重新填写。'
    : '系统正在重播发音，稍后重新拼写。'
  const wrongSubmittedAnswer = spellingFeedbackSnapshot ?? (spellingInput.trim() ? spellingInput : '未输入内容')
  const allowEditingWhileWrong = spellingResult === 'wrong' && (spellingLocked || spellingFeedbackDismissing)
  const disableSpellingInput = spellingResult === 'correct' || (spellingResult === 'wrong' && !allowEditingWhileWrong)
  const showSpellingActions = spellingResult === null

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
        {hasExamples && (
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
        )}

        <PracticeStageGuide guide={stageGuide} />

        <div className="dictation-play-area">
          <h2 className="dictation-mode-title">
            {isExampleMode ? '根据语境填写单词' : '根据发音写出单词'}
          </h2>
          <button
            className="play-btn-large"
            onClick={handleReplayClick}
            title={isExampleMode ? '重播例句，快捷键 Tab' : '重播发音，快捷键 Tab'}
            aria-label={isExampleMode ? '重播例句，快捷键 Tab' : '重播发音，快捷键 Tab'}
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
          {sentenceText && isExampleMode && (
            <div className="dictation-example-area">
              <div className="dictation-example-sentence">
                {buildBlankSentence(sentenceText, currentWord.word)}
              </div>
              <div className="dictation-example-definition">
                <span className="word-pos-tag">{currentWord.pos}</span>
                {currentWord.definition}
              </div>
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
      </div>

      <BottomBar progressValue={progressValue} total={total} queueIndex={queueIndex} />
    </div>
  )
}
