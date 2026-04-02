// ── Zod Schemas ────────────────────────────────────────────────────────────────
// Runtime validation for all data shapes in the app
// Each schema produces a TypeScript type (via z.infer) aligned with the
// domain interfaces in ../types/index.ts

import { z } from 'zod'

// ── Primitives ────────────────────────────────────────────────────────────────

/** Matches supported practice routes and analytics modes */
export const PracticeModeSchema = z.enum([
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
  answered_words: z.array(z.string()).optional(),
  updatedAt: z.string().datetime().optional(),
})
export type ProgressData = z.infer<typeof ProgressDataSchema>

// Map of chapter key (e.g. "bookId_chapterId") to progress data
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
  reviewInterval: z.string().optional(),
  reviewLimit: z.string().optional(),
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

export const LearnerProfileSummarySchema = z.object({
  date: z.string(),
  today_words: z.number().int(),
  today_accuracy: z.number(),
  today_duration_seconds: z.number().int(),
  today_sessions: z.number().int(),
  streak_days: z.number().int(),
  weakest_mode: z.string().nullable(),
  weakest_mode_label: z.string().nullable(),
  weakest_mode_accuracy: z.number().nullable(),
  due_reviews: z.number().int(),
  trend_direction: z.enum(['improving', 'stable', 'declining', 'new']),
})
export type LearnerProfileSummary = z.infer<typeof LearnerProfileSummarySchema>

export const LearnerProfileDimensionSchema = z.object({
  dimension: z.string(),
  label: z.string(),
  correct: z.number().int(),
  wrong: z.number().int(),
  attempts: z.number().int(),
  accuracy: z.number().nullable(),
  weakness: z.number(),
})
export type LearnerProfileDimension = z.infer<typeof LearnerProfileDimensionSchema>

export const LearnerProfileFocusWordSchema = z.object({
  word: z.string(),
  definition: z.string(),
  wrong_count: z.number().int(),
  dominant_dimension: z.string(),
  dominant_dimension_label: z.string(),
  dominant_wrong: z.number().int(),
  focus_score: z.number(),
})
export type LearnerProfileFocusWord = z.infer<typeof LearnerProfileFocusWordSchema>

export const LearnerProfileTopicSchema = z.object({
  title: z.string(),
  count: z.number().int(),
  word_context: z.string(),
  latest_answer: z.string(),
  latest_at: z.string().nullable(),
})
export type LearnerProfileTopic = z.infer<typeof LearnerProfileTopicSchema>

export const LearnerProfileModeSchema = z.object({
  mode: z.string(),
  label: z.string(),
  correct: z.number().int(),
  wrong: z.number().int(),
  words: z.number().int(),
  sessions: z.number().int(),
  attempts: z.number().int(),
  accuracy: z.number().nullable(),
})
export type LearnerProfileMode = z.infer<typeof LearnerProfileModeSchema>

export const LearnerProfileActivitySummarySchema = z.object({
  total_events: z.number().int(),
  study_sessions: z.number().int(),
  quick_memory_reviews: z.number().int(),
  listening_reviews: z.number().int().default(0),
  writing_reviews: z.number().int().default(0),
  wrong_word_records: z.number().int(),
  assistant_questions: z.number().int(),
  assistant_tool_uses: z.number().int().default(0),
  pronunciation_checks: z.number().int().default(0),
  speaking_simulations: z.number().int().default(0),
  chapter_updates: z.number().int(),
  books_touched: z.number().int(),
  chapters_touched: z.number().int(),
  words_touched: z.number().int(),
  total_duration_seconds: z.number().int(),
  correct_count: z.number().int(),
  wrong_count: z.number().int(),
})
export type LearnerProfileActivitySummary = z.infer<typeof LearnerProfileActivitySummarySchema>

export const LearnerProfileActivitySourceSchema = z.object({
  source: z.string(),
  label: z.string(),
  count: z.number().int(),
})
export type LearnerProfileActivitySource = z.infer<typeof LearnerProfileActivitySourceSchema>

export const LearnerProfileActivityBreakdownSchema = z.object({
  event_type: z.string(),
  label: z.string(),
  count: z.number().int(),
})
export type LearnerProfileActivityBreakdown = z.infer<typeof LearnerProfileActivityBreakdownSchema>

