export interface BuildPracticeIdempotencyKeyInput {
  sessionId?: string | number | null
  localSessionId?: string | null
  mode: string
  scopeKey: string
  wordKey: string
  dimension: string
  attemptIndex: number
}

const IDEMPOTENCY_KEY_PATTERN = /^practice:[a-z0-9._-]+:[a-z0-9._-]+:[a-z0-9._-]+:[a-z0-9._-]+:[a-z0-9._-]+:\d+$/

function sanitizeKeySegment(value: string | number | null | undefined, fallback: string): string {
  const normalized = String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9._-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  return normalized || fallback
}

export function buildPracticeIdempotencyKey(input: BuildPracticeIdempotencyKeyInput): string {
  const sessionSegment = input.sessionId == null
    ? sanitizeKeySegment(input.localSessionId, 'local')
    : sanitizeKeySegment(input.sessionId, 'session')

  return [
    'practice',
    sessionSegment,
    sanitizeKeySegment(input.mode, 'mode'),
    sanitizeKeySegment(input.scopeKey, 'scope'),
    sanitizeKeySegment(input.wordKey, 'word'),
    sanitizeKeySegment(input.dimension, 'dimension'),
    String(Math.max(0, Math.trunc(input.attemptIndex || 0))),
  ].join(':')
}

export function isValidPracticeIdempotencyKey(value: string | null | undefined): value is string {
  return Boolean(value && IDEMPOTENCY_KEY_PATTERN.test(value))
}
