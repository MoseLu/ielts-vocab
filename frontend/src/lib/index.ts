// ── Utility Functions ────────────────────────────────────────────────────────────

const RAW_API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? ''
let _apiBaseOverride: string | null = null

// LocalStorage helpers with type safety
export function getStorageItem<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : defaultValue
  } catch {
    return defaultValue
  }
}

export function setStorageItem<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value))
}

export function removeStorageItem(key: string): void {
  localStorage.removeItem(key)
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

// ── Secure API fetch — HttpOnly cookie mode ───────────────────────────────────
// • Always sends credentials (cookies) so the HttpOnly access_token is included
// • On 401, attempts one silent token refresh via POST /api/auth/refresh
// • If refresh succeeds, retries the original request once
// • If refresh fails with 401, fires 'auth:session-expired' so AuthContext can clear state
// • If refresh fails because the backend is temporarily unavailable, keeps local session state

let _refreshing: Promise<void> | null = null
let _authSessionActive = false
const AUTH_REFRESH_AUTH_FAILED = 'auth_failed'
const AUTH_REFRESH_TEMPORARILY_UNAVAILABLE = 'temporarily_unavailable'

export function setAuthSessionActive(active: boolean): void {
  _authSessionActive = active
}

async function _attemptRefresh(): Promise<void> {
  // Deduplicate: if a refresh is already in flight, wait for it.
  // The promise is stored BEFORE any await to prevent race conditions
  // where two concurrent 401s could each start their own refresh.
  if (_refreshing) return _refreshing

  // Create promise first, store it synchronously, then execute.
  // This ordering ensures any concurrent caller sees _refreshing already set.
  let resolveRefreshing: () => void
  let rejectRefreshing: (reason?: unknown) => void
  const promise = new Promise<void>((resolve, reject) => {
    resolveRefreshing = resolve
    rejectRefreshing = reject
  })

  _refreshing = promise

  // Immediately capture resolveRefreshing (synchronous assignment above)
  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const resolve = resolveRefreshing!
  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const reject = rejectRefreshing!

  // Run refresh logic, store the result, then resolve the outer promise.
  // This allows all concurrent callers to wait on the same promise.
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
  // Try up to 2 times to handle transient network drops (e.g. natapp tunnel
  // blip) without immediately treating them as token expiry.
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(buildApiUrl('/api/auth/refresh'), {
        method: 'POST',
        credentials: 'include',
        signal: AbortSignal.timeout(10_000),
      })
      if (r.ok) return
      // A real 401 means the token is genuinely expired — don't retry
      if (r.status === 401) throw new Error(AUTH_REFRESH_AUTH_FAILED)
      // Any other HTTP error: fall through to retry
      throw new Error(`refresh_http_${r.status}`)
    } catch (err) {
      const isAuthFailure = err instanceof Error && err.message === AUTH_REFRESH_AUTH_FAILED
      if (isAuthFailure || attempt === 1) throw err
      // Wait 1.5 s then retry (covers brief tunnel reconnection)
      await new Promise(res => setTimeout(res, 1500))
    }
  }
}

interface ApiRequestOptions extends RequestInit {
  skipAuthRefresh?: boolean
}

function _shouldRefreshResponse(url: string, response: Response, skipAuthRefresh: boolean): boolean {
  return (
    !skipAuthRefresh &&
    _authSessionActive &&
    response.status === 401 &&
    !url.includes('/api/auth/login') &&
    !url.includes('/api/auth/register') &&
    !url.includes('/api/auth/refresh') &&
    !url.includes('/api/auth/logout')
  )
}

async function _performApiRequest(url: string, options: RequestInit): Promise<Response> {
  const headers = _buildHeaders(options)
  const timeoutSignal = AbortSignal.timeout(30_000)
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeoutSignal])
    : timeoutSignal
  const init: RequestInit = { ...options, headers, credentials: 'include', signal }
  return fetch(url, init)
}

export async function apiRequest(
  url: string,
  options: ApiRequestOptions = {},
): Promise<Response> {
  const requestUrl = buildApiUrl(url)
  const { skipAuthRefresh = false, ...requestOptions } = options
  const response = await _performApiRequest(requestUrl, requestOptions)

  if (_shouldRefreshResponse(requestUrl, response, skipAuthRefresh)) {
    const refreshResult = await refreshAuthSession()
    if (refreshResult === 'success') {
      const retry = await _performApiRequest(requestUrl, requestOptions)
      if (retry.status === 401) {
        if (_authSessionActive) {
          window.dispatchEvent(new CustomEvent('auth:session-expired'))
        }
        throw new Error('登录已过期，请重新登录')
      }
      return retry
    }

    if (refreshResult === 'auth_failed') {
      if (_authSessionActive) {
        window.dispatchEvent(new CustomEvent('auth:session-expired'))
      }
      throw new Error('登录已过期，请重新登录')
    }

    throw new Error('服务暂时不可用，请稍后重试')
  }

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
  options: RequestInit = {}
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

// Date helpers
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

export function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`
}

// Array helpers
export function shuffleArray<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export function chunkArray<T>(arr: T[], size: number): T[][] {
  const chunks: T[][] = []
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size))
  }
  return chunks
}

// Number helpers
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export function percentage(value: number, total: number): number {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

// String helpers
export function truncate(str: string, length: number): string {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

// ── Re-export schemas & validation ─────────────────────────────────────────────
export * from './schemas'
export * from './validation'
export * from './bookPractice'
export { useForm } from './useForm'
