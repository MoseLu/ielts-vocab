// Auth refresh + session state machine.
//
// Owns the cross-cutting auth session state and the refresh-on-401 logic that
// transport.ts composes. Keeping this isolated lets the transport file stay
// under the 500-line guardrail and lets the refresh policy be unit-tested
// without touching the full request pipeline.

import { STORAGE_KEYS } from '../../constants'
import { buildApiUrl } from './transport'

export const AUTH_REFRESH_AUTH_FAILED = 'auth_failed'
export const AUTH_REFRESH_TEMPORARILY_UNAVAILABLE = 'temporarily_unavailable'

export let _refreshing: Promise<void> | null = null
export let _authSessionActive = false
export let _authAccessExpiresAt: number | null = _readAuthAccessExpiry()

function _readAuthAccessExpiry(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT)
    const value = raw ? Number(raw) : NaN
    return Number.isFinite(value) ? value : null
  } catch {
    return null
  }
}

export function setAuthSessionActive(active: boolean): void {
  _authSessionActive = active
  if (!active) {
    setAuthAccessExpiry(null)
  }
}

export function setAuthAccessExpiry(expiresInSeconds: number | null | undefined): void {
  if (typeof expiresInSeconds !== 'number' || !Number.isFinite(expiresInSeconds)) {
    _authAccessExpiresAt = null
    try {
      localStorage.removeItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT)
    } catch {
      // ignore storage failures
    }
    return
  }

  _authAccessExpiresAt = Date.now() + Math.max(0, expiresInSeconds) * 1000
  try {
    localStorage.setItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT, String(_authAccessExpiresAt))
  } catch {
    // ignore storage failures
  }
}

export function _isAuthRoute(url: string): boolean {
  return (
    url.includes('/api/auth/login') ||
    url.includes('/api/auth/register') ||
    url.includes('/api/auth/refresh') ||
    url.includes('/api/auth/logout')
  )
}

async function _attemptRefresh(): Promise<void> {
  if (_refreshing) return _refreshing

  let resolveRefreshing: () => void
  let rejectRefreshing: (reason?: unknown) => void
  const promise = new Promise<void>((resolve, reject) => {
    resolveRefreshing = resolve
    rejectRefreshing = reject
  })

  _refreshing = promise

  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const resolve = resolveRefreshing!
  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const reject = rejectRefreshing!

  _doRefresh()
    .then(() => {
      resolve()
    })
    .catch(error => {
      reject(error)
    })
    .finally(() => {
      _refreshing = null
    })

  return promise
}

async function _doRefresh(): Promise<void> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(buildApiUrl('/api/auth/refresh'), {
        method: 'POST',
        credentials: 'include',
        signal: AbortSignal.timeout(10_000),
      })
      if (r.ok) {
        const payload = await r.json().catch(() => null)
        setAuthAccessExpiry(
          payload && typeof payload === 'object' && 'access_expires_in' in payload
            ? Number(payload.access_expires_in)
            : null,
        )
        return
      }
      if (r.status === 401) throw new Error(AUTH_REFRESH_AUTH_FAILED)
      throw new Error(`refresh_http_${r.status}`)
    } catch (err) {
      const isAuthFailure = err instanceof Error && err.message === AUTH_REFRESH_AUTH_FAILED
      if (isAuthFailure || attempt === 1) throw err
      await new Promise(res => setTimeout(res, 1500))
    }
  }
}

export async function refreshAuthSession(): Promise<
  'success' | 'auth_failed' | 'temporarily_unavailable'
> {
  try {
    await _attemptRefresh()
    return 'success'
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_REFRESH_AUTH_FAILED) {
      return 'auth_failed'
    }
    return AUTH_REFRESH_TEMPORARILY_UNAVAILABLE
  }
}

const AUTH_ACCESS_REFRESH_SKEW_MS = 5_000

export function _shouldPreemptivelyRefresh(url: string, skipAuthRefresh: boolean): boolean {
  return (
    !skipAuthRefresh &&
    _authSessionActive &&
    _authAccessExpiresAt !== null &&
    Date.now() >= (_authAccessExpiresAt - AUTH_ACCESS_REFRESH_SKEW_MS) &&
    _isAuthRoute(url) === false
  )
}
