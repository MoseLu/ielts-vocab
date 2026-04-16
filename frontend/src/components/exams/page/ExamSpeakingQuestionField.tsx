import { useMemo, useState } from 'react'

import type { ExamQuestion } from '../../../lib'
import { evaluateExamSpeaking } from '../../../features/exams/examApi'
import { sanitizeExamHtml } from '../../../features/exams/examHtml'
import { useSpeakingRecorder } from '../../../features/speech/hooks/useSpeakingRecorder'


interface QuestionResponseState {
  responseText?: string | null
  feedback?: Record<string, unknown>
}

interface ExamSpeakingQuestionFieldProps {
  question: ExamQuestion
  response: QuestionResponseState | null
  disabled: boolean
  hidePrompt?: boolean
  onChange: (questionId: number, patch: Record<string, unknown>) => void
  onPersist: () => Promise<void>
}

function stripHtmlTags(value: string): string {
  return value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

export function ExamSpeakingQuestionField({
  question,
  response,
  disabled,
  hidePrompt = false,
  onChange,
  onPersist,
}: ExamSpeakingQuestionFieldProps) {
  const recorder = useSpeakingRecorder()
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState('')

  const assessment = useMemo(() => {
    const payload = response?.feedback?.speakingAssessment
    return payload && typeof payload === 'object' ? payload as Record<string, unknown> : null
  }, [response?.feedback])

  async function handleEvaluate() {
    if (!recorder.audioBlob) {
      setError('请先完成录音，再发起评估')
      return
    }
    setEvaluating(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('audio', recorder.audioBlob, `exam-speaking-${question.id}.wav`)
      formData.append('promptText', stripHtmlTags(question.promptHtml))
      formData.append('part', '2')
      formData.append('topic', `Exam question ${question.questionNumber || question.sortOrder}`)
      formData.append('durationSeconds', String(recorder.durationSeconds || 0))
      const result = await evaluateExamSpeaking(formData)
      onChange(question.id, {
        responseText: result.transcript,
        durationSeconds: result.metrics.durationSeconds ?? recorder.durationSeconds ?? null,
        feedback: { speakingAssessment: result },
      })
      await onPersist()
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '口语评估失败')
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="exam-speaking-field">
      {!hidePrompt && (
        <div
          className="exam-speaking-field__prompt"
          dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(question.promptHtml) }}
        />
      )}

      <textarea
        className="exam-response-textarea exam-response-textarea--speaking"
        placeholder="可手动输入回答或保留 AI 转写结果"
        value={response?.responseText || ''}
        disabled={disabled}
        onChange={event => onChange(question.id, { responseText: event.target.value })}
      />

      <div className="exam-speaking-field__controls">
        <button
          type="button"
          className="exam-action-button"
          disabled={disabled || recorder.isRecording}
          onClick={() => void recorder.startRecording()}
        >
          开始录音
        </button>
        <button
          type="button"
          className="exam-action-button"
          disabled={disabled || !recorder.isRecording}
          onClick={() => void recorder.stopRecording()}
        >
          结束录音
        </button>
        <button
          type="button"
          className="exam-action-button exam-action-button--accent"
          disabled={disabled || evaluating}
          onClick={() => void handleEvaluate()}
        >
          {evaluating ? '评估中...' : 'AI 评估'}
        </button>
      </div>

      {recorder.audioUrl && (
        <audio className="exam-speaking-field__player" controls src={recorder.audioUrl}>
          <track kind="captions" />
        </audio>
      )}

      {(error || recorder.error) && <div className="exam-inline-error">{error || recorder.error}</div>}

      {assessment && (
        <div className="exam-feedback-card">
          <div className="exam-feedback-card__header">
            <strong>口语反馈</strong>
            <span>Band {String(assessment.overallBand || '—')}</span>
          </div>
          <p>{String((assessment.feedback as Record<string, unknown> | undefined)?.summary || '已生成评估')}</p>
        </div>
      )}
    </div>
  )
}

export default ExamSpeakingQuestionField
