import {
  buildMobileWrongWordsReviewQueue,
  resolvePracticeQueueSource,
  type MobileBook,
  type MobileChapter,
  type MobileWord,
  type PracticeMode,
  type PracticeQueueSource,
} from '@ielts-vocab/app-core'
import { loadBooks, loadChapterWords, loadChapters, loadQuickMemoryReviewQueue, loadWrongWords } from '../../../api/learnerApi'
import type { NavigateOptions } from '../../../navigation/types'
import { getErrorReviewFilters } from './errorReviewProgressStorage'

const QUICK_MEMORY_REVIEW_LIMIT = 10
const QUICK_MEMORY_REVIEW_WINDOW_DAYS = 3

export type PracticeBootstrapData = {
  books: MobileBook[]
  chapters: MobileChapter[]
  initialBookId: string
}

export type PracticeQueueLoadResult = {
  queueSource: PracticeQueueSource
  words: MobileWord[]
}

export async function loadPracticeBootstrap(options?: NavigateOptions): Promise<PracticeBootstrapData> {
  const books = await loadBooks()
  const initialBookId = options?.bookId || String(books[0]?.id ?? '')
  const chapters = initialBookId ? await loadChapters(initialBookId) : []
  return { books, chapters, initialBookId }
}

export async function loadBookChapters(bookId: string): Promise<MobileChapter[]> {
  return loadChapters(bookId)
}

export async function loadPracticeQueue(params: {
  bookId: string
  chapterId?: string | number | null
  dueReviewRequested: boolean
  mode: PracticeMode
  options?: NavigateOptions
  refreshSmartPracticeContext: () => Promise<void>
}): Promise<PracticeQueueLoadResult> {
  const queueSource = resolvePracticeQueueSource({
    dueReviewRequested: params.dueReviewRequested,
    mode: params.mode,
  })
  if (queueSource === 'chapter' && !params.bookId) throw new Error('请先选择练习范围')
  if (params.mode === 'smart') await params.refreshSmartPracticeContext()

  const errorFilters = getErrorReviewFilters(params.options)
  const words = queueSource === 'errors'
    ? buildMobileWrongWordsReviewQueue(
      await loadWrongWords('', errorFilters),
      errorFilters,
      params.options?.selectedWrongWords ?? [],
    )
    : queueSource === 'due-review'
      ? await loadQuickMemoryReviewQueue({
        bookId: params.bookId || null,
        chapterId: params.chapterId,
        limit: QUICK_MEMORY_REVIEW_LIMIT,
        offset: 0,
        withinDays: QUICK_MEMORY_REVIEW_WINDOW_DAYS,
      })
      : await loadChapterWords(params.bookId, params.chapterId)

  return { queueSource, words }
}
