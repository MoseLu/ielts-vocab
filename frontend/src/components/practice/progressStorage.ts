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

export function persistBookProgressSnapshot(
  bookId: string,
  progressData: ProgressData,
  queueWords: string[],
): void {
  let bookProgress: Record<string, ProgressData> = {}

  try {
    bookProgress = JSON.parse(localStorage.getItem('book_progress') || '{}') as Record<string, ProgressData>
  } catch {
    bookProgress = {}
  }

  const previous = bookProgress[bookId]
  bookProgress[bookId] = {
    ...progressData,
    current_index: Math.max(previous?.current_index ?? 0, progressData.current_index),
    queue_words: queueWords,
    updatedAt: new Date().toISOString(),
  }

  localStorage.setItem('book_progress', JSON.stringify(bookProgress))
}
