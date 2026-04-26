import { z } from 'zod'

export const HomeTodoActionSchema = z.object({
  kind: z.enum(['add-book', 'due-review', 'error-review', 'continue-book', 'speaking']),
  cta_label: z.string(),
  task: z.enum(['add-book', 'due-review', 'error-review', 'continue-book', 'speaking']).nullable().optional().default(null),
  mode: z.string().nullable().optional().default(null),
  book_id: z.string().nullable().optional().default(null),
  chapter_id: z.union([z.string(), z.number()]).nullable().optional().default(null),
  dimension: z.string().nullable().optional().default(null),
})
export type HomeTodoAction = z.infer<typeof HomeTodoActionSchema>

export const HomeTodoStepSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(['pending', 'current', 'completed']),
})
export type HomeTodoStep = z.infer<typeof HomeTodoStepSchema>

export const HomeTodoItemSchema = z.object({
  id: z.string(),
  task_key: z.string().optional().default(''),
  kind: z.enum(['add-book', 'due-review', 'error-review', 'continue-book', 'speaking']),
  title: z.string(),
  description: z.string(),
  status: z.enum(['pending', 'completed']),
  completion_source: z.enum(['completed_today', 'already_clear']).nullable().optional().default(null),
  badge: z.string(),
  steps: z.array(HomeTodoStepSchema).optional().default([]),
  action: HomeTodoActionSchema,
  carry_over_count: z.number().int().optional().default(0),
})
export type HomeTodoItem = z.infer<typeof HomeTodoItemSchema>

export const HomeTodoPlanSummarySchema = z.object({
  pending_count: z.number().int(),
  completed_count: z.number().int(),
  carry_over_count: z.number().int(),
  last_generated_at: z.string().nullable(),
})
export type HomeTodoPlanSummary = z.infer<typeof HomeTodoPlanSummarySchema>

export const HomeTodoResponseSchema = z.object({
  date: z.string(),
  summary: HomeTodoPlanSummarySchema,
  primary_items: z.array(HomeTodoItemSchema),
  overflow_items: z.array(HomeTodoItemSchema),
})
export type HomeTodoResponse = z.infer<typeof HomeTodoResponseSchema>
