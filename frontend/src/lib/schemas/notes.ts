import { z } from 'zod'

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
