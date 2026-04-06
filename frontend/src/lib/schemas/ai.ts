import { z } from 'zod'
import { AIMessageRoleSchema } from './primitives'
import { PracticeSessionContextSchema } from './vocabulary'

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

export const LearningContextSchema = PracticeSessionContextSchema.extend({
  quickMemorySummary: QuickMemorySummarySchema.optional(),
  modePerformance: z.record(z.string(), ModePerformanceEntrySchema).optional(),
  localHistory: LocalHistorySchema.optional(),
  localBookProgress: z.record(z.string(), LocalBookProgressEntrySchema).optional(),
})
export type LearningContext = z.infer<typeof LearningContextSchema>

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

export const LearnerProfileDailyPlanActionSchema = z.object({
  kind: z.enum(['add-book', 'due-review', 'error-review', 'continue-book']),
  cta_label: z.string(),
  mode: z.string().nullable().optional().default(null),
  book_id: z.string().nullable().optional().default(null),
  dimension: z.string().nullable().optional().default(null),
})
export type LearnerProfileDailyPlanAction = z.infer<typeof LearnerProfileDailyPlanActionSchema>

export const LearnerProfileDailyPlanTaskSchema = z.object({
  id: z.string(),
  kind: z.enum(['add-book', 'due-review', 'error-review', 'continue-book']),
  title: z.string(),
  description: z.string(),
  status: z.enum(['pending', 'completed']),
  completion_source: z.enum(['completed_today', 'already_clear']).nullable().optional().default(null),
  badge: z.string(),
  action: LearnerProfileDailyPlanActionSchema,
})
export type LearnerProfileDailyPlanTask = z.infer<typeof LearnerProfileDailyPlanTaskSchema>

export const LearnerProfileDailyPlanTodayContentSchema = z.object({
  date: z.string(),
  studied_words: z.number().int(),
  duration_seconds: z.number().int(),
  sessions: z.number().int(),
  latest_activity_title: z.string().nullable(),
  latest_activity_at: z.string().nullable(),
})
export type LearnerProfileDailyPlanTodayContent = z.infer<typeof LearnerProfileDailyPlanTodayContentSchema>

export const LearnerProfileDailyPlanFocusBookSchema = z.object({
  book_id: z.string(),
  title: z.string(),
  current_index: z.number().int(),
  total_words: z.number().int(),
  progress_percent: z.number().int(),
  remaining_words: z.number().int(),
  is_completed: z.boolean(),
}).nullable()
export type LearnerProfileDailyPlanFocusBook = z.infer<typeof LearnerProfileDailyPlanFocusBookSchema>

export const LearnerProfileDailyPlanSchema = z.object({
  tasks: z.array(LearnerProfileDailyPlanTaskSchema),
  today_content: LearnerProfileDailyPlanTodayContentSchema,
  focus_book: LearnerProfileDailyPlanFocusBookSchema,
})
export type LearnerProfileDailyPlan = z.infer<typeof LearnerProfileDailyPlanSchema>

export const LearnerProfileSchema = z.object({
  date: z.string(),
  summary: LearnerProfileSummarySchema,
  dimensions: z.array(LearnerProfileDimensionSchema),
  focus_words: z.array(LearnerProfileFocusWordSchema),
  memory_system: LearnerProfileMemorySystemSchema.optional().default({}),
  daily_plan: LearnerProfileDailyPlanSchema.optional(),
  repeated_topics: z.array(LearnerProfileTopicSchema),
  next_actions: z.array(z.string()),
  mode_breakdown: z.array(LearnerProfileModeSchema),
  activity_summary: LearnerProfileActivitySummarySchema,
  activity_source_breakdown: z.array(LearnerProfileActivitySourceSchema),
  activity_event_breakdown: z.array(LearnerProfileActivityBreakdownSchema).optional().default([]),
  recent_activity: z.array(LearnerProfileActivityEventSchema),
})
export type LearnerProfile = z.infer<typeof LearnerProfileSchema>
