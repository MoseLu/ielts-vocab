import { z } from 'zod'

export const PracticeModeSchema = z.enum([
  'game',
  'smart',
  'listening',
  'meaning',
  'dictation',
  'radio',
  'quickmemory',
  'errors',
])
export type PracticeMode = z.infer<typeof PracticeModeSchema>

export const ToastTypeSchema = z.enum(['info', 'success', 'error'])
export type ToastType = z.infer<typeof ToastTypeSchema>

export const WordStatusSchema = z.enum(['correct', 'wrong'])
export type WordStatus = z.infer<typeof WordStatusSchema>

export const AIMessageRoleSchema = z.enum(['user', 'assistant'])
export type AIMessageRole = z.infer<typeof AIMessageRoleSchema>

export const UserSchema = z.object({
  id: z.union([z.string(), z.number()]),
  email: z.string().email().or(z.literal('')).optional(),
  username: z.string().optional(),
  avatar_url: z.string().nullable().optional(),
  is_admin: z.boolean().optional(),
  created_at: z.string().optional(),
})
export type User = z.infer<typeof UserSchema>

export const LoginSchema = z.object({
  identifier: z.string().min(1, '请输入邮箱或用户名'),
  password: z.string().min(6, '密码至少6个字符'),
})

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

export const ForgotPasswordEmailSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
})

export const ResetPasswordSchema = z.object({
  code: z.string().length(6, '请输入6位验证码'),
  password: z.string().min(6, '密码至少6个字符'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
})

export const BindEmailSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
  code: z.string().length(6, '请输入6位验证码'),
})

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
  is_custom_book: z.boolean().optional(),
  education_stage: z.string().optional().nullable(),
  exam_type: z.string().optional().nullable(),
  ielts_skill: z.string().optional().nullable(),
  share_enabled: z.boolean().optional(),
  chapter_word_target: z.number().int().positive().optional(),
  incomplete_word_count: z.number().int().nonnegative().optional(),
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
  is_incomplete: z.boolean().optional(),
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
  reviewInterval: z.string().optional(),
  reviewLimit: z.string().optional(),
  reviewLimitCustomized: z.boolean().optional(),
  darkMode: z.boolean().optional(),
  fontSize: fontSizeValues.optional(),
})
export type AppSettings = z.infer<typeof AppSettingsSchema>

export const AIMessageSchema = z.object({
  id: z.string(),
  role: AIMessageRoleSchema,
  content: z.string(),
  options: z.array(z.string()).optional(),
  timestamp: z.number().int().nonnegative(),
})
export type AIMessage = z.infer<typeof AIMessageSchema>

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
