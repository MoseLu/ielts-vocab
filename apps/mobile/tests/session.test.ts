import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { CORE_STORAGE_KEYS, createMemoryStorage, writeJson } from '@ielts-vocab/app-core'
import { apiBaseUrl, resolveMobileBaseUrls, speechBaseUrl } from '../src/config'
import { hydrateStoredSession } from '../src/state/sessionHydration'

const cachedUser = { id: 2, username: 'admin', email: '', is_admin: false }

describe('mobile config', () => {
  it('uses production gateway by default', () => {
    assert.equal(apiBaseUrl, 'https://axiomaticworld.com')
    assert.equal(speechBaseUrl, 'https://axiomaticworld.com')
  })

  it('uses the local wifi host for dev builds', () => {
    const urls = resolveMobileBaseUrls({
      devHost: '192.168.1.4',
      environment: 'dev',
    })

    assert.equal(urls.apiBaseUrl, 'http://192.168.1.4:8000')
    assert.equal(urls.speechBaseUrl, 'http://192.168.1.4:5001')
  })
})

describe('session hydration', () => {
  it('refreshes when optional /me returns an empty user for a cached session', async () => {
    const storage = createMemoryStorage()
    await writeJson(storage, CORE_STORAGE_KEYS.authUser, cachedUser)
    const calls: string[] = []
    const apiClient = {
      async json<T>(path: string): Promise<T> {
        calls.push(path)
        if (calls.length === 1) return { user: null } as T
        return { user: { ...cachedUser, username: 'admin-fresh' } } as T
      },
      async refreshSession() {
        calls.push('refresh')
        return 'success' as const
      },
    }

    const user = await hydrateStoredSession(storage, apiClient)

    assert.equal(user?.username, 'admin-fresh')
    assert.deepEqual(calls, ['/api/auth/me', 'refresh', '/api/auth/me'])
  })

  it('drops cached users only when refresh is explicitly rejected', async () => {
    const storage = createMemoryStorage()
    await writeJson(storage, CORE_STORAGE_KEYS.authUser, cachedUser)

    const user = await hydrateStoredSession(storage, {
      async json<T>() {
        return { user: null } as T
      },
      async refreshSession() {
        return 'auth_failed' as const
      },
    })

    assert.equal(user, null)
  })

  it('keeps cached users when session verification is temporarily unavailable', async () => {
    const storage = createMemoryStorage()
    await writeJson(storage, CORE_STORAGE_KEYS.authUser, cachedUser)

    const user = await hydrateStoredSession(storage, {
      async json<T>() {
        return { user: null } as T
      },
      async refreshSession() {
        return 'temporarily_unavailable' as const
      },
    })

    assert.deepEqual(user, cachedUser)
  })
})
