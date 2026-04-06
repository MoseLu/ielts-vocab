import { z } from 'zod'

import { PracticeModeSchema } from './core'

const QuickMemorySummarySchema = z.object({
  known: z.number().int().nonnegative().optional(),
  unknown: z.number().int().nonnegative().optional(),
  dueToday: z.number().int().nonnegative().optional(),
}).passthrough()

const ModePerformanceEntrySchema = z.object({
  correct: z.number().int().nonnegative().optional(),
  wrong: z.number().int().nonnegative().optional(),
}).passthrough()

const LocalHistorySchema = z.object({
  chaptersCompleted: z.number().int().nonnegative().optional(),
  chaptersAttempted: z.number().int().nonnegative().optional(),
  totalCorrect: z.number().int().nonnegative().optional(),
  totalWrong: z.number().int().nonnegative().optional(),
  overallAccuracy: z.number().optional(),
}).passthrough()

const LocalBookProgressEntrySchema = z.object({
  chaptersCompleted: z.number().int().nonnegative().optional(),
  chaptersAttempted: z.number().int().nonnegative().optional(),
  correct: z.number().int().nonnegative().optional(),
  wrong: z.number().int().nonnegative().optional(),
  wordsLearned: z.number().int().nonnegative().optional(),
}).passthrough()

export const LearningContextSchema = z.object({
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
  quickMemorySummary: QuickMemorySummarySchema.optional(),
  modePerformance: z.record(z.string(), ModePerformanceEntrySchema).optional(),
  localHistory: LocalHistorySchema.optional(),
  localBookProgress: z.record(z.string(), LocalBookProgressEntrySchema).optional(),
}).passthrough()
export type LearningContext = z.infer<typeof LearningContextSchema>

const GeneratedChapterWordSchema = z.object({
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
