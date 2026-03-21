// ── useForm Validation Hook ──────────────────────────────────────────────────
// Zod-powered form validation for React components

import { useState, useCallback } from 'react'
import { z } from 'zod'
import { safeParse, formatErrors, firstError } from './validation'

export type { ValidationResult, ValidationFailure, ValidationSuccess } from './validation'

interface UseFormOptions<S extends z.ZodTypeAny> {
  schema: S
  initialValues?: Partial<z.infer<S>>
}

/**
 * Provides field-level and form-level validation backed by Zod.
 *
 * @example
 * const form = useForm({ schema: RegisterSchema })
 * const handleSubmit = form.handleSubmit(async (values) => {
 *   await register(values.email, values.password, values.username)
 * })
 */
export function useForm<S extends z.ZodTypeAny>({ schema, initialValues }: UseFormOptions<S>) {
  const [values, setValues] = useState<Partial<z.infer<S>>>(() => initialValues ?? {})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  /** Update a single field value */
  const setFieldValue = useCallback(<K extends keyof z.infer<S>>(field: K, value: z.infer<S>[K]) => {
    setValues(prev => ({ ...prev, [field]: value }))
    // Re-validate the field
    const result = safeParse(schema, { ...values, [field]: value })
    if (!result.success) {
      const fieldError = result.errors.find(e => e.startsWith(`[${String(field)}]`))
      setErrors(prev => ({
        ...prev,
        [field]: fieldError ? fieldError.replace(/^\[.*?\] /, '') : '',
      }))
    } else {
      setErrors(prev => {
        const next = { ...prev }
        delete next[field as string]
        return next
      })
    }
  }, [schema, values])

  /** Mark a field as touched (for showing errors on blur) */
  const setFieldTouched = useCallback((field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }))
  }, [])

  /** Validate the entire form and return whether it's valid */
  const validate = useCallback((): boolean => {
    const result = safeParse(schema, values)
    if (result.success) {
      setErrors({})
      return true
    }

    // Map errors to field keys
    const fieldErrors: Record<string, string> = {}
    for (const err of result.errors) {
      // Extract field name from "[field]" prefix
      const match = err.match(/^\[(.+?)\] /)
      if (match) {
        const key = match[1]
        if (!fieldErrors[key]) {
          fieldErrors[key] = err.replace(/^\[.*?\] /, '')
        }
      } else {
        // Non-field error goes under '__form'
        fieldErrors.__form = err
      }
    }
    setErrors(fieldErrors)
    return false
  }, [schema, values])

  /**
   * Run validation then call the submit handler.
   * Pass a function that throws on failure — errors will be displayed as form-level errors.
   */
  const handleSubmit = useCallback(
    (onValid: (values: z.infer<S>) => Promise<void>) => {
      return async (e: React.FormEvent) => {
        e.preventDefault()
        const isValid = validate()
        if (!isValid) return
        try {
          await onValid(values as z.infer<S>)
        } catch (err) {
          setErrors(prev => ({
            ...prev,
            __form: err instanceof Error ? err.message : String(err),
          }))
        }
      }
    },
    [validate, values]
  )

  /** Reset form to initial state */
  const reset = useCallback(() => {
    setValues(initialValues ?? {})
    setErrors({})
    setTouched({})
  }, [initialValues])

  /** Get error for a specific field (only if touched) */
  const getFieldError = useCallback((field: string): string | undefined => {
    return touched[field] ? errors[field] : undefined
  }, [touched, errors])

  return {
    values: values as z.infer<S>,
    errors,
    touched,
    setFieldValue,
    setFieldTouched,
    validate,
    handleSubmit,
    reset,
    getFieldError,
    hasErrors: Object.keys(errors).filter(k => k !== '__form').length > 0,
  }
}
