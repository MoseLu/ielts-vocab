import {
  readQuickMemoryRecordsFromStorage,
  updateQuickMemoryRecord,
  writeQuickMemoryRecordsToStorage,
  type QuickMemoryRecordState,
} from './quickMemory'
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
  occurredAt,
}: RecordEbbinghausPracticeResultInput): QuickMemoryRecordState | null {
  const wordText = resolveWordText(word)
  if (!wordText.trim()) return null

  const { records, record } = updateQuickMemoryRecord(
    readQuickMemoryRecordsFromStorage(),
    wordText,
    passed ? 'known' : 'unknown',
    false,
    occurredAt ?? Date.now(),
    {
      bookId: bookId ?? undefined,
      chapterId: resolveChapterId(word, chapterId),
    },
  )
  writeQuickMemoryRecordsToStorage(records)
  if (!record) return null

  void syncQuickMemoryRecordsToBackend(
    [{ word: wordText, record }],
    { source: 'practice', sourceMode: sourceMode ?? undefined },
  ).catch(() => {})
  return record
}
