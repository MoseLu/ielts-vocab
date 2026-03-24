// ── Utility Functions ────────────────────────────────────────────────────────────

import type { z } from 'zod'

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

// ── Secure API fetch — HttpOnly cookie mode ───────────────────────────────────
// • Always sends credentials (cookies) so the HttpOnly access_token is included
// • On 401, attempts one silent token refresh via POST /api/auth/refresh
// • If refresh succeeds, retries the original request once
// • If refresh fails, fires 'auth:session-expired' so AuthContext can clear state

let _refreshing: Promise<void> | null = null

async function _attemptRefresh(): Promise<void> {
  // Deduplicate: if a refresh is already in flight, wait for it
  if (_refreshing) return _refreshing

  _refreshing = (async () => {
    // Try up to 2 times to handle transient network drops (e.g. natapp tunnel
    // blip) without immediately treating them as token expiry.
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const r = await fetch('/api/auth/refresh', {
          method: 'POST',
          credentials: 'include',
        })
        if (r.ok) return
        // A real 401 means the token is genuinely expired — don't retry
        if (r.status === 401) throw new Error('auth_failed')
        // Any other HTTP error: fall through to retry
        throw new Error(`refresh_http_${r.status}`)
      } catch (err) {
        const isAuthFailure = err instanceof Error && err.message === 'auth_failed'
        if (isAuthFailure || attempt === 1) throw err
        // Wait 1.5 s then retry (covers brief tunnel reconnection)
        await new Promise(res => setTimeout(res, 1500))
      }
    }
  })().finally(() => { _refreshing = null })

  return _refreshing
}

function _buildHeaders(options: RequestInit): Record<string, string> {
  const existing: Record<string, string> =
    options.headers instanceof Headers
      ? Object.fromEntries(options.headers.entries())
      : Array.isArray(options.headers)
      ? Object.fromEntries(options.headers)
      : (options.headers as Record<string, string>) || {}
  return { 'Content-Type': 'application/json', ...existing }
}

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = _buildHeaders(options)
  const init: RequestInit = { ...options, headers, credentials: 'include' }

  const response = await fetch(url, init)

  // Silent token refresh on 401 (but not for auth endpoints themselves)
  if (
    response.status === 401 &&
    !url.includes('/api/auth/login') &&
    !url.includes('/api/auth/register') &&
    !url.includes('/api/auth/refresh')
  ) {
    try {
      await _attemptRefresh()
      // Retry original request — cookies now carry the new access_token
      const retry = await fetch(url, init)
      if (!retry.ok) {
        const err = await retry.json().catch(() => ({ error: '请求失败，请稍后重试' }))
        throw new Error(err.error || '请求失败，请稍后重试')
      }
      return retry.json() as Promise<T>
    } catch {
      // Refresh failed — session truly expired
      window.dispatchEvent(new CustomEvent('auth:session-expired'))
      throw new Error('登录已过期，请重新登录')
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: '请求失败，请稍后重试' }))
    throw new Error(error.error || '请求失败，请稍后重试')
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
export { useForm } from './useForm'
