import { z } from 'zod'

export const UserSchema = z.object({
  id: z.union([z.string(), z.number()]),
  username: z.string(),
  email: z.string().optional().nullable().transform(value => value ?? ''),
  avatar_url: z.string().optional().nullable(),
  is_admin: z.boolean().optional().default(false),
  created_at: z.string().optional().nullable(),
})

export const MobileAuthSessionSchema = z.object({
  access_token: z.string().min(1),
  refresh_token: z.string().min(1),
  token_type: z.literal('Bearer').default('Bearer'),
  access_expires_in: z.number().int().positive(),
  refresh_expires_in: z.number().int().positive().optional(),
  user: UserSchema,
})

export const BookSummarySchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string(),
  description: z.string().optional().nullable(),
  category: z.string().optional().nullable(),
  level: z.string().optional().nullable(),
  total_words: z.number().optional().default(0),
})

export const LearningStatsSchema = z.object({
  total_words: z.number().optional().default(0),
  learned_words: z.number().optional().default(0),
  wrong_words: z.number().optional().default(0),
  streak_days: z.number().optional().default(0),
})

export type AppUser = z.infer<typeof UserSchema>
export type MobileAuthSession = z.infer<typeof MobileAuthSessionSchema>
export type BookSummary = z.infer<typeof BookSummarySchema>
export type LearningStats = z.infer<typeof LearningStatsSchema>
