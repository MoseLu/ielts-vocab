import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  AUTH_REFRESH_AUTH_FAILED,
  refreshAuthSession,
  setAuthAccessExpiry,
  setAuthSessionActive,
} from './authRefresh'

const originalFetch = globalThis.fetch
const STORAGE_KEY = 'auth_access_expires_at'

beforeEach(() => {
  localStorage.removeItem(STORAGE_KEY)
  setAuthSessionActive(false)
})

afterEach(() => {
  globalThis.fetch = originalFetch
  localStorage.removeItem(STORAGE_KEY)
})

describe('setAuthSessionActive', () => {
  it('clears the stored access expiry when deactivated', () => {
    setAuthAccessExpiry(60)
    expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull()

    setAuthSessionActive(false)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
  })
})

describe('setAuthAccessExpiry', () => {
  it('writes an absolute timestamp to localStorage when given seconds', () => {
    const before = Date.now()
    setAuthAccessExpiry(60)
    const after = Date.now()
    const stored = Number(localStorage.getItem(STORAGE_KEY))
    expect(stored).toBeGreaterThanOrEqual(before + 60_000)
    expect(stored).toBeLessThanOrEqual(after + 60_000)
  })

  it('removes the stored timestamp on null or non-finite values', () => {
    setAuthAccessExpiry(60)
    expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull()

    setAuthAccessExpiry(null)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()

    setAuthAccessExpiry(60)
    setAuthAccessExpiry(Number.NaN)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
  })
})

describe('refreshAuthSession', () => {
  it('returns success when the refresh call returns 200 and sets the new expiry', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ access_expires_in: 120 }), { status: 200 }),
    )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await refreshAuthSession()
    expect(result).toBe('success')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      credentials: 'include',
    })
    expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull()
  })

  it('returns auth_failed when the refresh endpoint returns 401', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await refreshAuthSession()
    expect(result).toBe('auth_failed')
  })

  it('retries on a transient error and then surfaces temporarily_unavailable', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await refreshAuthSession()
    expect(result).toBe('temporarily_unavailable')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('reuses the in-flight refresh promise when called twice in parallel', async () => {
    let resolveFn: (v: Response) => void = () => {}
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>(resolve => {
            resolveFn = resolve
          }),
      )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const a = refreshAuthSession()
    const b = refreshAuthSession()

    expect(fetchMock).toHaveBeenCalledTimes(1)

    resolveFn(new Response(JSON.stringify({ access_expires_in: 30 }), { status: 200 }))

    const [aResult, bResult] = await Promise.all([a, b])
    expect(aResult).toBe('success')
    expect(bResult).toBe('success')
  })
})

describe('AUTH_REFRESH_AUTH_FAILED constant', () => {
  it('matches the canonical auth_failed token', () => {
    expect(AUTH_REFRESH_AUTH_FAILED).toBe('auth_failed')
  })
})
