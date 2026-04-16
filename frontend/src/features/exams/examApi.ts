import {
  AISpeakingAssessmentResponseSchema,
  type ExamAttemptResultResponse,
  ExamAttemptResultResponseSchema,
  type ExamAttemptResponse,
  ExamAttemptResponseSchema,
  type ExamPaperDetailResponse,
  ExamPaperDetailResponseSchema,
  type ExamPapersResponse,
  ExamPapersResponseSchema,
} from '../../lib'
import { apiFetch } from '../../lib'
import { parseOrThrow } from '../../lib/validation'


export interface ExamResponseDraft {
  questionId: number
  responseText?: string | null
  selectedChoices?: string[]
  attachmentUrl?: string | null
  durationSeconds?: number | null
  isCorrect?: boolean | null
  score?: number | null
  feedback?: Record<string, unknown>
}

export async function listExamPapers(includeDraft = false): Promise<ExamPapersResponse> {
  const query = includeDraft ? '?include_draft=1' : ''
  return parseOrThrow(ExamPapersResponseSchema, await apiFetch(`/api/exams${query}`), 'listExamPapers')
}

export async function getExamPaper(paperId: number, includeDraft = false): Promise<ExamPaperDetailResponse> {
  const query = includeDraft ? '?include_draft=1' : ''
  return parseOrThrow(
    ExamPaperDetailResponseSchema,
    await apiFetch(`/api/exams/${paperId}${query}`),
    'getExamPaper',
  )
}

export async function createExamAttempt(paperId: number): Promise<ExamAttemptResponse> {
  return parseOrThrow(
    ExamAttemptResponseSchema,
    await apiFetch(`/api/exams/${paperId}/attempts`, { method: 'POST' }),
    'createExamAttempt',
  )
}

export async function saveExamResponses(attemptId: number, responses: ExamResponseDraft[]): Promise<ExamAttemptResponse> {
  return parseOrThrow(
    ExamAttemptResponseSchema,
    await apiFetch(`/api/exam-attempts/${attemptId}/responses`, {
      method: 'PATCH',
      body: JSON.stringify({ responses }),
    }),
    'saveExamResponses',
  )
}

export async function submitExamAttempt(attemptId: number): Promise<ExamAttemptResultResponse> {
  const payload = await apiFetch<{ result: ExamAttemptResultResponse }>(`/api/exam-attempts/${attemptId}/submit`, {
    method: 'POST',
  })
  return parseOrThrow(ExamAttemptResultResponseSchema, payload.result, 'submitExamAttempt')
}

export async function getExamAttemptResult(attemptId: number): Promise<ExamAttemptResultResponse> {
  return parseOrThrow(
    ExamAttemptResultResponseSchema,
    await apiFetch(`/api/exam-attempts/${attemptId}/result`),
    'getExamAttemptResult',
  )
}

export async function evaluateExamSpeaking(formData: FormData) {
  return parseOrThrow(
    AISpeakingAssessmentResponseSchema,
    await apiFetch('/api/ai/speaking/evaluate', { method: 'POST', body: formData }),
    'evaluateExamSpeaking',
  )
}
