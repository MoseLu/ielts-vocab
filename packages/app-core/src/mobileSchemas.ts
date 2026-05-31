import { z } from 'zod'

const OptionalStringSchema = z.string().nullable().optional().transform(value => value ?? '')
const IdSchema = z.union([z.string(), z.number()])

export const PRACTICE_MODES = [
  'smart',
  'quickmemory',
  'test',
  'listening',
  'meaning',
  'dictation',
  'follow',
  'radio',
  'errors',
] as const

export const PracticeModeSchema = z.enum(PRACTICE_MODES)
export type PracticeMode = z.infer<typeof PracticeModeSchema>

export const MobileWordSchema = z.object({
  word: z.string(),
  definition: OptionalStringSchema,
  phonetic: OptionalStringSchema,
  pos: OptionalStringSchema,
  group_key: OptionalStringSchema,
  book_id: OptionalStringSchema,
  book_title: OptionalStringSchema,
  chapter_id: IdSchema.optional().nullable(),
  chapter_title: OptionalStringSchema,
  examples: z.array(z.object({
    en: OptionalStringSchema,
    zh: OptionalStringSchema,
  })).default([]),
  listening_confusables: z.array(z.object({
    word: z.string(),
    definition: OptionalStringSchema,
    phonetic: OptionalStringSchema,
    pos: OptionalStringSchema,
  })).default([]),
})
export type MobileWord = z.infer<typeof MobileWordSchema>

export const MobileBookSchema = z.object({
  id: IdSchema,
  title: z.string(),
  description: OptionalStringSchema,
  category: OptionalStringSchema,
  level: OptionalStringSchema,
  total_words: z.number().optional().default(0),
  word_count: z.number().optional(),
  practice_mode: OptionalStringSchema,
  current_index: z.number().optional().default(0),
  completed_chapters: z.number().optional().default(0),
  total_chapters: z.number().optional().default(0),
  progress_percent: z.number().optional().default(0),
  is_completed: z.boolean().optional().default(false),
  updated_at: OptionalStringSchema,
})
export type MobileBook = z.infer<typeof MobileBookSchema>

export const MobileChapterSchema = z.object({
  id: IdSchema,
  title: z.string(),
  word_count: z.number().optional().default(0),
  group_count: z.number().optional(),
  is_custom: z.boolean().optional().default(false),
  current_index: z.number().optional().default(0),
  words_learned: z.number().optional().default(0),
  correct_count: z.number().optional().default(0),
  wrong_count: z.number().optional().default(0),
  accuracy: z.number().nullable().optional(),
  progress_percent: z.number().optional().default(0),
  is_completed: z.boolean().optional().default(false),
  updated_at: OptionalStringSchema,
})
export type MobileChapter = z.infer<typeof MobileChapterSchema>

export const WrongWordSchema = MobileWordSchema.extend({
  wrong_count: z.number().optional().default(1),
  last_error_at: OptionalStringSchema,
  mistake_type: OptionalStringSchema,
  recognition_pass_streak: z.number().optional().default(0),
  ebbinghaus_streak: z.number().optional().default(0),
  ebbinghaus_remaining: z.number().optional().default(0),
  ebbinghaus_completed: z.boolean().optional().default(false),
})
export type WrongWord = z.infer<typeof WrongWordSchema>

export const LearningStatsPayloadSchema = z.object({
  daily: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  books: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  modes: z.array(z.string()).optional().default([]),
  summary: z.record(z.string(), z.unknown()).optional().default({}),
  alltime: z.record(z.string(), z.unknown()).optional().default({}),
  mode_breakdown: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  pie_chart: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  chapter_breakdown: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  chapter_mode_stats: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  wrong_top10: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  history_wrong_top10: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  pending_wrong_top10: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  wrong_words: z.record(z.string(), z.unknown()).optional().default({}),
  use_fallback: z.boolean().optional().default(false),
})
export type LearningStatsPayload = z.infer<typeof LearningStatsPayloadSchema>

export const HomeTodoActionSchema = z.object({
  book_id: IdSchema.nullable().optional(),
  chapter_id: IdSchema.nullable().optional(),
  cta_label: OptionalStringSchema,
  dimension: OptionalStringSchema,
  kind: OptionalStringSchema,
  mode: OptionalStringSchema,
  task: OptionalStringSchema,
}).optional().default({
  cta_label: '',
  dimension: '',
  kind: '',
  mode: '',
  task: '',
})
export type HomeTodoAction = z.infer<typeof HomeTodoActionSchema>

