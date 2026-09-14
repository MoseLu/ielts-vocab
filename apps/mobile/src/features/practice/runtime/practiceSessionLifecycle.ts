import {
  clearPracticeProgressSnapshot,
  isUnfinishedPracticeProgressSnapshot,
  readPracticeProgressSnapshot,
  restorePracticeQueueFromSnapshot,
  writePracticeProgressSnapshot,
  type AppStorage,
  type MobileWord,
  type PracticeMode,
  type PracticeProgressSnapshot,
  type PracticeQueueSource,
  type StoredPracticeProgressSnapshot,
} from '@ielts-vocab/app-core'
import type { ProgressSnapshot } from '../../../api/learnerApi'

type PracticeProgressBaseline = {
  correctCount: number
  wrongCount: number
}

export type PracticeSessionDependencies = {
  loadBookProgress(bookId: string): Promise<ProgressSnapshot | null>
  loadChapterProgress(bookId: string, chapterId: string | number): Promise<ProgressSnapshot | null>
  logPracticeSession(params: {
    bookId?: string | null
    chapterId?: string | number | null
    correctCount: number
    durationSeconds: number
    mode: PracticeMode
    wordsStudied: number
    wrongCount: number
  }): Promise<unknown>
  savePracticeProgress(params: {
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
  }): Promise<unknown>
  storage: AppStorage
}

export type HydratedPracticeSession = {
  chapterBaseline: PracticeProgressBaseline
  correctCount: number
  index: number
  queue: MobileWord[]
  resumed: boolean
  wrongCount: number
}

function numberValue(value: unknown): number {
  const number = Number(value)
  return Number.isFinite(number) ? Math.max(0, number) : 0
}

function normalizeProgressSnapshot(
  raw: ProgressSnapshot | null | undefined,
  params: { bookId: string; chapterId?: string | number | null; mode: PracticeMode },
): StoredPracticeProgressSnapshot | null {
  if (!raw) return null
  return {
    answeredWords: Array.isArray(raw.answered_words) ? raw.answered_words.map(String) : [],
    bookId: params.bookId,
    chapterId: params.chapterId ?? null,
    correctCount: numberValue(raw.correct_count),
    currentIndex: numberValue(raw.current_index),
    isCompleted: Boolean(raw.is_completed),
    mode: params.mode,
    queueWords: Array.isArray(raw.queue_words) ? raw.queue_words.map(String) : [],
    updatedAt: String(raw.updated_at || ''),
    wordsLearned: numberValue(raw.words_learned ?? raw.current_index),
    wrongCount: numberValue(raw.wrong_count),
  }
}

function snapshotUpdatedAt(snapshot: StoredPracticeProgressSnapshot | null): number {
  const timestamp = Date.parse(snapshot?.updatedAt || '')
  return Number.isNaN(timestamp) ? 0 : timestamp
}

function pickLatestSnapshot(
  local: StoredPracticeProgressSnapshot | null,
  remote: StoredPracticeProgressSnapshot | null,
): StoredPracticeProgressSnapshot | null {
  if (!local) return remote
  if (!remote) return local
  return snapshotUpdatedAt(remote) > snapshotUpdatedAt(local) ? remote : local
}

function scopeFor(bookId: string, chapterId?: string | number | null) {
  return { bookId, chapterId: chapterId ?? null }
}

export async function hydratePracticeSession(params: {
  bookId: string
  chapterId?: string | number | null
  dependencies: PracticeSessionDependencies
  mode: PracticeMode
  queueSource: PracticeQueueSource
  words: MobileWord[]
}): Promise<HydratedPracticeSession> {
  const fallback = {
    chapterBaseline: { correctCount: 0, wrongCount: 0 },
    correctCount: 0,
    index: 0,
    queue: params.words,
    resumed: false,
    wrongCount: 0,
  }
  if (!params.bookId || params.queueSource !== 'chapter') return fallback

  const scope = scopeFor(params.bookId, params.chapterId)
  const local = await readPracticeProgressSnapshot(params.dependencies.storage, scope)
  const remoteRaw = params.chapterId == null
    ? await params.dependencies.loadBookProgress(params.bookId).catch(() => null)
    : await params.dependencies.loadChapterProgress(params.bookId, params.chapterId).catch(() => null)
  const latest = pickLatestSnapshot(
    local,
    normalizeProgressSnapshot(remoteRaw, { bookId: params.bookId, chapterId: params.chapterId, mode: params.mode }),
  )
  if (!latest) return fallback

  if (!isUnfinishedPracticeProgressSnapshot(latest)) {
    return {
      ...fallback,
      chapterBaseline: params.chapterId == null
        ? fallback.chapterBaseline
        : { correctCount: latest.correctCount, wrongCount: latest.wrongCount },
    }
  }

  const queue = restorePracticeQueueFromSnapshot(params.words, latest)
  return {
    chapterBaseline: { correctCount: 0, wrongCount: 0 },
    correctCount: latest.correctCount,
    index: Math.min(latest.currentIndex, queue.length),
    queue,
    resumed: true,
    wrongCount: latest.wrongCount,
  }
}

export async function persistPracticeSessionProgress(params: {
  bookId: string
  chapterBaseline: PracticeProgressBaseline
  chapterId?: string | number | null
  dependencies: PracticeSessionDependencies
  mode: PracticeMode
  queueSource: PracticeQueueSource
  snapshot: PracticeProgressSnapshot
}): Promise<PracticeProgressSnapshot | null> {
  if (!params.bookId || params.queueSource !== 'chapter') return null
  const cumulativeSnapshot = {
    ...params.snapshot,
    correctCount: params.chapterBaseline.correctCount + params.snapshot.correctCount,
    wrongCount: params.chapterBaseline.wrongCount + params.snapshot.wrongCount,
  }
  await writePracticeProgressSnapshot(
    params.dependencies.storage,
    scopeFor(params.bookId, params.chapterId),
    { ...cumulativeSnapshot, mode: params.mode },
  )
  await params.dependencies.savePracticeProgress({
    bookId: params.bookId,
    chapterId: params.chapterId,
    correctCount: cumulativeSnapshot.correctCount,
    currentIndex: cumulativeSnapshot.currentIndex,
    mode: params.mode,
    queueWords: cumulativeSnapshot.queueWords,
    answeredWords: cumulativeSnapshot.answeredWords,
    wordsLearned: cumulativeSnapshot.wordsLearned,
    wrongCount: cumulativeSnapshot.wrongCount,
    isCompleted: cumulativeSnapshot.isCompleted,
  })
  return cumulativeSnapshot
}

export async function completePracticeSession(params: {
  bookId: string
  chapterId?: string | number | null
  dependencies: PracticeSessionDependencies
  durationSeconds: number
  mode: PracticeMode
  queueSource: PracticeQueueSource
  snapshot: PracticeProgressSnapshot
  wordCount: number
}): Promise<void> {
  if (params.bookId && params.queueSource === 'chapter') {
    await clearPracticeProgressSnapshot(params.dependencies.storage, scopeFor(params.bookId, params.chapterId))
  }
  await params.dependencies.logPracticeSession({
    bookId: params.bookId || null,
    chapterId: params.chapterId,
    correctCount: params.snapshot.correctCount,
    durationSeconds: Math.max(1, params.durationSeconds),
    mode: params.mode,
    wordsStudied: Math.max(1, params.wordCount, params.snapshot.wordsLearned, params.snapshot.currentIndex),
    wrongCount: params.snapshot.wrongCount,
  })
}
