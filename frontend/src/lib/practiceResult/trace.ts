const TRACE_ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,127}$/

function fallbackRandomId(): string {
  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).slice(2, 12)
  return `${timestamp}${random}`
}

export function createPracticeTraceId(prefix = 'practice'): string {
  const normalizedPrefix = prefix.trim().replace(/[^a-zA-Z0-9._:-]/g, '-') || 'practice'
  const randomId = globalThis.crypto?.randomUUID?.() ?? fallbackRandomId()
  return `${normalizedPrefix}:${randomId}`
}

export function isValidPracticeTraceId(value: string | null | undefined): value is string {
  return Boolean(value && TRACE_ID_PATTERN.test(value))
}

export function normalizePracticeTraceId(value: string | null | undefined): string {
  return isValidPracticeTraceId(value) ? value : createPracticeTraceId()
}
