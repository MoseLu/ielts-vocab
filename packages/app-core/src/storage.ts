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
  wrongWords: 'mobile_wrong_words',
} as const

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
