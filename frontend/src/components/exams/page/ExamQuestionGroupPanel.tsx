import type { ReactNode } from 'react'
import type { ExamQuestion } from '../../../lib'
import type { ExamResponseDraft } from '../../../features/exams/examApi'
import { sanitizeExamHtml } from '../../../features/exams/examHtml'
import { ExamQuestionFields } from './ExamQuestionFields'

interface ExamQuestionGroupPanelProps {
  questions: ExamQuestion[]
  promptHtml?: string | null
  responseMap: Record<number, ExamResponseDraft>
  disabled: boolean
  onChange: (questionId: number, patch: Record<string, unknown>) => void
  onPersist: () => Promise<void>
}

function normalizeQuestionNumber(question: ExamQuestion): number {
  return question.questionNumber ?? question.sortOrder
}

function buildSharedPromptHtml(questions: ExamQuestion[]) {
  const prompts = questions
    .map(question => question.promptHtml.trim())
    .filter(Boolean)

  if (prompts.length === 0) return null

  const first = prompts[0]
  return prompts.every(prompt => prompt === first) ? first : null
}

function buildQuestionRangeLabel(questions: ExamQuestion[]) {
  if (questions.length === 0) return ''
  const numbers = questions.map(normalizeQuestionNumber)
  const start = Math.min(...numbers)
  const end = Math.max(...numbers)
  return start === end ? `Question ${start}` : `Questions ${start}-${end}`
}

function supportsInlineBlankPrompt(questions: ExamQuestion[], sharedPromptHtml: string | null) {
  if (!sharedPromptHtml) return false
  const supported = questions.every(
    question => question.questionType === 'fill_blank' || question.questionType === 'short_answer',
  )
  if (!supported) return false

  const plain = sanitizeExamHtml(sharedPromptHtml).replace(/<[^>]+>/g, ' ')
  return /[0-9]\s*[.。．…•·]{4,}/.test(plain)
}

