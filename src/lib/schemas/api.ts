import { z } from 'zod'

import {
  BookProgressSchema,
  BookSchema,
  ChapterSchema,
  ProgressMapSchema,
  UserSchema,
  WordSchema,
} from './core'

export const ApiErrorSchema = z.object({
  error: z.string(),
})

export const AuthResponseSchema = z.object({
  user: UserSchema,
  token: z.string(),
  message: z.string().optional(),
})

export const BooksListResponseSchema = z.object({
  books: z.array(BookSchema),
})

export const WordsListResponseSchema = z.object({
  words: z.array(WordSchema),
  total: z.number().int().nonnegative(),
})

const WordSearchExampleSchema = z.object({
  en: z.string().catch(''),
  zh: z.string().catch(''),
})

const WordSearchConfusableSchema = z.object({
  word: z.string().min(1),
  phonetic: z.string().catch(''),
  pos: z.string().catch(''),
  definition: z.string().catch(''),
  group_key: z.string().optional(),
})

export const WordSearchResultSchema = WordSchema.extend({
  phonetic: z.string().catch(''),
  pos: z.string().catch(''),
  definition: z.string().catch(''),
  listening_confusables: z.array(WordSearchConfusableSchema).optional(),
  examples: z.array(WordSearchExampleSchema).optional(),
  book_id: z.string(),
  book_title: z.string(),
  match_type: z.enum(['exact', 'prefix', 'contains', 'definition', 'example']),
})
export type WordSearchResult = z.infer<typeof WordSearchResultSchema>

export const WordSearchResponseSchema = z.object({
  query: z.string(),
  total: z.number().int().nonnegative(),
  results: z.array(WordSearchResultSchema),
})
export type WordSearchResponse = z.infer<typeof WordSearchResponseSchema>

export const WordRootSegmentSchema = z.object({
  kind: z.enum(['前缀', '词根', '后缀']),
  text: z.string(),
  meaning: z.string(),
})
export type WordRootSegment = z.infer<typeof WordRootSegmentSchema>

export const WordRootDetailSchema = z.object({
  word: z.string(),
  normalized_word: z.string(),
  segments: z.array(WordRootSegmentSchema),
  summary: z.string(),
  source: z.string().optional(),
  updated_at: z.string().nullable().optional(),
})
export type WordRootDetail = z.infer<typeof WordRootDetailSchema>

export const WordEnglishMeaningEntrySchema = z.object({
  pos: z.string().catch(''),
  definition: z.string().catch(''),
})
export type WordEnglishMeaningEntry = z.infer<typeof WordEnglishMeaningEntrySchema>

export const WordEnglishDetailSchema = z.object({
  word: z.string(),
  normalized_word: z.string(),
  entries: z.array(WordEnglishMeaningEntrySchema),
  source: z.string().optional(),
  updated_at: z.string().nullable().optional(),
})
export type WordEnglishDetail = z.infer<typeof WordEnglishDetailSchema>

export const WordDerivativeDetailSchema = z.object({
  word: z.string(),
  phonetic: z.string(),
  pos: z.string(),
  definition: z.string(),
  relation_type: z.string().optional(),
  source: z.string().optional(),
  sort_order: z.number().int().optional(),
})
export type WordDerivativeDetail = z.infer<typeof WordDerivativeDetailSchema>

export const WordDetailExampleSchema = z.object({
  en: z.string().catch(''),
  zh: z.string().catch(''),
  source: z.string().optional(),
  sort_order: z.number().int().optional(),
})
export type WordDetailExample = z.infer<typeof WordDetailExampleSchema>

export const WordDetailBookRefSchema = z.object({
  book_id: z.string(),
  book_title: z.string().catch(''),
  chapter_id: z.string().catch(''),
  chapter_title: z.string().catch(''),
})
export type WordDetailBookRef = z.infer<typeof WordDetailBookRefSchema>

export const WordDetailNoteSchema = z.object({
  word: z.string(),
  content: z.string(),
  updated_at: z.string().nullable().optional(),
})
export type WordDetailNote = z.infer<typeof WordDetailNoteSchema>

export const WordDetailResponseSchema = z.object({
  word: z.string(),
  phonetic: z.string().catch(''),
  pos: z.string().catch(''),
  definition: z.string().catch(''),
  root: WordRootDetailSchema,
  english: WordEnglishDetailSchema,
  examples: z.array(WordDetailExampleSchema),
  derivatives: z.array(WordDerivativeDetailSchema),
  books: z.array(WordDetailBookRefSchema).optional(),
  note: WordDetailNoteSchema,
})
export type WordDetailResponse = z.infer<typeof WordDetailResponseSchema>

export const SaveWordDetailNoteResponseSchema = z.object({
  note: WordDetailNoteSchema,
})
export type SaveWordDetailNoteResponse = z.infer<typeof SaveWordDetailNoteResponseSchema>

export const ProgressResponseSchema = z.object({
  progress: z.union([BookProgressSchema, ProgressMapSchema]),
})

export const ChaptersListResponseSchema = z.object({
  chapters: z.array(ChapterSchema),
})

export const AIAskResponseSchema = z.object({
  reply: z.string(),
  options: z.array(z.string()).nullable().optional(),
})

export const AIPronunciationCheckResponseSchema = z.object({
  word: z.string(),
  score: z.number(),
  passed: z.boolean(),
  stress_feedback: z.string(),
  vowel_feedback: z.string(),
  speed_feedback: z.string(),
})
export type AIPronunciationCheckResponse = z.infer<typeof AIPronunciationCheckResponseSchema>

export const AISpeakingSimulationResponseSchema = z.object({
  part: z.number().int(),
  topic: z.string(),
  question: z.string(),
  follow_ups: z.array(z.string()),
})
export type AISpeakingSimulationResponse = z.infer<typeof AISpeakingSimulationResponseSchema>

export const AIReviewPlanResponseSchema = z.object({
  level: z.string(),
  mastery_rule: z.string().optional(),
  priority_dimension: z.string().optional(),
  priority_reason: z.string().optional(),
  plan: z.array(z.string()),
  dimensions: z.array(z.object({
    key: z.string().optional(),
    label: z.string().optional(),
    status: z.string().optional(),
    status_label: z.string().optional(),
    schedule_label: z.string().optional(),
    next_action: z.string().optional(),
  })).optional(),
})
export type AIReviewPlanResponse = z.infer<typeof AIReviewPlanResponseSchema>
