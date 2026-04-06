import React from 'react'

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

export interface DictationErrorFeedbackProps {
  correctWord: string
  phonetic?: string
  submittedAnswer: string
  translation?: string
  replayNote: string
}

export interface DictationLiveStageProps {
  targetWord: string
  spellingInput: string
  shouldRevealAnswer: boolean
  revealDetail?: string
  isExampleMode: boolean
}

function buildLetterComparison(correctWord: string, submittedAnswer: string): DictationComparisonCell[] {
  const correctChars = Array.from(correctWord)
  const submittedChars = Array.from(submittedAnswer)
  const distance = Array.from(
    { length: submittedChars.length + 1 },
    () => Array<number>(correctChars.length + 1).fill(0),
  )

  for (let row = 0; row <= submittedChars.length; row += 1) distance[row][0] = row
  for (let column = 0; column <= correctChars.length; column += 1) distance[0][column] = column

  for (let row = 1; row <= submittedChars.length; row += 1) {
    for (let column = 1; column <= correctChars.length; column += 1) {
      if (submittedChars[row - 1].toLowerCase() === correctChars[column - 1].toLowerCase()) {
        distance[row][column] = distance[row - 1][column - 1]
      } else {
        distance[row][column] = Math.min(
          distance[row - 1][column - 1] + 1,
          distance[row - 1][column] + 1,
          distance[row][column - 1] + 1,
        )
      }
    }
  }

  const cells: DictationComparisonCell[] = []
  let submittedIndex = submittedChars.length
  let correctIndex = correctChars.length

  while (submittedIndex > 0 || correctIndex > 0) {
    const submittedChar = submittedChars[submittedIndex - 1]
    const correctChar = correctChars[correctIndex - 1]

    if (
      submittedIndex > 0
      && correctIndex > 0
      && submittedChar.toLowerCase() === correctChar.toLowerCase()
      && distance[submittedIndex][correctIndex] === distance[submittedIndex - 1][correctIndex - 1]
    ) {
      cells.push({ correctChar, submittedChar, operation: 'match' })
      submittedIndex -= 1
      correctIndex -= 1
      continue
    }

    if (
      submittedIndex > 0
      && correctIndex > 0
      && distance[submittedIndex][correctIndex] === distance[submittedIndex - 1][correctIndex - 1] + 1
    ) {
      cells.push({ correctChar, submittedChar, operation: 'replace' })
      submittedIndex -= 1
      correctIndex -= 1
      continue
    }

    if (
      correctIndex > 0
      && distance[submittedIndex][correctIndex] === distance[submittedIndex][correctIndex - 1] + 1
    ) {
      cells.push({ correctChar, submittedChar: null, operation: 'missing' })
      correctIndex -= 1
      continue
    }

    cells.push({ correctChar: null, submittedChar, operation: 'extra' })
    submittedIndex -= 1
  }

  return cells.reverse()
}

function buildTypingPreviewCells(targetWord: string, submittedAnswer: string): DictationTypingCell[] {
  const targetChars = Array.from(targetWord)
  const submittedChars = Array.from(submittedAnswer)
  return Array.from({ length: Math.max(targetChars.length, submittedChars.length) }, (_value, index) => {
    const targetChar = targetChars[index]
    const submittedChar = submittedChars[index]

    if (targetChar === ' ') return { char: '', state: 'space' }
    if (targetChar == null) return { char: submittedChar ?? '', state: submittedChar ? 'extra' : 'empty' }
    if (!submittedChar || submittedChar === ' ') return { char: '', state: 'empty' }
    return { char: submittedChar, state: 'filled' }
  })
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
          const char = row === 'correct' ? (cell.correctChar ?? '') : (cell.submittedChar ?? '○')
          const state = row === 'correct'
            ? (cell.operation === 'match' ? 'is-match' : cell.operation === 'extra' ? 'is-ghost' : 'is-focus')
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
  return (
    <span className="dictation-live-preview-word" aria-label={plainText || '未输入内容'}>
      <span className="sr-only">{plainText || '未输入内容'}</span>
      <span className="dictation-live-letter-row" aria-hidden="true">
        {buildTypingPreviewCells(targetWord, plainText).map((cell, index) => (
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

export function DictationErrorFeedback({
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

export function DictationLiveStage({
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
        <span className="dictation-live-preview-label">{isExampleMode ? '当前填写' : '当前拼写'}</span>
        {renderTypingPreviewWord(targetWord, spellingInput)}
      </div>
    </div>
  )
}