export const LearnerProfileActivityEventSchema = z.object({
  id: z.number().int(),
  event_type: z.string(),
  label: z.string(),
  source: z.string(),
  source_label: z.string(),
  mode: z.string().nullable(),
  mode_label: z.string(),
  book_id: z.string().nullable(),
  chapter_id: z.string().nullable(),
  word: z.string().nullable(),
  item_count: z.number().int(),
  correct_count: z.number().int(),
  wrong_count: z.number().int(),
  duration_seconds: z.number().int(),
  occurred_at: z.string().nullable(),
  title: z.string(),
  payload: z.record(z.string(), z.unknown()),
})
export type LearnerProfileActivityEvent = z.infer<typeof LearnerProfileActivityEventSchema>

export const LearnerProfileMemorySystemSchema = z.object({}).passthrough().default({})
export type LearnerProfileMemorySystem = z.infer<typeof LearnerProfileMemorySystemSchema>

export const LearnerProfileSchema = z.object({
  date: z.string(),
  summary: LearnerProfileSummarySchema,
  dimensions: z.array(LearnerProfileDimensionSchema),
  focus_words: z.array(LearnerProfileFocusWordSchema),
  memory_system: LearnerProfileMemorySystemSchema.optional().default({}),
  repeated_topics: z.array(LearnerProfileTopicSchema),
  next_actions: z.array(z.string()),
  mode_breakdown: z.array(LearnerProfileModeSchema),
  activity_summary: LearnerProfileActivitySummarySchema,
  activity_source_breakdown: z.array(LearnerProfileActivitySourceSchema),
  activity_event_breakdown: z.array(LearnerProfileActivityBreakdownSchema).optional().default([]),
  recent_activity: z.array(LearnerProfileActivityEventSchema),
})
export type LearnerProfile = z.infer<typeof LearnerProfileSchema>

// ── Learning Journal ──────────────────────────────────────────────────────────

export const LearningNoteSchema = z.object({
  id: z.number().int(),
  question: z.string(),
  answer: z.string(),
  word_context: z.string().nullable().optional(),
  created_at: z.string(),
})
export type LearningNote = z.infer<typeof LearningNoteSchema>

export const NoteMemoryTopicRelatedNoteSchema = z.object({
  id: z.number().int(),
  question: z.string(),
  answer: z.string(),
  word_context: z.string().nullable().optional(),
  created_at: z.string().nullable(),
})
export type NoteMemoryTopicRelatedNote = z.infer<typeof NoteMemoryTopicRelatedNoteSchema>

export const NoteMemoryTopicSchema = z.object({
  key: z.string(),
  title: z.string(),
  count: z.number().int(),
  word_context: z.string(),
  latest_answer: z.string(),
  latest_at: z.string().nullable(),
  note_ids: z.array(z.number().int()),
  related_notes: z.array(NoteMemoryTopicRelatedNoteSchema),
  follow_up_hint: z.string().nullable().optional(),
  is_repeated: z.boolean().optional(),
})
export type NoteMemoryTopic = z.infer<typeof NoteMemoryTopicSchema>

export const DailySummarySchema = z.object({
  id: z.number().int(),
  date: z.string(),
  content: z.string(),
  generated_at: z.string(),
})
export type DailySummary = z.infer<typeof DailySummarySchema>

export const NotesListResponseSchema = z.object({
  notes: z.array(LearningNoteSchema),
  memory_topics: z.array(NoteMemoryTopicSchema).optional(),
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

export const SummaryGenerationStatusSchema = z.enum(['queued', 'running', 'completed', 'failed'])
export type SummaryGenerationStatus = z.infer<typeof SummaryGenerationStatusSchema>

export const SummaryGenerationJobSchema = z.object({
  job_id: z.string().min(1),
  date: z.string(),
  status: SummaryGenerationStatusSchema,
  progress: z.number().int().min(0).max(100),
  message: z.string(),
  estimated_chars: z.number().int().min(0),
  generated_chars: z.number().int().min(0),
  summary: DailySummarySchema.nullable().optional(),
  error: z.string().nullable().optional(),
})
export type SummaryGenerationJob = z.infer<typeof SummaryGenerationJobSchema>

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