export const HomeTodoItemSchema = z.object({
  action: HomeTodoActionSchema,
  description: OptionalStringSchema,
  id: OptionalStringSchema,
  title: OptionalStringSchema,
  subtitle: OptionalStringSchema,
  cta_label: OptionalStringSchema,
  target_path: OptionalStringSchema,
  priority: z.number().optional().default(0),
})
export type HomeTodoItem = z.infer<typeof HomeTodoItemSchema>

export const HomeTodoPayloadSchema = z.object({
  date: OptionalStringSchema,
  summary: z.record(z.string(), z.unknown()).optional().default({}),
  primary_items: z.array(HomeTodoItemSchema).optional().default([]),
  overflow_items: z.array(HomeTodoItemSchema).optional().default([]),
})
export type HomeTodoPayload = z.infer<typeof HomeTodoPayloadSchema>

export const JournalSummarySchema = z.object({
  id: IdSchema.optional(),
  date: OptionalStringSchema,
  title: OptionalStringSchema,
  content: OptionalStringSchema,
  markdown: OptionalStringSchema,
  summary: OptionalStringSchema,
  created_at: OptionalStringSchema,
})
export type JournalSummary = z.infer<typeof JournalSummarySchema>

export const LearningNoteSchema = z.object({
  id: IdSchema.optional(),
  question: OptionalStringSchema,
  answer: OptionalStringSchema,
  content: OptionalStringSchema,
  created_at: OptionalStringSchema,
  word: OptionalStringSchema,
})
export type LearningNote = z.infer<typeof LearningNoteSchema>

export const ExamChoiceSchema = z.object({
  id: z.number().optional(),
  key: z.string(),
  label: OptionalStringSchema,
  contentHtml: OptionalStringSchema,
})
export type ExamChoice = z.infer<typeof ExamChoiceSchema>

export const ExamQuestionSchema = z.object({
  id: z.number(),
  questionNumber: z.number().nullable().optional(),
  sortOrder: z.number().optional().default(0),
  questionType: z.string(),
  promptHtml: OptionalStringSchema,
  groupKey: OptionalStringSchema,
  choices: z.array(ExamChoiceSchema).optional().default([]),
  acceptedAnswers: z.array(z.string()).optional().default([]),
  response: z.record(z.string(), z.unknown()).nullable().optional(),
})
export type ExamQuestion = z.infer<typeof ExamQuestionSchema>

export const ExamSectionSchema = z.object({
  id: z.number(),
  sectionType: z.string(),
  title: z.string(),
  instructionsHtml: OptionalStringSchema,
  htmlContent: OptionalStringSchema,
  questions: z.array(ExamQuestionSchema).optional().default([]),
})
export type ExamSection = z.infer<typeof ExamSectionSchema>

export const ExamPaperSummarySchema = z.object({
  id: z.number(),
  collectionTitle: OptionalStringSchema,
  title: z.string(),
  examKind: OptionalStringSchema,
  hasListeningAudio: z.boolean().optional().default(false),
  sections: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  latestAttempt: z.record(z.string(), z.unknown()).nullable().optional(),
})
export type ExamPaperSummary = z.infer<typeof ExamPaperSummarySchema>

export const ExamPaperDetailSchema = z.object({
  id: z.number(),
  collectionTitle: OptionalStringSchema,
  title: z.string(),
  examKind: OptionalStringSchema,
  sections: z.array(ExamSectionSchema).optional().default([]),
})
export type ExamPaperDetail = z.infer<typeof ExamPaperDetailSchema>

export const FeatureWishSchema = z.object({
  id: z.number(),
  title: z.string(),
  description: OptionalStringSchema,
  status: OptionalStringSchema,
  votes: z.number().optional().default(0),
})
export type FeatureWish = z.infer<typeof FeatureWishSchema>

export function parseArray<T>(schema: z.ZodType<T>, values: unknown): T[] {
  if (!Array.isArray(values)) return []
  return values.flatMap(value => {
    const parsed = schema.safeParse(value)
    return parsed.success ? [parsed.data] : []
  })
}
