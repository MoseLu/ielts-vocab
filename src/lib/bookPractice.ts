type BookPracticeConfig = {
  id: string | number
  practice_mode?: string
}

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
