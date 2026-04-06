import { z } from 'zod'
import { PracticeModeSchema, WordStatusSchema } from './primitives'

export const BookSchema = z.object({
  id: z.string(),
  title: z.string().min(1),
  description: z.string().optional(),
  word_count: z.number().int().nonnegative(),
  chapter_count: z.number().int().nonnegative().optional(),
  group_count: z.number().int().nonnegative().optional(),
  category: z.string().optional(),
  level: z.string().optional(),
  icon: z.string().optional(),
  color: z.string().optional(),
  is_paid: z.boolean().optional(),
  has_chapters: z.boolean().optional(),
  is_auto_favorites: z.boolean().optional(),
  study_type: z.string().optional(),
  file: z.string().optional(),
  practice_mode: z.string().optional(),
})
export type Book = z.infer<typeof BookSchema>

export const ChapterSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string().min(1),
  word_count: z.number().int().nonnegative().optional(),
  group_count: z.number().int().nonnegative().optional(),
  is_custom: z.boolean().optional(),
})
export type Chapter = z.infer<typeof ChapterSchema>

export const BookProgressSchema = z.object({
  book_id: z.union([z.string(), z.number()]),
  current_index: z.number().int().nonnegative(),
  correct_count: z.number().int().nonnegative().optional(),
  wrong_count: z.number().int().nonnegative().optional(),
  is_completed: z.boolean().optional(),
  updatedAt: z.string().optional(),
})
export type BookProgress = z.infer<typeof BookProgressSchema>

export const ProgressMapSchema = z.record(z.string(), BookProgressSchema)
export type ProgressMap = z.infer<typeof ProgressMapSchema>

export const ListeningConfusableCandidateSchema = z.object({
  word: z.string().min(1),
  phonetic: z.string(),
  pos: z.string(),
  definition: z.string().min(1),
  group_key: z.string().optional(),
})
export type ListeningConfusableCandidate = z.infer<typeof ListeningConfusableCandidateSchema>

export const WordSchema = z.object({
  word: z.string().min(1),
  phonetic: z.string(),
  pos: z.string(),
  definition: z.string().min(1),
  group_key: z.string().optional(),
  listening_confusables: z.array(ListeningConfusableCandidateSchema).optional(),
  chapter_id: z.union([z.string(), z.number()]).optional(),
  chapter_title: z.string().optional(),
  examples: z.array(z.object({
    en: z.string(),
    zh: z.string(),
  })).optional(),
})
export type Word = z.infer<typeof WordSchema>

export const ProgressDataSchema = z.object({
  current_index: z.number().int().nonnegative(),
  correct_count: z.number().int().nonnegative().optional(),
  wrong_count: z.number().int().nonnegative().optional(),
  is_completed: z.boolean().optional(),
  words_learned: z.number().int().nonnegative().optional(),
  answered_words: z.array(z.string()).optional(),
  updatedAt: z.string().datetime().optional(),
})
export type ProgressData = z.infer<typeof ProgressDataSchema>

export const ChapterProgressMapSchema = z.record(z.string(), z.object({
  current_index: z.number().optional(),
  correct_count: z.number().optional(),
  wrong_count: z.number().optional(),
  is_completed: z.boolean().optional(),
  words_learned: z.number().optional(),
  updatedAt: z.string().optional(),
}).passthrough())
export type ChapterProgressMap = z.infer<typeof ChapterProgressMapSchema>

export const OptionItemSchema = z.object({
  definition: z.string().min(1),
  pos: z.string(),
  word: z.string().min(1).optional(),
  phonetic: z.string().optional(),
  display_mode: z.enum(['definition', 'word']).optional(),
})
export type OptionItem = z.infer<typeof OptionItemSchema>

export const LastStateSchema = z.object({
  qi: z.number().int().nonnegative(),
  cc: z.number().int().nonnegative(),
  wc: z.number().int().nonnegative(),
  prevWord: WordSchema.nullable(),
})
export type LastState = z.infer<typeof LastStateSchema>

export const WordStatusesSchema = z.record(z.string(), WordStatusSchema)
export type WordStatuses = z.infer<typeof WordStatusesSchema>

const FontSizeSchema = z.union([
  z.literal('small'),
  z.literal('medium'),
  z.literal('large'),
])

export const AppSettingsSchema = z.object({
  shuffle: z.boolean().optional(),
  repeatWrong: z.boolean().optional(),
  playbackSpeed: z.string().optional(),
  volume: z.string().optional(),
  interval: z.string().optional(),
  reviewInterval: z.string().optional(),
  reviewLimit: z.string().optional(),
  reviewLimitCustomized: z.boolean().optional(),
  darkMode: z.boolean().optional(),
  fontSize: FontSizeSchema.optional(),
})
export type AppSettings = z.infer<typeof AppSettingsSchema>

export const GeneratedChapterWordSchema = z.object({
  chapterId: z.string(),
  word: z.string(),
  phonetic: z.string(),
  pos: z.string(),
  definition: z.string(),
})

export const GeneratedBookSchema = z.object({
  bookId: z.string(),
  title: z.string().min(1),
  description: z.string(),
  chapters: z.array(
    z.object({ id: z.string(), title: z.string(), wordCount: z.number().int().nonnegative() }),
  ),
  words: z.array(GeneratedChapterWordSchema),
})
export type GeneratedBook = z.infer<typeof GeneratedBookSchema>

export const PracticeSessionContextSchema = z.object({
  currentWord: z.string().optional(),
  currentPhonetic: z.string().optional(),
  currentPos: z.string().optional(),
  currentDefinition: z.string().optional(),
  currentBook: z.string().optional(),
  currentChapter: z.string().optional(),
  currentChapterTitle: z.string().optional(),
  practiceMode: PracticeModeSchema.optional(),
  mode: z.string().optional(),
  sessionCompleted: z.boolean().optional(),
  sessionProgress: z.number().optional(),
  sessionAccuracy: z.number().optional(),
  wordsCompleted: z.number().int().nonnegative().optional(),
  totalWords: z.number().int().nonnegative().optional(),
  currentFocusDimension: z.string().optional(),
  weakestDimension: z.string().optional(),
  weakDimensionOrder: z.array(z.string()).optional(),
  weakFocusWords: z.array(z.string()).optional(),
  recentWrongWords: z.array(z.string()).optional(),
  trapStrategy: z.string().optional(),
  priorityDistractorWords: z.array(z.string()).optional(),
}).passthrough()
