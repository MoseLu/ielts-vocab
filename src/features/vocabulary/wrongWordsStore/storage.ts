import { STORAGE_KEYS } from '../../../constants'
import { getStorageItem, setStorageItem } from '../../../lib'
import {
  type ScopedUserId,
  type WrongWordInput,
  type WrongWordsResponse,
  type WrongWordRecord,
} from './types'
import { mergeWrongWordLists, normalizeScopedUserId } from './core'

export function readAuthUserIdFromStorage(): string | number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { id?: unknown }
    return normalizeScopedUserId(parsed.id)
  } catch {
    return null
  }
}

function resolveScopedUserId(userId?: ScopedUserId): string | number | null {
  return normalizeScopedUserId(userId) ?? readAuthUserIdFromStorage()
}

function buildUserScopedStorageKey(baseKey: string, userId?: ScopedUserId): string {
  const resolvedUserId = resolveScopedUserId(userId)
  return resolvedUserId == null ? baseKey : `${baseKey}:user:${String(resolvedUserId)}`
}

export function getWrongWordsStorageKey(userId?: ScopedUserId): string {
  return buildUserScopedStorageKey(STORAGE_KEYS.WRONG_WORDS, userId)
}

export function getWrongWordsProgressStorageKey(userId?: ScopedUserId): string {
  return buildUserScopedStorageKey(STORAGE_KEYS.WRONG_WORDS_PROGRESS, userId)
}

export function readWrongWordsFromStorage(userId?: ScopedUserId): WrongWordRecord[] {
  const stored = getStorageItem<WrongWordInput[]>(getWrongWordsStorageKey(userId), [])
  return Array.isArray(stored) ? mergeWrongWordLists(stored) : []
}

export function writeWrongWordsToStorage(words: WrongWordInput[], userId?: ScopedUserId): WrongWordRecord[] {
  const normalized = mergeWrongWordLists(words)
  setStorageItem(getWrongWordsStorageKey(userId), normalized)
  return normalized
}

function readUserId(user: unknown): string | number | null {
  if (!user || typeof user !== 'object' || !('id' in user)) {
    return null
  }

  return normalizeScopedUserId((user as { id?: unknown }).id)
}

export async function loadWrongWords({
  user,
  fetchRemote,
}: {
  user?: unknown
  fetchRemote?: () => Promise<WrongWordsResponse>
}): Promise<WrongWordRecord[]> {
  const userId = readUserId(user)
  const localWords = readWrongWordsFromStorage(userId)

  if (!user || !fetchRemote) {
    return localWords
  }

  try {
    const response = await fetchRemote()
    const remoteWords = Array.isArray(response.words) ? response.words : []
    const merged = mergeWrongWordLists(remoteWords, localWords)
    writeWrongWordsToStorage(merged, userId)
    return merged
  } catch {
    return localWords
  }
}
