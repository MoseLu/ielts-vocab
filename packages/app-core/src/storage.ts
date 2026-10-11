import type { PracticeMode } from './mobileSchemas'
import type { PracticeProgressSnapshot } from './practiceEngine'

export interface AppStorage {
  getItem(key: string): Promise<string | null>
  removeItem(key: string): Promise<void>
  setItem(key: string, value: string): Promise<void>
}

export interface SecureTokenStorage {
  getAccessToken(): Promise<string | null>
  getRefreshToken(): Promise<string | null>
  setTokens(tokens: { accessToken: string; refreshToken: string }): Promise<void>
  clearTokens(): Promise<void>
}

export const CORE_STORAGE_KEYS = {
  appSettings: 'mobile_app_settings',
  authUser: 'mobile_auth_user',
  pendingSync: 'mobile_pending_sync',
  practiceProgress: 'mobile_practice_progress',
  wrongWordReview: 'mobile_wrong_word_review',
  wrongWords: 'mobile_wrong_words',
} as const

export type PracticeProgressScope = {
  bookId: string
  chapterId?: string | number | null
}

export type StoredPracticeProgressSnapshot = PracticeProgressSnapshot & {
  bookId: string
  chapterId?: string | number | null
  mode: PracticeMode
  updatedAt: string
}

export function scopedStorageKey(baseKey: string, userId: string | number | null | undefined) {
  if (userId === null || userId === undefined || userId === '') return baseKey
  return `${baseKey}:user:${String(userId)}`
}

export async function readJson<T>(storage: AppStorage, key: string, fallback: T): Promise<T> {
  const raw = await storage.getItem(key)
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export async function writeJson<T>(storage: AppStorage, key: string, value: T): Promise<void> {
  await storage.setItem(key, JSON.stringify(value))
}

export function practiceProgressStorageKey(scope: PracticeProgressScope): string {
  const bookKey = scope.bookId.trim()
  const chapterKey = scope.chapterId == null ? 'book' : `chapter:${String(scope.chapterId)}`
  return `${bookKey}:${chapterKey}`
}

export function isUnfinishedPracticeProgressSnapshot(
  snapshot: Pick<PracticeProgressSnapshot, 'currentIndex' | 'isCompleted' | 'queueWords'> | null | undefined,
): boolean {
  if (!snapshot || snapshot.isCompleted) return false
  return snapshot.queueWords.length > 0 && snapshot.currentIndex > 0 && snapshot.currentIndex < snapshot.queueWords.length
}

export async function readPracticeProgressSnapshot(
  storage: AppStorage,
  scope: PracticeProgressScope,
): Promise<StoredPracticeProgressSnapshot | null> {
  const snapshots = await readJson<Record<string, StoredPracticeProgressSnapshot>>(
    storage,
    CORE_STORAGE_KEYS.practiceProgress,
    {},
  )
  return snapshots[practiceProgressStorageKey(scope)] ?? null
}

export async function writePracticeProgressSnapshot(
  storage: AppStorage,
  scope: PracticeProgressScope,
  snapshot: Omit<StoredPracticeProgressSnapshot, 'bookId' | 'chapterId' | 'updatedAt'>,
  now = new Date(),
): Promise<StoredPracticeProgressSnapshot> {
  const snapshots = await readJson<Record<string, StoredPracticeProgressSnapshot>>(
    storage,
    CORE_STORAGE_KEYS.practiceProgress,
    {},
  )
  const nextSnapshot: StoredPracticeProgressSnapshot = {
    ...snapshot,
    bookId: scope.bookId,
    chapterId: scope.chapterId ?? null,
    updatedAt: now.toISOString(),
  }
  snapshots[practiceProgressStorageKey(scope)] = nextSnapshot
  await writeJson(storage, CORE_STORAGE_KEYS.practiceProgress, snapshots)
  return nextSnapshot
}

export async function clearPracticeProgressSnapshot(
  storage: AppStorage,
  scope: PracticeProgressScope,
): Promise<void> {
  const snapshots = await readJson<Record<string, StoredPracticeProgressSnapshot>>(
    storage,
    CORE_STORAGE_KEYS.practiceProgress,
    {},
  )
  delete snapshots[practiceProgressStorageKey(scope)]
  await writeJson(storage, CORE_STORAGE_KEYS.practiceProgress, snapshots)
}

export function createMemoryStorage(initial: Record<string, string> = {}): AppStorage {
  const data = new Map(Object.entries(initial))
  return {
    async getItem(key) {
      return data.get(key) ?? null
    },
    async removeItem(key) {
      data.delete(key)
    },
    async setItem(key, value) {
      data.set(key, value)
    },
  }
}

export function createMemoryTokenStorage(): SecureTokenStorage {
  let accessToken: string | null = null
  let refreshToken: string | null = null
  return {
    async clearTokens() {
      accessToken = null
      refreshToken = null
    },
    async getAccessToken() {
      return accessToken
    },
    async getRefreshToken() {
      return refreshToken
    },
    async setTokens(tokens) {
      accessToken = tokens.accessToken
      refreshToken = tokens.refreshToken
    },
  }
}
