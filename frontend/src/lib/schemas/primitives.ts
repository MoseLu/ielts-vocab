import { z } from 'zod'

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
