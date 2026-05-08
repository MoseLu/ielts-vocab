import {
  ExamPaperDetailSchema,
  ExamPaperSummarySchema,
  HomeTodoPayloadSchema,
  JournalSummarySchema,
  LearningNoteSchema,
  LearningStatsPayloadSchema,
  MobileBookSchema,
  MobileChapterSchema,
  MobileWordSchema,
  WrongWordSchema,
  parseArray,
  type ExamPaperDetail,
  type ExamPaperSummary,
  type HomeTodoPayload,
  type JournalSummary,
  type LearningNote,
  type LearningStatsPayload,
  type MobileBook,
  type MobileChapter,
  type MobileWord,
  type PracticeMode,
  type WrongWord,
} from '@ielts-vocab/app-core'
import { mobileApiClient } from './mobileApi'

export type ExamResponseDraft = {
  questionId: number
  responseText?: string | null
  selectedChoices?: string[]
  durationSeconds?: number | null
}

export type ProgressSnapshot = Record<string, unknown> & {
  accuracy?: number | null
  book_id?: string
  chapter_id?: string | number
  completed_chapters?: number
  correct_count?: number
  current_index?: number
  is_completed?: boolean
  progress_percent?: number
  total_chapters?: number
  total_words?: number
  words_learned?: number
  wrong_count?: number
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  })
  const value = search.toString()
  return value ? `?${value}` : ''
}

function normalizeProgressMap(value: unknown, idKey: 'book_id' | 'chapter_id'): Record<string, ProgressSnapshot> {
  const result: Record<string, ProgressSnapshot> = {}
  const put = (key: string, snapshot: unknown) => {
    if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot)) return
    result[key] = snapshot as ProgressSnapshot
  }

  if (Array.isArray(value)) {
    value.forEach(item => {
      if (!item || typeof item !== 'object') return
      const key = (item as ProgressSnapshot)[idKey]
      if (key != null) put(String(key), item)
    })
    return result
  }

  if (value && typeof value === 'object') {
    Object.entries(value as Record<string, unknown>).forEach(([key, snapshot]) => put(key, snapshot))
  }
  return result
}

export async function loadHomeTodos(): Promise<HomeTodoPayload> {
  return HomeTodoPayloadSchema.parse(await mobileApiClient.json('/api/ai/home-todos'))
}

export async function loadLearningStats(): Promise<LearningStatsPayload> {
  return LearningStatsPayloadSchema.parse(await mobileApiClient.json('/api/ai/learning-stats?days=7'))
}

export async function loadLearnerProfile(): Promise<Record<string, unknown>> {
  return mobileApiClient.json('/api/ai/learner-profile?view=stats')
}

export async function loadBooks(search = ''): Promise<MobileBook[]> {
  const payload = await mobileApiClient.json<{ books?: unknown[] }>(`/api/books${query({ search })}`)
  return parseArray(MobileBookSchema, payload.books)
}

export async function loadMyBookIds(): Promise<string[]> {
  const payload = await mobileApiClient.json<{ book_ids?: unknown[] }>('/api/books/my')
  return Array.isArray(payload.book_ids) ? payload.book_ids.map(String) : []
}

export async function loadBookProgressMap(): Promise<Record<string, ProgressSnapshot>> {
  const payload = await mobileApiClient.json<{ progress?: unknown }>('/api/books/progress')
  return normalizeProgressMap(payload.progress, 'book_id')
}

export async function addMyBook(bookId: string) {
  return mobileApiClient.json('/api/books/my', {
    method: 'POST',
    body: JSON.stringify({ book_id: bookId }),
  })
}

export async function loadChapters(bookId: string): Promise<MobileChapter[]> {
  const payload = await mobileApiClient.json<{ chapters?: unknown[] }>(`/api/books/${bookId}/chapters`)
  return parseArray(MobileChapterSchema, payload.chapters)
}

export async function loadChapterProgressMap(bookId: string): Promise<Record<string, ProgressSnapshot>> {
  const payload = await mobileApiClient.json<{ chapter_progress?: unknown; progress?: unknown }>(
    `/api/books/${bookId}/chapters/progress`,
  )
  return normalizeProgressMap(payload.chapter_progress ?? payload.progress, 'chapter_id')
}

export async function loadChapterWords(bookId: string, chapterId?: string | number | null): Promise<MobileWord[]> {
  const path = chapterId == null
    ? `/api/books/word-list${query({ scope: 'book', book_id: bookId })}`
    : `/api/books/${bookId}/chapters/${chapterId}`
  const payload = await mobileApiClient.json<{ words?: unknown[]; chapter?: { words?: unknown[] } }>(path)
  return parseArray(MobileWordSchema, payload.words ?? payload.chapter?.words)
}

export async function searchWords(term: string): Promise<MobileWord[]> {
  const payload = await mobileApiClient.json<{ results?: unknown[]; words?: unknown[] }>(
    `/api/books/search${query({ q: term, limit: 20 })}`,
  )
  return parseArray(MobileWordSchema, payload.results ?? payload.words)
}

export async function loadWordDetails(word: string): Promise<Record<string, unknown>> {
  return mobileApiClient.json(`/api/books/word-details${query({ word })}`)
}

export async function setFavorite(word: string, enabled: boolean) {
  return mobileApiClient.json('/api/books/favorites', {
    method: enabled ? 'POST' : 'DELETE',
    body: JSON.stringify({ word }),
  })
}

