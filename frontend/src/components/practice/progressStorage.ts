import { STORAGE_KEYS } from '../../constants'
import { apiFetch } from '../../lib'
import type { ProgressData } from './types'

interface StoredSelection {
  id?: string | number | null
}

function readStoredSelection(key: string): StoredSelection | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) as StoredSelection : null
  } catch {
    return null
  }
}

export function readStoredChapterStartIndex(
  bookId: string | null | undefined,
  chapterId: string | number | null | undefined,
): number {
  if (!bookId || chapterId == null) return 0

  const selectedBook = readStoredSelection('selected_book')
  if (selectedBook?.id != null && String(selectedBook.id) !== String(bookId)) {
    return 0
  }

  const selectedChapter = readStoredSelection('selected_chapter')
  if (selectedChapter?.id != null && String(selectedChapter.id) !== String(chapterId)) {
    return 0
  }

  const rawStartIndex = localStorage.getItem('chapter_start_index')
  const startIndex = rawStartIndex == null ? Number.NaN : Number.parseInt(rawStartIndex, 10)
  return Number.isFinite(startIndex) && startIndex >= 0 ? startIndex : 0
}

function readStoredProgressMap(key: string): Record<string, ProgressData> {
  try {
    return JSON.parse(localStorage.getItem(key) || '{}') as Record<string, ProgressData>
  } catch {
    return {}
  }
}

function writeStoredProgressMap(key: string, value: Record<string, ProgressData>): void {
  localStorage.setItem(key, JSON.stringify(value))
}

function buildStoredSnapshot(progressData: ProgressData): ProgressData {
  return {
    ...progressData,
    updatedAt: new Date().toISOString(),
  }
}

export function readStoredChapterProgressSnapshot(
  bookId: string,
  chapterId: string | number,
): ProgressData | null {
  return readStoredProgressMap(STORAGE_KEYS.CHAPTER_PROGRESS)[`${bookId}_${chapterId}`] ?? null
}

export function persistBookProgressSnapshot(
  bookId: string,
  progressData: ProgressData,
  queueWords: string[],
): void {
  const bookProgress = readStoredProgressMap(STORAGE_KEYS.BOOK_PROGRESS)
  const previous = bookProgress[bookId]
  bookProgress[bookId] = {
    ...buildStoredSnapshot(progressData),
    current_index: Math.max(previous?.current_index ?? 0, progressData.current_index),
    queue_words: queueWords,
  }
  writeStoredProgressMap(STORAGE_KEYS.BOOK_PROGRESS, bookProgress)
}

export function persistChapterProgressSnapshot(
  bookId: string,
  chapterId: string | number,
  progressData: ProgressData,
): void {
  const chapterProgress = readStoredProgressMap(STORAGE_KEYS.CHAPTER_PROGRESS)
  chapterProgress[`${bookId}_${chapterId}`] = buildStoredSnapshot(progressData)
  writeStoredProgressMap(STORAGE_KEYS.CHAPTER_PROGRESS, chapterProgress)
}

export function clearChapterProgressSnapshot(
  bookId: string,
  chapterId: string | number,
): void {
  const chapterProgress = readStoredProgressMap(STORAGE_KEYS.CHAPTER_PROGRESS)
  delete chapterProgress[`${bookId}_${chapterId}`]
  writeStoredProgressMap(STORAGE_KEYS.CHAPTER_PROGRESS, chapterProgress)
}

export async function loadBookProgressSnapshot(bookId: string): Promise<ProgressData | null> {
  const stored = readStoredProgressMap(STORAGE_KEYS.BOOK_PROGRESS)[bookId] ?? null
  if (stored) return stored

  try {
    const remote = await apiFetch<{ progress?: ProgressData }>(`/api/books/progress/${bookId}`)
    return remote.progress ?? null
  } catch {
    return null
  }
}

export async function loadChapterProgressSnapshot(
  bookId: string,
  chapterId: string | number,
): Promise<ProgressData | null> {
  const stored = readStoredChapterProgressSnapshot(bookId, chapterId)
  if (stored) return stored

  try {
    const remote = await apiFetch<{ chapter_progress?: Record<string, ProgressData> }>(
      `/api/books/${bookId}/chapters/progress`,
    )
    return remote.chapter_progress?.[String(chapterId)] ?? null
  } catch {
    return null
  }
}
