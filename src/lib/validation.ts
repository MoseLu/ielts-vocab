// ── Validation Utilities ─────────────────────────────────────────────────────
// Safe wrappers around Zod schemas — never throw, always return typed results

import { z } from 'zod'

// ── Result type ────────────────────────────────────────────────────────────

export type ValidationSuccess<T> = { success: true; data: T }
export type ValidationFailure = { success: false; errors: string[] }
export type ValidationResult<T> = ValidationSuccess<T> | ValidationFailure

// ── Core safeParse ────────────────────────────────────────────────────────

/**
 * Wraps z.schema.safeParse() so callers always get a typed result
 * instead of a thrown error. Individual field errors are joined into
 * a single string array.
 */
export function safeParse<S extends z.ZodTypeAny>(
  schema: S,
  data: unknown
): ValidationResult<z.infer<S>> {
  const result = schema.safeParse(data)

  if (result.success) {
    return { success: true, data: result.data }
  }

  const errors = result.error.issues.map((issue) => {
    const path = issue.path.length > 0 ? `[${issue.path.join('.')}] ` : ''
    return `${path}${issue.message}`
  })

  return { success: false, errors }
}

// ── Specialised helpers ────────────────────────────────────────────────────

/** Validates data against a schema; throws if invalid (use in tests / trusted env) */
export function parseOrThrow<S extends z.ZodTypeAny>(
  schema: S,
  data: unknown,
  label = 'validation'
): z.infer<S> {
  const result = safeParse(schema, data)
  if (!result.success) {
    throw new Error(`${label} failed: ${result.errors.join('; ')}`)
  }
  return result.data
}

/** Validates localStorage JSON — returns null on parse failure instead of throwing */
export function safeParseJSON<T>(raw: string | null, fallback: T): ValidationSuccess<T> {
  if (raw === null) return { success: true, data: fallback }
  try {
    const parsed = JSON.parse(raw)
    return { success: true, data: parsed as T }
  } catch {
    return { success: true, data: fallback }
  }
}

/** Joins ValidationFailure.errors into a single human-readable string */
export function formatErrors(result: ValidationFailure): string {
  return result.errors.join('；')
}

/** Returns the first error or an empty string */
export function firstError(result: ValidationFailure): string {
  return result.errors[0] ?? ''
}
