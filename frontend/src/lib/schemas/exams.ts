import { z } from 'zod'


const ExamQuestionTypeSchema = z.enum([
  'single_choice',
  'multiple_choice',
  'matching',
  'fill_blank',
  'short_answer',
  'writing_prompt',
  'speaking_prompt',
])

const ExamChoiceSchema = z.object({
  id: z.number().int(),
  key: z.string(),
  label: z.string().nullable().optional(),
  contentHtml: z.string(),
})
export type ExamChoice = z.infer<typeof ExamChoiceSchema>

const ExamTrackSchema = z.object({
  assetId: z.number().int().nullable().optional(),
  partNumber: z.number().int().nullable().optional(),
  title: z.string().nullable().optional(),
  sourceUrl: z.string().nullable().optional(),
})

const ExamResponseSchema = z.object({
  id: z.number().int(),
  questionId: z.number().int(),
  responseText: z.string().nullable().optional(),
  selectedChoices: z.array(z.string()).default([]),
  attachmentUrl: z.string().nullable().optional(),
  durationSeconds: z.number().int().nullable().optional(),
  isCorrect: z.boolean().nullable().optional(),
  score: z.number().nullable().optional(),
  feedback: z.record(z.string(), z.unknown()).default({}),
})
export type ExamResponse = z.infer<typeof ExamResponseSchema>

const ExamQuestionSchema = z.object({
  id: z.number().int(),
  questionNumber: z.number().int().nullable().optional(),
  sortOrder: z.number().int(),
  questionType: ExamQuestionTypeSchema,
  promptHtml: z.string(),
  groupKey: z.string(),
  confidence: z.number(),
  choices: z.array(ExamChoiceSchema).default([]),
  acceptedAnswers: z.array(z.string()).default([]),
  response: ExamResponseSchema.nullable().optional(),
})
export type ExamQuestion = z.infer<typeof ExamQuestionSchema>

const ExamPassageSchema = z.object({
  id: z.number().int(),
  title: z.string().nullable().optional(),
  htmlContent: z.string(),
  sourcePageFrom: z.number().int().nullable().optional(),
  sourcePageTo: z.number().int().nullable().optional(),
  confidence: z.number(),
})
export type ExamPassage = z.infer<typeof ExamPassageSchema>

const ExamSectionSchema = z.object({
  id: z.number().int(),
  sectionType: z.string(),
  title: z.string(),
  instructionsHtml: z.string().nullable().optional(),
  htmlContent: z.string().nullable().optional(),
  confidence: z.number(),
  audioAssetId: z.number().int().nullable().optional(),
  audioTracks: z.array(ExamTrackSchema).default([]),
  passages: z.array(ExamPassageSchema).default([]),
  questions: z.array(ExamQuestionSchema).default([]),
})
export type ExamSection = z.infer<typeof ExamSectionSchema>

const ExamReviewItemSchema = z.object({
  id: z.number().int(),
  itemType: z.string(),
  severity: z.string(),
  status: z.string(),
  message: z.string(),
  sectionId: z.number().int().nullable().optional(),
  questionId: z.number().int().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()).default({}),
})

export const ExamAttemptSchema = z.object({
  id: z.number().int(),
  paperId: z.number().int(),
  status: z.string(),
  objectiveCorrect: z.number().int(),
  objectiveTotal: z.number().int(),
  autoScore: z.number(),
  maxScore: z.number(),
  feedback: z.record(z.string(), z.unknown()).default({}),
  startedAt: z.string().nullable().optional(),
  submittedAt: z.string().nullable().optional(),
  responses: z.array(ExamResponseSchema).default([]),
})
export type ExamAttempt = z.infer<typeof ExamAttemptSchema>

export const ExamPaperSummarySchema = z.object({
  id: z.number().int(),
  collectionTitle: z.string(),
  title: z.string(),
  seriesNumber: z.number().int().nullable().optional(),
  testNumber: z.number().int().nullable().optional(),
  examKind: z.string(),
  publishStatus: z.string(),
  rightsStatus: z.string(),
  importConfidence: z.number(),
  answerKeyConfidence: z.number(),
  hasListeningAudio: z.boolean(),
  reviewCount: z.number().int(),
  sections: z.array(z.object({
    id: z.number().int(),
    sectionType: z.string(),
    title: z.string(),
    audioTracks: z.array(ExamTrackSchema).default([]),
    questionCount: z.number().int(),
  })).default([]),
  latestAttempt: ExamAttemptSchema.nullable().optional(),
})
export type ExamPaperSummary = z.infer<typeof ExamPaperSummarySchema>

export const ExamPaperDetailSchema = z.object({
  id: z.number().int(),
  collectionTitle: z.string(),
  title: z.string(),
  seriesNumber: z.number().int().nullable().optional(),
  testNumber: z.number().int().nullable().optional(),
  examKind: z.string(),
  publishStatus: z.string(),
  rightsStatus: z.string(),
  importConfidence: z.number(),
  answerKeyConfidence: z.number(),
  hasListeningAudio: z.boolean(),
  sections: z.array(ExamSectionSchema).default([]),
  reviewItems: z.array(ExamReviewItemSchema).default([]),
})
export type ExamPaperDetail = z.infer<typeof ExamPaperDetailSchema>

export const ExamPapersResponseSchema = z.object({
  items: z.array(ExamPaperSummarySchema).default([]),
})
export type ExamPapersResponse = z.infer<typeof ExamPapersResponseSchema>

export const ExamPaperDetailResponseSchema = z.object({
  paper: ExamPaperDetailSchema,
  latestAttempt: ExamAttemptSchema.nullable().optional(),
})
export type ExamPaperDetailResponse = z.infer<typeof ExamPaperDetailResponseSchema>

export const ExamAttemptResponseSchema = z.object({
  attempt: ExamAttemptSchema,
})
export type ExamAttemptResponse = z.infer<typeof ExamAttemptResponseSchema>

export const ExamAttemptResultResponseSchema = z.object({
  attempt: ExamAttemptSchema,
  summary: z.object({
    objectiveCorrect: z.number().int(),
    objectiveTotal: z.number().int(),
    autoScore: z.number(),
    maxScore: z.number(),
    feedback: z.record(z.string(), z.unknown()).default({}),
  }),
})
export type ExamAttemptResultResponse = z.infer<typeof ExamAttemptResultResponseSchema>
