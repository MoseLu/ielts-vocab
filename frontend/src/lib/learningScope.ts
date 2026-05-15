export type LearningScopeType = 'chapter' | 'book' | 'day' | 'user' | 'wrong_words' | 'favorites'

export interface LearningScopeInput {
  scopeKey?: string | null
  scopeType?: string | null
  originScope?: Record<string, unknown> | null
  bookId?: string | null
  chapterId?: string | number | null
  day?: number | null
}

export interface LearningScope {
  scopeKey: string
  scopeType: LearningScopeType
  originScope: Record<string, unknown>
  bookId?: string
  chapterId?: string
  day?: number
}

function cleanText(value: unknown): string | undefined {
  const text = String(value ?? '').trim()
  return text || undefined
}

function normalizeDay(value: unknown): number | undefined {
  if (typeof value !== 'number' || !Number.isFinite(value)) return undefined
  const day = Math.trunc(value)
  return day > 0 ? day : undefined
}

function normalizeScopeType(value: unknown): LearningScopeType | undefined {
  const text = cleanText(value)
  if (
    text === 'chapter'
    || text === 'book'
    || text === 'day'
    || text === 'user'
    || text === 'wrong_words'
    || text === 'favorites'
  ) {
    return text
  }
  return undefined
}

function normalizeScopeKey(value: unknown): string | undefined {
  const text = cleanText(value)
  return text === 'global' ? 'user' : text
}

function inferScopeType(scopeKey: string, input: LearningScopeInput): LearningScopeType {
  const explicit = normalizeScopeType(input.scopeType)
  if (explicit) return explicit
  if (scopeKey.startsWith('chapter:') || (input.bookId && input.chapterId != null)) return 'chapter'
  if (scopeKey.startsWith('book:') || input.bookId) return 'book'
  if (scopeKey.startsWith('day:') || input.day != null) return 'day'
  return 'user'
}

export function buildLearningScope(input: LearningScopeInput = {}): LearningScope {
  const bookId = cleanText(input.bookId)
  const chapterId = cleanText(input.chapterId)
  const day = normalizeDay(input.day)
  const explicitScopeKey = normalizeScopeKey(input.scopeKey)
  const scopeKey = explicitScopeKey
    ?? (bookId && chapterId ? `chapter:${bookId}:${chapterId}` : undefined)
    ?? (bookId ? `book:${bookId}` : undefined)
    ?? (day != null ? `day:${day}` : undefined)
    ?? 'user'
  const scopeType = inferScopeType(scopeKey, { ...input, bookId, chapterId, day })
  const originScope = {
    ...(input.originScope && typeof input.originScope === 'object' ? input.originScope : {}),
    scopeKey,
    scopeType,
    ...(bookId ? { bookId } : {}),
    ...(chapterId ? { chapterId } : {}),
    ...(day != null ? { day } : {}),
  }

  return {
    scopeKey,
    scopeType,
    originScope,
    ...(bookId ? { bookId } : {}),
    ...(chapterId ? { chapterId } : {}),
    ...(day != null ? { day } : {}),
  }
}
