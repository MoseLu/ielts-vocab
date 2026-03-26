// ── Zod Schemas ────────────────────────────────────────────────────────────────
// Runtime validation for all data shapes in the app
// Each schema produces a TypeScript type (via z.infer) aligned with the
// domain interfaces in ../types/index.ts

import { z } from 'zod'

// ── Primitives ────────────────────────────────────────────────────────────────

/** Matches 'smart' | 'listening' | 'meaning' | 'dictation' | 'radio' */
export const PracticeModeSchema = z.enum(['smart', 'listening', 'meaning', 'dictation', 'radio'])
export type PracticeMode = z.infer<typeof PracticeModeSchema>

export const ToastTypeSchema = z.enum(['info', 'success', 'error'])
export type ToastType = z.infer<typeof ToastTypeSchema>

export const WordStatusSchema = z.enum(['correct', 'wrong'])
export type WordStatus = z.infer<typeof WordStatusSchema>

export const AIMessageRoleSchema = z.enum(['user', 'assistant'])
export type AIMessageRole = z.infer<typeof AIMessageRoleSchema>

// ── Auth / User ─────────────────────────────────────────────────────────────

export const UserSchema = z.object({
  id: z.union([z.string(), z.number()]),
  email: z.string().email().or(z.literal('')).optional(),
  username: z.string().optional(),
  avatar_url: z.string().nullable().optional(),
  is_admin: z.boolean().optional(),
  created_at: z.string().optional(),
})
export type User = z.infer<typeof UserSchema>

/** Email OR username + password login */
export const LoginSchema = z.object({
  identifier: z.string().min(1, '请输入邮箱或用户名'),
  password: z.string().min(6, '密码至少6个字符'),
})

/** Registration form */
export const RegisterSchema = z.object({
  username: z
    .string()
    .min(3, '用户名至少3个字符')
    .max(30, '用户名最多30个字符')
    .regex(/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, '用户名只能包含字母、数字、下划线和中文'),
  email: z.string().email('请输入有效的邮箱地址').optional().or(z.literal('')),
  password: z.string().min(6, '密码至少6个字符'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
})

/** Forgot password — step 1: enter email */
export const ForgotPasswordEmailSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
})

/** Forgot password — step 2: enter code + new password */
export const ResetPasswordSchema = z.object({
  code: z.string().length(6, '请输入6位验证码'),
  password: z.string().min(6, '密码至少6个字符'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
})

/** Bind email in profile */
export const BindEmailSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
  code: z.string().length(6, '请输入6位验证码'),
})

// ── Book / Chapter / Progress ───────────────────────────────────────────────

export const BookSchema = z.object({
  id: z.string(),
  title: z.string().min(1),
  description: z.string().optional(),
  word_count: z.number().int().nonnegative(),
  category: z.string().optional(),
  level: z.string().optional(),
  icon: z.string().optional(),
  color: z.string().optional(),
  is_paid: z.boolean().optional(),
  has_chapters: z.boolean().optional(),
  study_type: z.string().optional(),
  file: z.string().optional(),
})
export type Book = z.infer<typeof BookSchema>

export const ChapterSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string().min(1),
  word_count: z.number().int().nonnegative().optional(),
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

/** Record<bookId, BookProgress> */
export const ProgressMapSchema = z.record(z.string(), BookProgressSchema)
export type ProgressMap = z.infer<typeof ProgressMapSchema>

// ── Practice ────────────────────────────────────────────────────────────────

export const WordSchema = z.object({
  word: z.string().min(1),
  phonetic: z.string(),
  pos: z.string(),
  definition: z.string().min(1),
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
  updatedAt: z.string().datetime().optional(),
})
export type ProgressData = z.infer<typeof ProgressDataSchema>

export const OptionItemSchema = z.object({
  definition: z.string().min(1),
  pos: z.string(),
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

// ── App Settings ────────────────────────────────────────────────────────────

const fontSizeValues = z.union([
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
  darkMode: z.boolean().optional(),
  fontSize: fontSizeValues.optional(),
})
export type AppSettings = z.infer<typeof AppSettingsSchema>

// ── AI Chat ────────────────────────────────────────────────────────────────

export const AIMessageSchema = z.object({
  id: z.string(),
  role: AIMessageRoleSchema,
  content: z.string(),
  options: z.array(z.string()).optional(),
  timestamp: z.number().int().nonnegative(),
})
export type AIMessage = z.infer<typeof AIMessageSchema>

export const LearningContextSchema = z.object({
  currentWord: z.string().optional(),
  currentPhonetic: z.string().optional(),
  currentPos: z.string().optional(),
  currentDefinition: z.string().optional(),
  currentBook: z.string().optional(),
  currentChapter: z.string().optional(),
  practiceMode: PracticeModeSchema.optional(),
  mode: z.string().optional(),
  sessionProgress: z.number().optional(),
  sessionAccuracy: z.number().optional(),
  wordsCompleted: z.number().int().nonnegative().optional(),
  totalWords: z.number().int().nonnegative().optional(),
})
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
    z.object({ id: z.string(), title: z.string(), wordCount: z.number().int().nonnegative() })
  ),
  words: z.array(GeneratedChapterWordSchema),
})
export type GeneratedBook = z.infer<typeof GeneratedBookSchema>

// ── API Responses ────────────────────────────────────────────────────────────

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

export const AIAskResponseSchema = z.object({
  reply: z.string(),
  options: z.array(z.string()).nullable().optional(),
})

// ── Learning Journal ──────────────────────────────────────────────────────────

export const LearningNoteSchema = z.object({
  id: z.number().int(),
  question: z.string(),
  answer: z.string(),
  word_context: z.string().nullable().optional(),
  created_at: z.string(),
})
export type LearningNote = z.infer<typeof LearningNoteSchema>

export const DailySummarySchema = z.object({
  id: z.number().int(),
  date: z.string(),
  content: z.string(),
  generated_at: z.string(),
})
export type DailySummary = z.infer<typeof DailySummarySchema>

export const NotesListResponseSchema = z.object({
  notes: z.array(LearningNoteSchema),
  total: z.number().int(),
  per_page: z.number().int(),
  next_cursor: z.number().int().nullable().optional(),
  has_more: z.boolean(),
})

export const SummariesListResponseSchema = z.object({
  summaries: z.array(DailySummarySchema),
})

export const GenerateSummaryResponseSchema = z.object({
  summary: DailySummarySchema,
})

export const ExportResponseSchema = z.object({
  content: z.string(),
  filename: z.string(),
  format: z.string(),
})

// ── Form / UI ──────────────────────────────────────────────────────────────

export const ToastDataSchema = z.object({
  message: z.string().min(1),
  type: ToastTypeSchema,
})
export type ToastData = z.infer<typeof ToastDataSchema>

export const BreadcrumbItemSchema = z.object({
  label: z.string().min(1),
  href: z.string().optional(),
})
export type BreadcrumbItem = z.infer<typeof BreadcrumbItemSchema>