function buildPromptLines(sharedPromptHtml: string) {
  return sanitizeExamHtml(sharedPromptHtml)
    .replace(/<\/p>/gi, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .split('\n')
    .map(line => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
}

function isRangeLine(line: string) {
  return /^Questions?\s+\d+\s*-\s*\d+$/i.test(line)
}

function isInstructionLine(line: string) {
  return /^(Complete the|Write |Choose |In boxes |TRUE if|FALSE if|NOT GIVEN if)/i.test(line)
}

function isSectionHeadingLine(line: string) {
  if (isRangeLine(line) || isInstructionLine(line) || line.endsWith(':')) return false
  if (/^[A-Z' ]{4,}$/.test(line)) return true
  return /^[A-Z][A-Za-z' ]{3,40}$/.test(line) && line.split(' ').length <= 5
}

function looksLikeLabelLine(line: string) {
  if (isRangeLine(line) || isInstructionLine(line) || isSectionHeadingLine(line)) return false
  return line.endsWith(':') || (
    /^[A-Z][A-Za-z'() /-]{2,28}$/.test(line)
    && !/[.!?]/.test(line)
    && !/^[•-]/.test(line)
  )
}

function detectInlinePromptMode(lines: string[]) {
  return lines.some(line => /Complete the form below|REPORT FORM/i.test(line)) ? 'form' : 'notes'
}

function buildInlineLineClass(line: string) {
  if (isRangeLine(line)) return 'exam-inline-line exam-inline-line--range'
  if (isInstructionLine(line)) return 'exam-inline-line exam-inline-line--instruction'
  if (isSectionHeadingLine(line)) return 'exam-inline-line exam-inline-line--section'
  return 'exam-inline-line'
}

function renderInlineLine(
  line: string,
  questions: ExamQuestion[],
  responseMap: Record<number, ExamResponseDraft>,
  disabled: boolean,
  onChange: (questionId: number, patch: Record<string, unknown>) => void,
  cursorRef: { value: number },
) {
  const parts: ReactNode[] = []
  const pattern = /([0-9]\s*[.。．…•·]{4,})/g
  let lastIndex = 0
  let match = pattern.exec(line)

  while (match) {
    if (match.index > lastIndex) {
      parts.push(line.slice(lastIndex, match.index))
    }

      const question = questions[cursorRef.value]
    if (question) {
      parts.push(
        <span
          key={`blank-${question.id}`}
          id={`exam-question-${question.id}`}
          className="exam-inline-blank-wrap"
        >
          <span className="exam-inline-blank-number">#{question.questionNumber ?? question.sortOrder}</span>
          <input
            className="exam-inline-blank"
            value={responseMap[question.id]?.responseText || ''}
            disabled={disabled}
            onChange={event => onChange(question.id, { responseText: event.target.value })}
          />
        </span>,
      )
      cursorRef.value += 1
    } else {
      parts.push(match[0])
    }

    lastIndex = match.index + match[0].length
    match = pattern.exec(line)
  }

  if (lastIndex < line.length) {
    parts.push(line.slice(lastIndex))
  }

  return parts
}

function renderFormSheet(
  lines: string[],
  questions: ExamQuestion[],
  responseMap: Record<number, ExamResponseDraft>,
  disabled: boolean,
  onChange: (questionId: number, patch: Record<string, unknown>) => void,
  cursorRef: { value: number },
) {
  let bodyStart = 0
  while (bodyStart < lines.length && (isRangeLine(lines[bodyStart]) || isInstructionLine(lines[bodyStart]))) {
    bodyStart += 1
  }

  const introLines = lines.slice(0, bodyStart)
  const bodyLines = lines.slice(bodyStart)
  const rows: ReactNode[] = []

  for (let index = 0; index < bodyLines.length; index += 1) {
    const line = bodyLines[index]
    const next = bodyLines[index + 1] || ''

    if (isSectionHeadingLine(line)) {
      rows.push(
        <div key={`section-${index}`} className="exam-inline-form__section">
          {line}
        </div>,
      )
      continue
    }

    if (looksLikeLabelLine(line) && next && !isSectionHeadingLine(next) && !isInstructionLine(next)) {
      rows.push(
        <div key={`row-${index}`} className="exam-inline-form__row">
          <div className="exam-inline-form__label">{line.replace(/:$/, '')}</div>
          <div className="exam-inline-form__value">
            {renderInlineLine(next, questions, responseMap, disabled, onChange, cursorRef)}
          </div>
        </div>,
      )
      index += 1
      continue
    }

    rows.push(
      <div key={`full-${index}`} className="exam-inline-form__row exam-inline-form__row--full">
        <div className="exam-inline-form__value">
          {renderInlineLine(line, questions, responseMap, disabled, onChange, cursorRef)}
        </div>
      </div>,
    )
  }

  return (
    <div className="exam-inline-sheet exam-inline-sheet--form">
      <div className="exam-inline-sheet__intro">
        {introLines.map((line, index) => (
          <p key={`intro-${index}`} className={buildInlineLineClass(line)}>
            {line}
          </p>
        ))}
      </div>
      <div className="exam-inline-form">{rows}</div>
    </div>
  )
}

function renderNotesSheet(
  lines: string[],
  questions: ExamQuestion[],
  responseMap: Record<number, ExamResponseDraft>,
  disabled: boolean,
  onChange: (questionId: number, patch: Record<string, unknown>) => void,
  cursorRef: { value: number },
) {
  return (
    <div className="exam-inline-sheet exam-inline-sheet--notes">
      {lines.map((line, index) => (
        <p key={`note-${index}`} className={buildInlineLineClass(line)}>
          {renderInlineLine(line, questions, responseMap, disabled, onChange, cursorRef)}
        </p>
      ))}
    </div>
  )
}

export function ExamQuestionGroupPanel({
  questions,
  promptHtml = null,
  responseMap,
  disabled,
  onChange,
  onPersist,
}: ExamQuestionGroupPanelProps) {
  const sharedPromptHtml = promptHtml || buildSharedPromptHtml(questions)
  const rangeLabel = buildQuestionRangeLabel(questions)
  const inlineBlankPrompt = supportsInlineBlankPrompt(questions, sharedPromptHtml)
  const promptLines = inlineBlankPrompt && sharedPromptHtml ? buildPromptLines(sharedPromptHtml) : []
  const inlinePromptMode = detectInlinePromptMode(promptLines)
  const inlineCursor = { value: 0 }

  return (
    <div className="exam-question-group">
      {sharedPromptHtml && (
        <div className="exam-question-group__prompt">
          <div className="exam-question-group__prompt-meta">
            <strong>{rangeLabel}</strong>
            <span>{questions[0]?.questionType || ''}</span>
          </div>
          {inlineBlankPrompt ? (
            <div className="exam-question-group__inline-sheet">
              {inlinePromptMode === 'form'
                ? renderFormSheet(promptLines, questions, responseMap, disabled, onChange, inlineCursor)
                : renderNotesSheet(promptLines, questions, responseMap, disabled, onChange, inlineCursor)}
            </div>
          ) : (
            <div
              className="exam-question-group__prompt-body"
              dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(sharedPromptHtml) }}
            />
          )}
        </div>
      )}

      {!inlineBlankPrompt && (
        <div className="exam-question-group__answers">
          {questions.map(question => (
            <article
              key={question.id}
              id={`exam-question-${question.id}`}
              className="exam-question-row"
            >
              <div className="exam-question-row__label">
                <strong>Q{normalizeQuestionNumber(question)}</strong>
                {!sharedPromptHtml && (
                  <span>{question.questionType}</span>
                )}
              </div>

              <div className="exam-question-row__field">
                <ExamQuestionFields
                  question={question}
                  response={responseMap[question.id] || null}
                  disabled={disabled}
                  hidePrompt={Boolean(sharedPromptHtml)}
                  className={sharedPromptHtml ? 'exam-question-fields--inline' : ''}
                  onChange={onChange}
                  onPersist={onPersist}
                />
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

export default ExamQuestionGroupPanel
