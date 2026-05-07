import { STORAGE_KEYS } from '../constants'
import { reportHttpResponseError, reportNetworkError } from './errorReporting'

const RAW_API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? ''
let _apiBaseOverride: string | null = null

let _refreshing: Promise<void> | null = null
let _authSessionActive = false
let _authAccessExpiresAt = _readAuthAccessExpiry()
const AUTH_REFRESH_AUTH_FAILED = 'auth_failed'
const AUTH_REFRESH_TEMPORARILY_UNAVAILABLE = 'temporarily_unavailable'
const AUTH_ACCESS_REFRESH_SKEW_MS = 5_000

export interface ApiRequestOptions extends RequestInit {
  skipAuthRefresh?: boolean
  timeoutMs?: number
  traceId?: string
  idempotencyKey?: string
}

export function buildApiUrl(path: string): string {
  const normalizedApiBase = (_apiBaseOverride ?? RAW_API_BASE).replace(/\/+$/, '')
  if (/^https?:\/\//i.test(path)) return path
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!normalizedApiBase) return normalizedPath
  if (normalizedPath.startsWith('/api/')) return `${normalizedApiBase}${normalizedPath}`
  return `${normalizedApiBase}${normalizedPath}`
}

export function __setApiBaseOverrideForTests(value: string | null): void {
  _apiBaseOverride = value?.trim() ? value.trim() : null
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
    localStorage.removeItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT)
    return
  }

  _authAccessExpiresAt = Date.now() + Math.max(0, expiresInSeconds) * 1000
  localStorage.setItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT, String(_authAccessExpiresAt))
}

function _readAuthAccessExpiry(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT)
    const value = raw ? Number(raw) : NaN
    return Number.isFinite(value) ? value : null
  } catch {
    return null
  }
}

function _isAuthRoute(url: string): boolean {
  return (
    url.includes('/api/auth/login') ||
    url.includes('/api/auth/register') ||
    url.includes('/api/auth/refresh') ||
    url.includes('/api/auth/logout')
  )
}

function _shouldPreemptivelyRefresh(url: string, skipAuthRefresh: boolean): boolean {
  return (
    !skipAuthRefresh &&
    _authSessionActive &&
    _authAccessExpiresAt !== null &&
    Date.now() >= (_authAccessExpiresAt - AUTH_ACCESS_REFRESH_SKEW_MS) &&
    !_isAuthRoute(url)
  )
}

function _throwForRefreshFailure(refreshResult: 'auth_failed' | 'temporarily_unavailable'): never {
  if (refreshResult === 'auth_failed') {
    if (_authSessionActive) {
      window.dispatchEvent(new CustomEvent('auth:session-expired'))
    }
    throw new Error('登录已过期，请重新登录')
  }

  throw new Error('服务暂时不可用，请稍后重试')
}

async function _ensureFreshSession(url: string, skipAuthRefresh: boolean): Promise<void> {
  if (!_shouldPreemptivelyRefresh(url, skipAuthRefresh)) {
    return
  }

  const refreshResult = await refreshAuthSession()
  if (refreshResult !== 'success') {
    _throwForRefreshFailure(refreshResult)
  }
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

function _headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (headers instanceof Headers) return Object.fromEntries(headers.entries())
  if (Array.isArray(headers)) return Object.fromEntries(headers)
  return (headers as Record<string, string>) || {}
}

function _withRequestMetadataHeaders(
  options: RequestInit,
  traceId?: string,
  idempotencyKey?: string,
): RequestInit {
  if (!traceId && !idempotencyKey) return options
  return {
    ...options,
    headers: {
      ..._headersToRecord(options.headers),
      ...(traceId ? { 'X-Trace-Id': traceId } : {}),
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
    },
  }
}

function _shouldRefreshResponse(url: string, response: Response, skipAuthRefresh: boolean): boolean {
  return (
    !skipAuthRefresh &&
    _authSessionActive &&
    response.status === 401 &&
    !_isAuthRoute(url)
  )
}

async function _performApiRequest(
  url: string,
  options: RequestInit,
  timeoutMs = 30_000,
): Promise<Response> {
  const headers = _buildHeaders(options)
  const timeoutSignal = AbortSignal.timeout(timeoutMs)
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeoutSignal])
    : timeoutSignal
  const init: RequestInit = { ...options, headers, credentials: 'include', signal }
  return fetch(url, init)
}

