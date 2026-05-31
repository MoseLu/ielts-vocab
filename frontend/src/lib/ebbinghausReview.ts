import {
  readQuickMemoryRecordsFromStorage,
  updateQuickMemoryRecord,
  writeQuickMemoryRecordsToStorage,
  type QuickMemoryRecordState,
} from './quickMemory'
import { buildLearningScope } from './learningScope'
import { syncQuickMemoryRecordsToBackend } from './quickMemorySync'

interface EbbinghausWordPayload {
  word?: string | null
  chapter_id?: string | number | null
  chapterId?: string | number | null
}

interface RecordEbbinghausPracticeResultInput {
  word: string | EbbinghausWordPayload
  passed: boolean
  sourceMode?: string | null
  bookId?: string | null
  chapterId?: string | number | null
  scopeKey?: string | null
  scopeType?: string | null
  originScope?: Record<string, unknown> | null
  occurredAt?: number
}

function resolveWordText(word: string | EbbinghausWordPayload): string {
  return typeof word === 'string' ? word : String(word.word ?? '')
}

function resolveChapterId(
  word: string | EbbinghausWordPayload,
  chapterId?: string | number | null,
): string | undefined {
  const rawValue = chapterId ?? (typeof word === 'string' ? null : (word.chapterId ?? word.chapter_id))
  if (rawValue === null || rawValue === undefined) return undefined
  const normalized = String(rawValue).trim()
  return normalized || undefined
}

export function recordEbbinghausPracticeResult({
  word,
  passed,
  sourceMode,
  bookId,
  chapterId,
  scopeKey,
  scopeType,
  originScope,
  occurredAt,
}: RecordEbbinghausPracticeResultInput): QuickMemoryRecordState | null {
  const wordText = resolveWordText(word)
  if (!wordText.trim()) return null
  const scope = buildLearningScope({
    scopeKey,
    scopeType,
    originScope,
    bookId,
    chapterId: resolveChapterId(word, chapterId),
  })

  const { records, record } = updateQuickMemoryRecord(
    readQuickMemoryRecordsFromStorage(undefined, scope),
    wordText,
    passed ? 'known' : 'unknown',
    false,
    occurredAt ?? Date.now(),
    scope,
  )
  writeQuickMemoryRecordsToStorage(records, undefined, scope)
  if (!record) return null

  void syncQuickMemoryRecordsToBackend(
    [{ word: wordText, record }],
    { ...scope, source: 'practice', sourceMode: sourceMode ?? undefined },
  ).catch(() => {})
  return record
}
