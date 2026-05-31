import {
  CORE_STORAGE_KEYS,
  readJson,
  UserSchema,
  type AppStorage,
  type AppUser,
} from '@ielts-vocab/app-core'

type SessionRefreshResult = 'success' | 'auth_failed' | 'temporarily_unavailable'

type SessionApiClient = {
  json<T>(path: string): Promise<T>
  refreshSession(): Promise<SessionRefreshResult>
}

async function readCurrentUser(apiClient: SessionApiClient): Promise<AppUser | null> {
  const payload = await apiClient.json<{ user?: unknown }>('/api/auth/me')
  const parsedUser = UserSchema.safeParse(payload.user)
  return parsedUser.success ? parsedUser.data : null
}

export async function hydrateStoredSession(
  storage: AppStorage,
  apiClient: SessionApiClient,
): Promise<AppUser | null> {
  const cachedUser = await readJson<AppUser | null>(storage, CORE_STORAGE_KEYS.authUser, null)

  try {
    const currentUser = await readCurrentUser(apiClient)
    if (currentUser) return currentUser

    if (!cachedUser) return null
    const refreshResult = await apiClient.refreshSession()
    if (refreshResult === 'auth_failed') return null
    if (refreshResult === 'temporarily_unavailable') return cachedUser

    return (await readCurrentUser(apiClient)) ?? cachedUser
  } catch {
    return cachedUser
  }
}