function _requestMethod(options: RequestInit): string {
  return (options.method || 'GET').toUpperCase()
}

function _reportHttpFailure(url: string, options: RequestInit, response: Response): void {
  if (response.ok) return
  reportHttpResponseError({
    requestUrl: url,
    method: _requestMethod(options),
    response,
  })
}

export async function apiRequest(
  url: string,
  options: ApiRequestOptions = {},
): Promise<Response> {
  const requestUrl = buildApiUrl(url)
  const {
    skipAuthRefresh = false,
    timeoutMs,
    traceId,
    idempotencyKey,
    ...rawRequestOptions
  } = options
  const requestOptions = _withRequestMetadataHeaders(rawRequestOptions, traceId, idempotencyKey)
  await _ensureFreshSession(requestUrl, skipAuthRefresh)
  let response: Response
  try {
    response = await _performApiRequest(requestUrl, requestOptions, timeoutMs)
  } catch (error) {
    reportNetworkError({
      requestUrl,
      method: _requestMethod(requestOptions),
      error,
    })
    throw error
  }

  if (_shouldRefreshResponse(requestUrl, response, skipAuthRefresh)) {
    const refreshResult = await refreshAuthSession()
    if (refreshResult === 'success') {
      let retry: Response
      try {
        retry = await _performApiRequest(requestUrl, requestOptions, timeoutMs)
      } catch (error) {
        reportNetworkError({
          requestUrl,
          method: _requestMethod(requestOptions),
          error,
        })
        throw error
      }
      if (retry.status === 401) {
        _reportHttpFailure(requestUrl, requestOptions, retry)
        if (_authSessionActive) {
          window.dispatchEvent(new CustomEvent('auth:session-expired'))
        }
        throw new Error('登录已过期，请重新登录')
      }
      _reportHttpFailure(requestUrl, requestOptions, retry)
      return retry
    }

    _reportHttpFailure(requestUrl, requestOptions, response)
    _throwForRefreshFailure(refreshResult)
  }

  _reportHttpFailure(requestUrl, requestOptions, response)
  return response
}

export async function refreshAuthSession(): Promise<'success' | 'auth_failed' | 'temporarily_unavailable'> {
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

function _buildHeaders(options: RequestInit): Record<string, string> {
  const existing: Record<string, string> =
    options.headers instanceof Headers
      ? Object.fromEntries(options.headers.entries())
      : Array.isArray(options.headers)
      ? Object.fromEntries(options.headers)
      : (options.headers as Record<string, string>) || {}
  const isFormDataBody = typeof FormData !== 'undefined' && options.body instanceof FormData
  if (isFormDataBody) return existing
  return { 'Content-Type': 'application/json', ...existing }
}

function _formatRetryAfter(seconds: number): string {
  const totalSeconds = Math.max(1, Math.ceil(seconds))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const remainingSeconds = totalSeconds % 60

  if (hours > 0) {
    if (minutes > 0) return `${hours}小时${minutes}分钟后再试`
    return `${hours}小时后再试`
  }
  if (minutes > 0) {
    if (remainingSeconds > 0) return `${minutes}分${remainingSeconds}秒后再试`
    return `${minutes}分钟后再试`
  }
  return `${remainingSeconds}秒后再试`
}

function _buildApiErrorMessage(
  status: number,
  payload: { error?: unknown; retry_after?: unknown },
): string {
  const fallback = typeof payload.error === 'string' && payload.error.trim()
    ? payload.error.trim()
    : '请求失败，请稍后重试'
  const retryAfter = Number(payload.retry_after)

  if (status === 429 && Number.isFinite(retryAfter) && retryAfter > 0) {
    const prefix = fallback.replace(/，?\s*请\s*\d+\s*秒后再试$/, '').trim() || '操作过于频繁'
    return `${prefix}，请 ${_formatRetryAfter(retryAfter)}`
  }

  return fallback
}

export async function apiFetch<T>(
  url: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const response = await apiRequest(url, options)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: '请求失败，请稍后重试' }))
    throw new Error(_buildApiErrorMessage(response.status, error))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
