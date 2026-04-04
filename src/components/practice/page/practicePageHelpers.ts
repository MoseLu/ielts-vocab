import type { PracticeMode, ProgressData, SmartDimension, Word } from '../types'
import { getWrongWordsProgressStorageKey, type WrongWordDimension } from '../../../features/vocabulary/wrongWordsStore'

export interface WrongWordsProgressData {
  current_index: number
  correct_count: number
  wrong_count: number
  is_completed: boolean
  round?: number
  queue_words?: string[]
  mode?: PracticeMode
  updatedAt?: string
}

export interface ReviewQueueContext {
  book_id: string
  book_title: string
  chapter_id: string
  chapter_title: string
  due_count: number
  upcoming_count: number
  total_count: number
  next_review: number
}

export interface ReviewQueueSummary {
  due_count: number
  upcoming_count: number
  returned_count: number
  review_window_days: number
  offset: number
  limit: number | null
  total_count: number
  has_more: boolean
  next_offset: number | null
  contexts?: ReviewQueueContext[]
  selected_context?: ReviewQueueContext | null
}

function hasCompleteListeningPresets(word: Word): boolean {
  return Array.isArray(word.listening_confusables) && word.listening_confusables.length >= 3
}

export function normalizeOptionWordKey(word?: string | null): string | null {
  const normalized = word?.trim().toLowerCase()
  return normalized ? normalized : null
}

export function filterVocabularyForMode(words: Word[], mode?: PracticeMode): Word[] {
  if (mode !== 'listening') return words
  return words.filter(hasCompleteListeningPresets)
}

export function readUserId(user: unknown): string | number | null {
  if (typeof user !== 'object' || user === null || !('id' in user)) {
    return null
  }

  const id = (user as { id?: unknown }).id
  return typeof id === 'string' || typeof id === 'number' ? id : null
}

export function resolveWrongWordDimensionForPractice(
  mode?: PracticeMode,
  smartDimension?: SmartDimension,
): WrongWordDimension {
  if (mode === 'quickmemory') return 'recognition'
  if (mode === 'listening') return 'listening'
  if (mode === 'dictation') return 'dictation'
  if (mode === 'meaning') return 'meaning'

  if (mode === 'smart') {
    if (smartDimension === 'listening') return 'listening'
    if (smartDimension === 'dictation') return 'dictation'
    return 'meaning'
  }

  return 'meaning'
}

export function readWrongWordsProgress(
  currentMode?: PracticeMode,
  userId?: string | number | null,
): WrongWordsProgressData | null {
  try {
    const stored = JSON.parse(localStorage.getItem(getWrongWordsProgressStorageKey(userId)) || '{}') as {
      _last?: WrongWordsProgressData
    }
    const snapshot = stored._last
    if (!snapshot) return null
    if (snapshot.mode && currentMode && snapshot.mode !== currentMode) return null

    return {
      current_index: Math.max(0, Number(snapshot.current_index) || 0),
      correct_count: Math.max(0, Number(snapshot.correct_count) || 0),
      wrong_count: Math.max(0, Number(snapshot.wrong_count) || 0),
      is_completed: Boolean(snapshot.is_completed),
      round: Math.max(1, Number(snapshot.round) || 1),
      queue_words: Array.isArray(snapshot.queue_words) ? snapshot.queue_words : undefined,
      mode: snapshot.mode,
      updatedAt: snapshot.updatedAt,
    }
  } catch {
    return null
  }
}

export function buildWrongWordsQueue(words: Word[], queueWords?: string[]): number[] | null {
  if (!queueWords?.length) return null

  const indexByWord = new Map<string, number>()
  words.forEach((word, index) => {
    indexByWord.set(word.word.trim().toLowerCase(), index)
  })

  const restoredQueue: number[] = []
  const seen = new Set<number>()

  for (const queuedWord of queueWords) {
    const index = indexByWord.get(queuedWord.trim().toLowerCase())
    if (index == null || seen.has(index)) continue
    restoredQueue.push(index)
    seen.add(index)
  }

  words.forEach((_word, index) => {
    if (seen.has(index)) return
    restoredQueue.push(index)
  })

  return restoredQueue.length ? restoredQueue : null
}

export function persistWrongWordsProgress(
  snapshot: WrongWordsProgressData,
  userId?: string | number | null,
) {
  localStorage.setItem(
    getWrongWordsProgressStorageKey(userId),
    JSON.stringify({
      _last: {
        ...snapshot,
        updatedAt: new Date().toISOString(),
      },
    }),
  )
}

export function createResetProgressState(
  queueLength: number,
  progress: ProgressData,
  chapterId: string | null,
  vocabLen: number,
) {
  const cap = vocabLen || 0
  const baseline = chapterId ? Math.min(progress.words_learned ?? cap, cap) : 0
  return {
    queueIndex: progress.is_completed ? 0 : Math.min(progress.current_index || 0, queueLength),
    correctCount: progress.is_completed ? 0 : (progress.correct_count || 0),
    wrongCount: progress.is_completed ? 0 : (progress.wrong_count || 0),
    wordsLearnedBaseline: baseline,
    answeredWords: progress.is_completed || !chapterId ? new Set<string>() : new Set(progress.answered_words ?? []),
  }
}
