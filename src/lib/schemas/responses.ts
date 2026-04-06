import { z } from 'zod'
import { UserSchema } from './auth'
import { ChapterSchema, BookProgressSchema, BookSchema, ProgressMapSchema, WordSchema } from './vocabulary'

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

export const ProgressResponseSchema = z.object({
  progress: z.union([BookProgressSchema, ProgressMapSchema]),
})

export const ChaptersListResponseSchema = z.object({
  chapters: z.array(ChapterSchema),
})
