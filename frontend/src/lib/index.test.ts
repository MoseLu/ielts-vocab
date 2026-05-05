import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  __resetErrorReportingForTests,
  __setErrorReportingEnabledForTests,
} from './errorReporting'
import {
  __setApiBaseOverrideForTests,
  apiFetch,
  apiRequest,
  buildApiUrl,
  setAuthAccessExpiry,
  setAuthSessionActive,
} from './index'

describe('api helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setAuthSessionActive(true)
    setAuthAccessExpiry(null)
    __setApiBaseOverrideForTests(null)
    __resetErrorReportingForTests()
    __setErrorReportingEnabledForTests(false)
  })

  afterEach(() => {
    setAuthAccessExpiry(null)
    __setApiBaseOverrideForTests(null)
    __resetErrorReportingForTests()
  })

  it('builds request urls from the configured api base', () => {
    __setApiBaseOverrideForTests('https://api.example.com/base/')

    expect(buildApiUrl('/api/books/my')).toBe('https://api.example.com/base/api/books/my')
    expect(buildApiUrl('https://cdn.example.com/file.mp3')).toBe('https://cdn.example.com/file.mp3')
  })

  it('does not retry the original request when token refresh fails', async () => {
    const dispatchEventSpy = vi.spyOn(window, 'dispatchEvent')

    vi.mocked(global.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'unauthorized' }), { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'auth failed' }), { status: 401 }))

    await expect(apiFetch('/api/books/my')).rejects.toThrow()

    expect(global.fetch).toHaveBeenCalledTimes(2)
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      '/api/books/my',
      expect.objectContaining({ credentials: 'include' }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      '/api/auth/refresh',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(dispatchEventSpy).toHaveBeenCalledWith(expect.any(CustomEvent))
  })

  it('refreshes an expired session before sending the protected request', async () => {
    setAuthAccessExpiry(0)
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ user: { id: 1 }, access_expires_in: 900 }), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    await apiFetch<{ ok: boolean }>('/api/books/my')

    expect(global.fetch).toHaveBeenCalledTimes(2)
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      '/api/auth/refresh',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      '/api/books/my',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('deduplicates the preflight refresh across concurrent protected requests', async () => {
    setAuthAccessExpiry(0)
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ user: { id: 1 }, access_expires_in: 900 }), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    await Promise.all([
      apiRequest('/api/books/my'),
      apiRequest('/api/books/progress'),
    ])

    expect(global.fetch).toHaveBeenCalledTimes(3)
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      '/api/auth/refresh',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      '/api/books/my',
      expect.objectContaining({ credentials: 'include' }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      3,
      '/api/books/progress',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('keeps the local session when token refresh is temporarily unavailable', async () => {
    const dispatchEventSpy = vi.spyOn(window, 'dispatchEvent')

    vi.mocked(global.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'unauthorized' }), { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'busy' }), { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'busy' }), { status: 503 }))

    await expect(apiFetch('/api/books/my')).rejects.toThrow('服务暂时不可用，请稍后重试')

    expect(global.fetch).toHaveBeenCalledTimes(3)
    expect(dispatchEventSpy).not.toHaveBeenCalled()
  })

  it('formats retry_after responses into readable lockout messages', async () => {
    setAuthSessionActive(false)
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: '登录尝试过于频繁，请 877 秒后再试',
          retry_after: 877,
        }),
        { status: 429 },
      ),
    )

    await expect(apiFetch('/api/auth/login', { method: 'POST' })).rejects.toThrow(
      '登录尝试过于频繁，请 14分37秒后再试',
    )
  })

  it('reports final failed responses without using apiRequest recursively', async () => {
    __setErrorReportingEnabledForTests(true)
    setAuthSessionActive(false)
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'down' }), { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 201 }))

    await expect(apiFetch('/api/books/my?token=secret')).rejects.toThrow('down')

    await vi.waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2))
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      '/api/ops/frontend-error-logs',
      expect.objectContaining({ keepalive: true, credentials: 'include' }),
    )
    const reportBody = JSON.parse(String(vi.mocked(global.fetch).mock.calls[1]?.[1]?.body))
    expect(reportBody.status_code).toBe(503)
    expect(reportBody.severity).toBe('error')
    expect(reportBody.request_url).not.toContain('secret')
  })

  it('does not force json content-type for FormData uploads', async () => {
    setAuthSessionActive(false)
    const formData = new FormData()
    formData.append('audio', new Blob(['test'], { type: 'audio/wav' }), 'sample.wav')

    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    await apiFetch<{ ok: boolean }>('/api/ai/speaking/evaluate', {
      method: 'POST',
      body: formData,
    })

    const headers = new Headers(vi.mocked(global.fetch).mock.calls[0]?.[1]?.headers)
    expect(headers.get('Content-Type')).toBeNull()
  })

  it('applies the configured api base to raw requests', async () => {
    __setApiBaseOverrideForTests('https://api.example.com')
    setAuthSessionActive(false)
    vi.mocked(global.fetch).mockResolvedValueOnce(new Response(null, { status: 204 }))

    await apiRequest('/api/auth/logout', { method: 'POST', skipAuthRefresh: true })

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/api/auth/logout',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      }),
    )
  })

  it('adds trace and idempotency headers when request metadata is provided', async () => {
    setAuthSessionActive(false)
    vi.mocked(global.fetch).mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    await apiRequest('/api/ai/practice/game/attempt', {
      method: 'POST',
      traceId: 'practice:trace-1234',
      idempotencyKey: 'practice:42:smart:book-1:abandon:meaning:1',
      body: JSON.stringify({ passed: true }),
    })

    const headers = new Headers(vi.mocked(global.fetch).mock.calls[0]?.[1]?.headers)
    expect(headers.get('X-Trace-Id')).toBe('practice:trace-1234')
    expect(headers.get('Idempotency-Key')).toBe('practice:42:smart:book-1:abandon:meaning:1')
  })

  it('preserves trace and idempotency headers across auth-refresh retries', async () => {
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'unauthorized' }), { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ user: { id: 1 }, access_expires_in: 900 }), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    await apiRequest('/api/books/progress', {
      method: 'POST',
      traceId: 'practice:retry-trace',
      idempotencyKey: 'practice:42:meaning:book-1:abandon:meaning:2',
      body: JSON.stringify({ book_id: 'book-1' }),
    })

    const firstHeaders = new Headers(vi.mocked(global.fetch).mock.calls[0]?.[1]?.headers)
    const refreshHeaders = new Headers(vi.mocked(global.fetch).mock.calls[1]?.[1]?.headers)
    const retryHeaders = new Headers(vi.mocked(global.fetch).mock.calls[2]?.[1]?.headers)
    expect(firstHeaders.get('X-Trace-Id')).toBe('practice:retry-trace')
    expect(firstHeaders.get('Idempotency-Key')).toBe('practice:42:meaning:book-1:abandon:meaning:2')
    expect(refreshHeaders.get('X-Trace-Id')).toBeNull()
    expect(refreshHeaders.get('Idempotency-Key')).toBeNull()
    expect(retryHeaders.get('X-Trace-Id')).toBe('practice:retry-trace')
    expect(retryHeaders.get('Idempotency-Key')).toBe('practice:42:meaning:book-1:abandon:meaning:2')
  })

  it('does not require request metadata on read requests', async () => {
    setAuthSessionActive(false)
    vi.mocked(global.fetch).mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    await apiRequest('/api/books/my')

    const headers = new Headers(vi.mocked(global.fetch).mock.calls[0]?.[1]?.headers)
    expect(headers.get('X-Trace-Id')).toBeNull()
    expect(headers.get('Idempotency-Key')).toBeNull()
  })
})
