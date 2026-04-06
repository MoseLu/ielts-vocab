// ── Tests for src/lib/validation.ts ─────────────────────────────────────────

import { z } from 'zod'
import {
  safeParse,
  parseOrThrow,
  safeParseJSON,
  formatErrors,
  firstError,
} from './validation'

describe('safeParse', () => {
  const schema = z.object({ name: z.string(), age: z.number() })

  it('returns success with valid data', () => {
    const result = safeParse(schema, { name: 'Alice', age: 30 })
    expect(result.success).toBe(true)
    if (result.success) expect(result.data).toEqual({ name: 'Alice', age: 30 })
  })

  it('returns failure with invalid data', () => {
    const result = safeParse(schema, { name: 123 })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.errors.length).toBeGreaterThan(0)
    }
  })

  it('maps Zod issues to readable error messages', () => {
    const result = safeParse(schema, { name: 1, age: 'not-a-number' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.errors[0]).toContain('name')
    }
  })

  it('handles totally invalid input', () => {
    const result = safeParse(schema, null)
    expect(result.success).toBe(false)
    if (!result.success) expect(result.errors.length).toBeGreaterThan(0)
  })

  it('preserves path in error messages', () => {
    const nested = z.object({ user: z.object({ email: z.string().email() }) })
    const result = safeParse(nested, { user: { email: 'invalid' } })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.errors[0]).toContain('user.email')
    }
  })
})

describe('parseOrThrow', () => {
  const schema = z.object({ id: z.number() })

  it('returns data on valid input', () => {
    expect(parseOrThrow(schema, { id: 42 })).toEqual({ id: 42 })
  })

  it('throws with custom label on invalid input', () => {
    expect(() => parseOrThrow(schema, { id: 'bad' }, 'UserSchema')).toThrow(
      'UserSchema failed:'
    )
  })

  it('uses default label "validation"', () => {
    expect(() => parseOrThrow(schema, { id: 'bad' })).toThrow('validation failed:')
  })
})

describe('safeParseJSON', () => {
  it('parses valid JSON', () => {
    const result = safeParseJSON('{"count":5}', { count: 0 })
    expect(result.success).toBe(true)
    if (result.success) expect(result.data).toEqual({ count: 5 })
  })

  it('returns fallback on null input', () => {
    const result = safeParseJSON<string[]>(null, ['default'])
    expect(result.success).toBe(true)
    if (result.success) expect(result.data).toEqual(['default'])
  })

  it('returns fallback on malformed JSON', () => {
    const result = safeParseJSON<number[]>('{bad json}', [99])
    expect(result.success).toBe(true)
    if (result.success) expect(result.data).toEqual([99])
  })
})

describe('formatErrors', () => {
  it('joins errors with Chinese semicolon', () => {
    const failure = { success: false as const, errors: ['error one', 'error two'] }
    expect(formatErrors(failure)).toBe('error one；error two')
  })

  it('handles empty errors array', () => {
    const failure = { success: false as const, errors: [] }
    expect(formatErrors(failure)).toBe('')
  })
})

describe('firstError', () => {
  it('returns the first error message', () => {
    const failure = { success: false as const, errors: ['first', 'second'] }
    expect(firstError(failure)).toBe('first')
  })

  it('returns empty string when no errors', () => {
    const failure = { success: false as const, errors: [] }
    expect(firstError(failure)).toBe('')
  })
})
