import { z } from 'zod'
import { apiFetch, safeParse } from '../../lib'

export const FollowReadScoreBandSchema = z.enum(['needs_work', 'near_pass', 'pass'])
export type FollowReadScoreBand = z.infer<typeof FollowReadScoreBandSchema>
export const FollowReadSegmentStatusSchema = z.enum(['good', 'ok', 'weak'])
export type FollowReadSegmentStatus = z.infer<typeof FollowReadSegmentStatusSchema>

export const FollowReadSegmentFeedbackSchema = z.object({
  text: z.string(),
  phonetic: z.string().optional(),
  score: z.number(),
  status: FollowReadSegmentStatusSchema,
  comment: z.string().optional(),
})
export type FollowReadSegmentFeedback = z.infer<typeof FollowReadSegmentFeedbackSchema>

export const FollowReadPhonemeFeedbackSchema = z.object({
  expectedPhoneme: z.string(),
  score: z.number(),
  status: FollowReadSegmentStatusSchema,
  candidatePhonemes: z.array(z.object({
    phoneme: z.string(),
    confidence: z.number(),
  })).optional().default([]),
  offsetMs: z.number().optional(),
  durationMs: z.number().optional(),
})
export type FollowReadPhonemeFeedback = z.infer<typeof FollowReadPhonemeFeedbackSchema>

export const FollowReadPronunciationResponseSchema = z.object({
  word: z.string(),
  score: z.number(),
  band: FollowReadScoreBandSchema,
  passed: z.boolean(),
  transcript: z.string().optional(),
  feedback: z.object({
    summary: z.string(),
    stress: z.string(),
    vowel: z.string(),
    consonant: z.string(),
    ending: z.string(),
    rhythm: z.string(),
  }),
  weakSegments: z.array(z.string()).optional(),
  segmentFeedback: z.array(FollowReadSegmentFeedbackSchema).optional().default([]),
  phonemeFeedback: z.array(FollowReadPhonemeFeedbackSchema).optional().default([]),
  dimensions: z.object({
    phonemeAccuracy: z.number(),
    completeness: z.number(),
    fluency: z.number(),
    prosody: z.number().optional(),
  }).optional(),
  provider: z.string().optional(),
  scoringProvider: z.string().optional(),
  assessmentVersion: z.string().optional(),
  explanationToken: z.string().optional(),
  model: z.string().optional(),
  confidence: z.string().optional(),
})

export type FollowReadPronunciationResponse = z.infer<typeof FollowReadPronunciationResponseSchema>

interface EvaluateFollowReadPronunciationInput {
  word: string
  phonetic?: string | null
  bookId?: string | null
  chapterId?: string | null
  durationSeconds?: number | null
  segments?: Array<{ text: string; phonetic?: string | null }>
  audio: Blob
  referenceAudio?: Blob | null
}

function appendOptional(formData: FormData, key: string, value?: string | number | null) {
  if (value == null || value === '') return
  formData.append(key, String(value))
}

export async function evaluateFollowReadPronunciation(
  input: EvaluateFollowReadPronunciationInput,
): Promise<FollowReadPronunciationResponse> {
  const formData = new FormData()
  formData.append('audio', input.audio, 'follow-read-user.webm')
  if (input.referenceAudio) {
    formData.append('referenceAudio', input.referenceAudio, 'follow-read-reference.mp3')
  }
  formData.append('word', input.word)
  appendOptional(formData, 'phonetic', input.phonetic)
  appendOptional(formData, 'bookId', input.bookId)
  appendOptional(formData, 'chapterId', input.chapterId)
  appendOptional(formData, 'durationSeconds', input.durationSeconds)
  const segments = (input.segments || [])
    .map(segment => ({ text: segment.text.trim(), phonetic: segment.phonetic || null }))
    .filter(segment => segment.text)
  if (segments.length) formData.append('segments', JSON.stringify(segments))

  const raw = await apiFetch('/api/ai/follow-read/evaluate', {
    method: 'POST',
    body: formData,
  })
  const parsed = safeParse(FollowReadPronunciationResponseSchema, raw)
  if (!parsed.success) {
    throw new Error('跟读评分响应格式错误')
  }
  return parsed.data
}

export async function explainFollowReadPronunciation(token: string): Promise<string> {
  const payload = await apiFetch<{ summary?: unknown }>('/api/ai/follow-read/explain', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
  return typeof payload.summary === 'string' ? payload.summary.trim() : ''
}
