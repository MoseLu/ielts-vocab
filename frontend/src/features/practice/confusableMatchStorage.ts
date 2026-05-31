import { STORAGE_KEYS } from '../../constants'
import type { MatchProgressSnapshot } from './confusableMatch'

function readChapterProgressMap(): Record<string, MatchProgressSnapshot> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.CHAPTER_PROGRESS) || '{}') as Record<
      string,
      MatchProgressSnapshot
    >
  } catch {
    return {}
  }
}

export function readStoredChapterSnapshot(bookId: string, chapterId: string): MatchProgressSnapshot | null {
  return readChapterProgressMap()[`${bookId}_${chapterId}`] ?? null
}

export function persistChapterSnapshot(
  bookId: string,
  chapterId: string,
  snapshot: MatchProgressSnapshot,
): void {
  const current = readChapterProgressMap()
  current[`${bookId}_${chapterId}`] = {
    ...snapshot,
    updatedAt: new Date().toISOString(),
  }
  localStorage.setItem(STORAGE_KEYS.CHAPTER_PROGRESS, JSON.stringify(current))
}

export function clearStoredChapterSnapshot(bookId: string, chapterId: string): void {
  const current = readChapterProgressMap()
  delete current[`${bookId}_${chapterId}`]
  localStorage.setItem(STORAGE_KEYS.CHAPTER_PROGRESS, JSON.stringify(current))
}
