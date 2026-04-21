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
  group_key: z.string().nullable().optional(),
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

export const WordMemoryDetailSchema = z.object({
  badge: z.enum(['谐音', '联想']),
  text: z.string(),
  source: z.string().catch('').optional(),
  updated_at: z.string().nullable().optional(),
})
export type WordMemoryDetail = z.infer<typeof WordMemoryDetailSchema>

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
  memory: WordMemoryDetailSchema.nullable().optional(),
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
  mastery_state: z.object({
    overall_status: z.string(),
    current_round: z.number().int(),
    pending_dimensions: z.array(z.string()),
    dimension_states: z.record(z.string(), z.object({
      status: z.string(),
      pass_streak: z.number().int(),
      attempt_count: z.number().int(),
      history_wrong: z.number().int().optional(),
      last_result: z.string().nullable().optional(),
      next_review_at: z.string().nullable().optional(),
      source_mode: z.string().nullable().optional(),
    })),
  }).optional(),
})
export type AIPronunciationCheckResponse = z.infer<typeof AIPronunciationCheckResponseSchema>

export const GamePracticeDimensionStateSchema = z.object({
  status: z.string(),
  pass_streak: z.number().int(),
  attempt_count: z.number().int(),
  history_wrong: z.number().int().optional(),
  last_result: z.string().nullable().optional(),
  next_review_at: z.string().nullable().optional(),
  source_mode: z.string().nullable().optional(),
})
export type GamePracticeDimensionState = z.infer<typeof GamePracticeDimensionStateSchema>

export const GameCampaignDimensionSchema = z.enum([
  'recognition',
  'meaning',
  'listening',
  'speaking',
  'dictation',
])
export type GameCampaignDimension = z.infer<typeof GameCampaignDimensionSchema>

export const GameNodeTypeSchema = z.enum([
  'word',
  'speaking_boss',
  'speaking_reward',
])
export type GameNodeType = z.infer<typeof GameNodeTypeSchema>

export const GamePracticeWordImageSchema = z.object({
  status: z.enum(['queued', 'generating', 'ready', 'failed']),
  senseKey: z.string().catch(''),
  url: z.string().nullable().optional().default(null),
  alt: z.string().catch('词义配图'),
  styleVersion: z.string().nullable().optional().default(null),
  model: z.string().nullable().optional().default(null),
  generatedAt: z.string().nullable().optional().default(null),
})
export type GamePracticeWordImage = z.infer<typeof GamePracticeWordImageSchema>

export const GameCampaignWordSchema = z.object({
  word: z.string(),
  phonetic: z.string().catch(''),
  pos: z.string().catch(''),
  definition: z.string().catch(''),
  chapter_id: z.union([z.string(), z.number()]).nullable().optional(),
  chapter_title: z.string().nullable().optional(),
  overall_status: z.enum(['new', 'unlocked', 'in_review', 'passed']),
  current_round: z.number().int(),
  pending_dimensions: z.array(z.string()),
  listening_confusables: z.array(WordSearchConfusableSchema).optional(),
  examples: z.array(WordSearchExampleSchema).optional(),
  dimension_states: z.record(z.string(), GamePracticeDimensionStateSchema),
  image: GamePracticeWordImageSchema,
})
export type GameCampaignWord = z.infer<typeof GameCampaignWordSchema>

export const GameCampaignNodeSchema = z.object({
  nodeType: GameNodeTypeSchema,
  nodeKey: z.string(),
  segmentIndex: z.number().int().nonnegative(),
  title: z.string(),
  subtitle: z.string().nullable().optional().default(null),
  status: z.enum(['locked', 'ready', 'pending', 'passed']),
  dimension: GameCampaignDimensionSchema.nullable().optional().default(null),
  promptText: z.string().nullable().optional().default(null),
  targetWords: z.array(z.string()).default([]),
  failedDimensions: z.array(GameCampaignDimensionSchema).default([]),
  bossFailures: z.number().int().nonnegative().optional().default(0),
  rewardFailures: z.number().int().nonnegative().optional().default(0),
  lastEncounterType: GameNodeTypeSchema.nullable().optional().default(null),
  word: GameCampaignWordSchema.nullable().optional().default(null),
})
export type GameCampaignNode = z.infer<typeof GameCampaignNodeSchema>

export const GameCampaignRecoveryItemSchema = z.object({
  nodeKey: z.string(),
  nodeType: GameNodeTypeSchema,
  title: z.string(),
  subtitle: z.string().nullable().optional().default(null),
  failedDimensions: z.array(GameCampaignDimensionSchema).default([]),
  bossFailures: z.number().int().nonnegative().optional().default(0),
  rewardFailures: z.number().int().nonnegative().optional().default(0),
  updatedAt: z.string().nullable().optional().default(null),
})
export type GameCampaignRecoveryItem = z.infer<typeof GameCampaignRecoveryItemSchema>

