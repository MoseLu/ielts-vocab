import type { ExamQuestion } from '../../../lib'
import { sanitizeExamHtml } from '../../../features/exams/examHtml'
import { ExamSpeakingQuestionField } from './ExamSpeakingQuestionField'


interface QuestionResponseState {
  responseText?: string | null
  selectedChoices?: string[]
  isCorrect?: boolean | null
  score?: number | null
  feedback?: Record<string, unknown>
}

interface ExamQuestionFieldsProps {
  question: ExamQuestion
  response: QuestionResponseState | null
  disabled: boolean
  className?: string
  hidePrompt?: boolean
  onChange: (questionId: number, patch: Record<string, unknown>) => void
  onPersist: () => Promise<void>
}

function toggleChoice(current: string[], value: string): string[] {
  return current.includes(value)
    ? current.filter(item => item !== value)
    : [...current, value]
}

function renderObjectiveFeedback(question: ExamQuestion, response: QuestionResponseState | null) {
  if (!response || response.isCorrect == null) return null
  return (
    <div className={`exam-feedback-card ${response.isCorrect ? 'is-correct' : 'is-wrong'}`}>
      <div className="exam-feedback-card__header">
        <strong>{response.isCorrect ? '回答正确' : '需要修正'}</strong>
        <span>{response.score ?? 0}/{question.acceptedAnswers.length > 0 ? 1 : 0}</span>
      </div>
      {!response.isCorrect && question.acceptedAnswers.length > 0 && (
        <p>参考答案：{question.acceptedAnswers.join(' / ')}</p>
      )}
    </div>
  )
}

function renderWritingFeedback(response: QuestionResponseState | null) {
  const writing = response?.feedback?.writing
  if (!writing || typeof writing !== 'object') return null
  const payload = writing as Record<string, unknown>
  const strengths = Array.isArray(payload.strengths) ? payload.strengths : []
  const priorities = Array.isArray(payload.priorities) ? payload.priorities : []

  return (
    <div className="exam-feedback-card">
      <div className="exam-feedback-card__header">
        <strong>写作反馈</strong>
        <span>{String(payload.estimatedBand || 'Draft')}</span>
      </div>
      <p>{String(payload.summary || '已生成写作反馈')}</p>
      {strengths.length > 0 && <p>亮点：{strengths.map(item => String(item)).join('；')}</p>}
      {priorities.length > 0 && <p>优先改进：{priorities.map(item => String(item)).join('；')}</p>}
    </div>
  )
}

export function ExamQuestionFields({
  question,
  response,
  disabled,
  className = '',
  hidePrompt = false,
  onChange,
  onPersist,
}: ExamQuestionFieldsProps) {
  if (question.questionType === 'speaking_prompt') {
    return (
      <ExamSpeakingQuestionField
        question={question}
        response={response}
        disabled={disabled}
        hidePrompt={hidePrompt}
        onChange={onChange}
        onPersist={onPersist}
      />
    )
  }

  const selectedChoices = response?.selectedChoices || []
  const classes = ['exam-question-fields', className].filter(Boolean).join(' ')

  return (
    <div className={classes}>
      {!hidePrompt && (
        <div
          className="exam-question-fields__prompt"
          dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(question.promptHtml) }}
        />
      )}

      {(question.questionType === 'single_choice' || question.questionType === 'multiple_choice' || question.questionType === 'matching') && (
        <div className="exam-choice-list">
          {question.choices.map(choice => {
            const checked = selectedChoices.includes(choice.key)
            const inputType = question.questionType === 'single_choice' ? 'radio' : 'checkbox'
            return (
              <label key={choice.id} className={`exam-choice-item ${checked ? 'is-selected' : ''}`}>
                <input
                  type={inputType}
                  name={`question-${question.id}`}
                  checked={checked}
                  disabled={disabled}
                  onChange={() => {
                    const nextSelected = question.questionType === 'single_choice'
                      ? [choice.key]
                      : toggleChoice(selectedChoices, choice.key)
                    onChange(question.id, { selectedChoices: nextSelected })
                  }}
                />
                <span className="exam-choice-item__content" dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(choice.contentHtml) }} />
              </label>
            )
          })}
        </div>
      )}

      {(question.questionType === 'fill_blank' || question.questionType === 'short_answer') && (
        <input
          className="exam-response-input"
          placeholder="输入你的答案"
          value={response?.responseText || ''}
          disabled={disabled}
          onChange={event => onChange(question.id, { responseText: event.target.value })}
        />
      )}

      {question.questionType === 'writing_prompt' && (
        <textarea
          className="exam-response-textarea"
          placeholder="开始写作..."
          value={response?.responseText || ''}
          disabled={disabled}
          onChange={event => onChange(question.id, { responseText: event.target.value })}
        />
      )}

      {renderObjectiveFeedback(question, response)}
      {question.questionType === 'writing_prompt' && renderWritingFeedback(response)}

      {!disabled && question.questionType !== 'speaking_prompt' && (
        <div className="exam-question-fields__hint">输入后会自动保存。</div>
      )}
    </div>
  )
}

export default ExamQuestionFields
