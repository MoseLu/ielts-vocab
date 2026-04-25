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

export const GameLevelKindSchema = z.enum([
  'spelling',
  'pronunciation',
  'definition',
  'speaking',
  'example',
])
export type GameLevelKind = z.infer<typeof GameLevelKindSchema>

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
  levelKind: GameLevelKindSchema.nullable().optional().default(null),
  levelLabel: z.string().nullable().optional().default(null),
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

export const GameLevelCardSchema = z.object({
  kind: GameLevelKindSchema,
  dimension: GameCampaignDimensionSchema,
  label: z.string(),
  subtitle: z.string(),
  assetKey: z.string(),
  step: z.number().int().positive(),
  status: z.enum(['locked', 'ready', 'active', 'pending', 'passed']),
  passStreak: z.number().int().nonnegative(),
  attemptCount: z.number().int().nonnegative(),
})
export type GameLevelCard = z.infer<typeof GameLevelCardSchema>

export const GameSessionSchema = z.object({
  status: z.enum(['launcher', 'active', 'result']).catch('launcher'),
  score: z.number().int().catch(0),
  hits: z.number().int().catch(0),
  bestHits: z.number().int().catch(0),
  hintsRemaining: z.number().int().catch(0),
  hintUsage: z.number().int().catch(0),
  energy: z.number().int().catch(0),
  energyMax: z.number().int().catch(5),
  nextEnergyAt: z.string().nullable().optional().default(null),
  enabledBoosts: z.record(z.string(), z.boolean()).catch({}),
  resultOverlay: z.record(z.string(), z.unknown()).nullable().optional().default(null),
  boostModule: z.record(z.string(), z.unknown()).nullable().optional().default(null),
})
export type GameSession = z.infer<typeof GameSessionSchema>

export const GameLauncherSchema = z.object({
  lessonId: z.string().catch('lesson-1'),
  title: z.string().catch('五维词关'),
  estimatedMinutes: z.number().int().catch(5),
  energyCost: z.number().int().catch(2),
  passScore: z.number().int().catch(70),
  segmentIndex: z.number().int().nonnegative().catch(0),
  boosts: z.record(z.string(), z.boolean()).catch({}),
})
export type GameLauncher = z.infer<typeof GameLauncherSchema>

export const GameRewardSummarySchema = z.object({
  coins: z.number().int().catch(0),
  diamonds: z.number().int().catch(0),
  exp: z.number().int().catch(0),
  stars: z.number().int().catch(0),
  chest: z.enum(['normal', 'sapphire', 'golden', 'special']).catch('normal'),
  bestHits: z.number().int().catch(0),
})
export type GameRewardSummary = z.infer<typeof GameRewardSummarySchema>

export const GameCampaignHudSchema = z.object({
  playerLevel: z.number().int().positive().catch(1),
  levelProgressPercent: z.number().int().min(0).max(100).catch(0),
  unreadMessages: z.number().int().nonnegative().catch(0),
})
export type GameCampaignHud = z.infer<typeof GameCampaignHudSchema>

export const GameAnimationPayloadSchema = z.object({
  sceneTheme: z.string().nullable().optional().default(null),
  mascotState: z.string().nullable().optional().default(null),
  feedbackTone: z.string().nullable().optional().default(null),
  showResultLayer: z.boolean().catch(false),
})
export type GameAnimationPayload = z.infer<typeof GameAnimationPayloadSchema>

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
  levelCards: z.array(GameLevelCardSchema).default([]),
  rewards: GameRewardSummarySchema.optional().default({
    coins: 0,
    diamonds: 0,
    exp: 0,
    stars: 0,
    chest: 'normal',
    bestHits: 0,
  }),
  session: GameSessionSchema.optional(),
  launcher: GameLauncherSchema.optional(),
  hud: GameCampaignHudSchema.optional().default({
    playerLevel: 1,
    levelProgressPercent: 0,
    unreadMessages: 0,
  }),
  animationPayload: GameAnimationPayloadSchema.optional(),
  boostModule: z.record(z.string(), z.unknown()).nullable().optional().default(null),
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

export const GameCampaignStartResponseSchema = z.object({
  game_state: GameCampaignStateSchema,
})
export type GameCampaignStartResponse = z.infer<typeof GameCampaignStartResponseSchema>

export type GamePracticeWord = GameCampaignWord
export type GamePracticeState = GameCampaignState
export type GamePracticeAttemptResponse = GameCampaignAttemptResponse
