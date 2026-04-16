type BookPracticeConfig = {
  id: string | number
  practice_mode?: string
}

export type BookEntryMode = 'practice' | 'game'

export function buildBookPracticePath(
  book: BookPracticeConfig,
  chapterId?: string | number | null,
): string {
  const pathname = book.practice_mode === 'match' ? '/practice/confusable' : '/practice'
  const params = new URLSearchParams({ book: String(book.id) })

  if (chapterId != null) {
    params.set('chapter', String(chapterId))
  }

  return `${pathname}?${params.toString()}`
}

export function buildBookGamePath(
  book: BookPracticeConfig,
  chapterId?: string | number | null,
): string {
  const params = new URLSearchParams({ book: String(book.id) })

  if (chapterId != null) {
    params.set('chapter', String(chapterId))
  }

  return `/game?${params.toString()}`
}

export function buildBookStudyEntryPath(
  book: BookPracticeConfig,
  entryMode: BookEntryMode = 'practice',
  chapterId?: string | number | null,
): string {
  return entryMode === 'game'
    ? buildBookGamePath(book, chapterId)
    : buildBookPracticePath(book, chapterId)
}