export async function setFamiliar(word: string, enabled: boolean) {
  return mobileApiClient.json('/api/books/familiar', {
    method: enabled ? 'POST' : 'DELETE',
    body: JSON.stringify({ word }),
  })
}

export async function saveWordNote(word: string, note: string) {
  return mobileApiClient.json('/api/books/word-details/note', {
    method: 'PUT',
    body: JSON.stringify({ word, note }),
  })
}

export async function createCustomBook(title: string, words: MobileWord[] | WrongWord[]) {
  return mobileApiClient.json('/api/books/custom-books', {
    method: 'POST',
    body: JSON.stringify({
      title,
      words: words.map(item => ({
        word: item.word,
        definition: item.definition,
        phonetic: item.phonetic,
        pos: item.pos,
      })),
    }),
  })
}

export async function loadWrongWords(search = ''): Promise<WrongWord[]> {
  const payload = await mobileApiClient.json<{ words?: unknown[] }>(
    `/api/ai/wrong-words${query({ details: 'compact', search })}`,
  )
  return parseArray(WrongWordSchema, payload.words)
}

export async function clearWrongWord(word: string) {
  return mobileApiClient.json(`/api/ai/wrong-words/${encodeURIComponent(word)}`, { method: 'DELETE' })
}

export async function syncWrongWord(word: WrongWord) {
  return mobileApiClient.json('/api/ai/wrong-words/sync', {
    method: 'POST',
    body: JSON.stringify({ words: [word] }),
  })
}

export async function syncQuickMemory(record: Record<string, unknown>) {
  return mobileApiClient.json('/api/ai/quick-memory/sync', {
    method: 'POST',
    body: JSON.stringify({ records: [record] }),
  })
}

export async function savePracticeProgress(params: {
  bookId: string
  chapterId?: string | number | null
  correctCount: number
  currentIndex: number
  mode: PracticeMode
  queueWords: string[]
  answeredWords: string[]
  wordsLearned: number
  wrongCount: number
  isCompleted: boolean
}) {
  if (params.chapterId == null) return null
  const body = {
    mode: params.mode,
    current_index: params.currentIndex,
    words_learned: params.wordsLearned,
    correct_count: params.correctCount,
    wrong_count: params.wrongCount,
    is_completed: params.isCompleted,
    answered_words: params.answeredWords,
    queue_words: params.queueWords,
  }
  await mobileApiClient.json(`/api/books/${params.bookId}/chapters/${params.chapterId}/progress`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return mobileApiClient.json(`/api/books/${params.bookId}/chapters/${params.chapterId}/mode-progress`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function logPracticeSession(params: {
  bookId?: string | null
  chapterId?: string | number | null
  correctCount: number
  durationSeconds: number
  mode: PracticeMode
  wordsStudied: number
  wrongCount: number
}) {
  return mobileApiClient.json('/api/ai/log-session', {
    method: 'POST',
    body: JSON.stringify({
      mode: params.mode,
      bookId: params.bookId,
      chapterId: params.chapterId,
      correctCount: params.correctCount,
      durationSeconds: Math.max(1, params.durationSeconds),
      endedAt: Date.now(),
      wordsStudied: params.wordsStudied,
      wrongCount: params.wrongCount,
    }),
  })
}

export async function loadExamPapers(): Promise<ExamPaperSummary[]> {
  const payload = await mobileApiClient.json<{ items?: unknown[] }>('/api/exams')
  return parseArray(ExamPaperSummarySchema, payload.items)
}

export async function loadExamPaper(paperId: number): Promise<ExamPaperDetail> {
  const payload = await mobileApiClient.json<{ paper?: unknown }>(`/api/exams/${paperId}`)
  return ExamPaperDetailSchema.parse(payload.paper)
}

export async function createExamAttempt(paperId: number): Promise<number> {
  const payload = await mobileApiClient.json<{ attempt?: { id?: number } }>(`/api/exams/${paperId}/attempts`, {
    method: 'POST',
  })
  return Number(payload.attempt?.id)
}

export async function saveExamResponses(attemptId: number, responses: ExamResponseDraft[]) {
  return mobileApiClient.json(`/api/exam-attempts/${attemptId}/responses`, {
    method: 'PATCH',
    body: JSON.stringify({ responses }),
  })
}

export async function submitExamAttempt(attemptId: number) {
  return mobileApiClient.json(`/api/exam-attempts/${attemptId}/submit`, { method: 'POST' })
}

export async function loadJournalSummaries(): Promise<JournalSummary[]> {
  const payload = await mobileApiClient.json<{ summaries?: unknown[]; items?: unknown[] }>('/api/notes/summaries')
  return parseArray(JournalSummarySchema, payload.summaries ?? payload.items)
}

export async function loadLearningNotes(): Promise<LearningNote[]> {
  const payload = await mobileApiClient.json<{ notes?: unknown[]; items?: unknown[] }>('/api/notes?limit=20')
  return parseArray(LearningNoteSchema, payload.notes ?? payload.items)
}

export async function startSummaryJob(date: string) {
  return mobileApiClient.json('/api/notes/summaries/generate-jobs', {
    method: 'POST',
    body: JSON.stringify({ date }),
  })
}

export async function askAi(message: string) {
  return mobileApiClient.json<{ answer?: string; response?: string; message?: string }>('/api/ai/ask', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}