export const GameCampaignStateSchema = z.object({
  scope: z.object({
    bookId: z.string().nullable().optional(),
    chapterId: z.union([z.string(), z.number()]).nullable().optional(),
    day: z.number().int().nullable().optional(),
  }),
  campaign: z.object({
    title: z.string(),
    scopeLabel: z.string(),
    totalWords: z.number().int(),
    passedWords: z.number().int(),
    totalSegments: z.number().int(),
    clearedSegments: z.number().int(),
    currentSegment: z.number().int(),
  }),
  segment: z.object({
    index: z.number().int(),
    title: z.string(),
    clearedWords: z.number().int(),
    totalWords: z.number().int(),
    bossStatus: z.enum(['locked', 'ready', 'pending', 'passed']),
    rewardStatus: z.enum(['locked', 'ready', 'pending', 'passed']),
  }),
  currentNode: GameCampaignNodeSchema.nullable(),
  nodeType: GameNodeTypeSchema.nullable(),
  speakingBoss: GameCampaignNodeSchema.nullable(),
  speakingReward: GameCampaignNodeSchema.nullable(),
  recoveryPanel: z.object({
    queue: z.array(GameCampaignRecoveryItemSchema),
    bossQueue: z.array(GameCampaignRecoveryItemSchema),
    recentMisses: z.array(GameCampaignRecoveryItemSchema),
    resumeNode: GameCampaignRecoveryItemSchema.nullable(),
  }),
})
export type GameCampaignState = z.infer<typeof GameCampaignStateSchema>

export const GameCampaignAttemptResponseSchema = z.object({
  state: z.object({
    nodeType: GameNodeTypeSchema,
    status: z.string(),
    failedDimensions: z.array(GameCampaignDimensionSchema).default([]),
    bossFailures: z.number().int().nonnegative().optional().default(0),
    rewardFailures: z.number().int().nonnegative().optional().default(0),
  }),
  game_state: GameCampaignStateSchema,
})
export type GameCampaignAttemptResponse = z.infer<typeof GameCampaignAttemptResponseSchema>

export type GamePracticeWord = GameCampaignWord
export type GamePracticeState = GameCampaignState
export type GamePracticeAttemptResponse = GameCampaignAttemptResponse

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

export const AISpeakingPromptsResponseSchema = z.object({
  promptText: z.string(),
  followUps: z.array(z.string()),
  recommendedDurationSeconds: z.number().int().positive(),
})
export type AISpeakingPromptsResponse = z.infer<typeof AISpeakingPromptsResponseSchema>

export const AISpeakingDimensionBandsSchema = z.object({
  fluency: z.number(),
  lexical: z.number(),
  grammar: z.number(),
  pronunciation: z.number(),
})
export type AISpeakingDimensionBands = z.infer<typeof AISpeakingDimensionBandsSchema>

export const AISpeakingRawScoresSchema = z.object({
  fluency: z.number().int(),
  lexical: z.number().int(),
  grammar: z.number().int(),
  pronunciation: z.number().int(),
})
export type AISpeakingRawScores = z.infer<typeof AISpeakingRawScoresSchema>

export const AISpeakingFeedbackSchema = z.object({
  summary: z.string(),
  strengths: z.array(z.string()).default([]),
  priorities: z.array(z.string()).default([]),
  dimensionFeedback: z.object({
    fluency: z.string(),
    lexical: z.string(),
    grammar: z.string(),
    pronunciation: z.string(),
  }),
})
export type AISpeakingFeedback = z.infer<typeof AISpeakingFeedbackSchema>

export const AISpeakingMetricsSchema = z.object({
  durationSeconds: z.number().int().nullable().optional(),
  wordCount: z.number().int().nonnegative(),
  uniqueWordCount: z.number().int().nonnegative(),
  typeTokenRatio: z.number(),
  estimatedWpm: z.number().int().nullable().optional(),
  targetWordsAttempted: z.number().int().nonnegative(),
  targetWordsUsed: z.array(z.string()).default([]),
  rawScores: AISpeakingRawScoresSchema.optional(),
})
export type AISpeakingMetrics = z.infer<typeof AISpeakingMetricsSchema>

export const AISpeakingAssessmentResponseSchema = z.object({
  assessmentId: z.number().int(),
  part: z.number().int(),
  topic: z.string(),
  promptText: z.string(),
  targetWords: z.array(z.string()).default([]),
  transcript: z.string(),
  overallBand: z.number(),
  dimensionBands: AISpeakingDimensionBandsSchema,
  feedback: AISpeakingFeedbackSchema,
  metrics: AISpeakingMetricsSchema,
  provider: z.string().nullable().optional().default(null),
  model: z.string().nullable().optional().default(null),
  createdAt: z.string().nullable().optional().default(null),
})
export type AISpeakingAssessmentResponse = z.infer<typeof AISpeakingAssessmentResponseSchema>

export const AISpeakingHistoryItemSchema = z.object({
  assessmentId: z.number().int(),
  part: z.number().int(),
  topic: z.string(),
  promptText: z.string(),
  targetWords: z.array(z.string()).default([]),
  transcriptExcerpt: z.string(),
  overallBand: z.number(),
  dimensionBands: AISpeakingDimensionBandsSchema,
  createdAt: z.string().nullable().optional().default(null),
})
export type AISpeakingHistoryItem = z.infer<typeof AISpeakingHistoryItemSchema>

export const AISpeakingHistoryResponseSchema = z.object({
  items: z.array(AISpeakingHistoryItemSchema),
})
export type AISpeakingHistoryResponse = z.infer<typeof AISpeakingHistoryResponseSchema>
