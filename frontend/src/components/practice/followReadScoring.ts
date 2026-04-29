import { z } from 'zod'
import { apiFetch, safeParse } from '../../lib'

export const FollowReadScoreBandSchema = z.enum(['needs_work', 'near_pass', 'pass'])
export type FollowReadScoreBand = z.infer<typeof FollowReadScoreBandSchema>

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
  provider: z.string().optional(),
  model: z.string().optional(),
})

export type FollowReadPronunciationResponse = z.infer<typeof FollowReadPronunciationResponseSchema>

interface EvaluateFollowReadPronunciationInput {
  word: string
  phonetic?: string | null
  bookId?: string | null
  chapterId?: string | null
  durationSeconds?: number | null
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
