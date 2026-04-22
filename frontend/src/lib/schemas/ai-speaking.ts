import { z } from 'zod'

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
