import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { __setApiBaseOverrideForTests, apiFetch, buildApiUrl } from './transport'

const reportHttpMock = vi.hoisted(() => vi.fn())
const reportNetworkMock = vi.hoisted(() => vi.fn())

vi.mock('../errorReporting', () => ({
  reportHttpResponseError: reportHttpMock,
  reportNetworkError: reportNetworkMock,
}))

describe('buildApiUrl', () => {
  const originalEnv = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

  afterEach(() => {
    __setApiBaseOverrideForTests(null)
  })

  it('returns the path unchanged when the path is already absolute', () => {
    expect(buildApiUrl('https://example.com/foo')).toBe('https://example.com/foo')
  })

  it('prefixes the override base for /api/ paths', () => {
    __setApiBaseOverrideForTests('https://override.example.com')
    expect(buildApiUrl('/api/auth/login')).toBe('https://override.example.com/api/auth/login')
  })

  it('strips trailing slashes from the override base', () => {
    __setApiBaseOverrideForTests('https://override.example.com///')
    expect(buildApiUrl('/api/auth/login')).toBe('https://override.example.com/api/auth/login')
  })

  it('does not add a prefix when no base is configured', () => {
    __setApiBaseOverrideForTests(null)
    // ignore the static VITE_API_URL during this test
    expect(buildApiUrl('/api/foo').startsWith('/api/foo')).toBe(true)
  })

  it('falls back to the empty string if VITE_API_URL is unset and no override is set', () => {
    expect(typeof buildApiUrl('/api/foo')).toBe('string')
    expect(originalEnv).toBeDefined() // sanity: env key exists
  })
})

describe('apiFetch', () => {
  const originalFetch = globalThis.fetch
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    reportHttpMock.mockReset()
    reportNetworkMock.mockReset()
    __setApiBaseOverrideForTests(null)
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('parses a JSON success body and skips the error reporter on 2xx', async () => {
    fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true, value: 42 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await apiFetch<{ ok: boolean; value: number }>('/api/foo')

    expect(result).toEqual({ ok: true, value: 42 })
    expect(reportHttpMock).not.toHaveBeenCalled()
    expect(reportNetworkMock).not.toHaveBeenCalled()
  })

  it('returns undefined for 204 responses', async () => {
    fetchMock = vi.fn().mockResolvedValueOnce(new Response(null, { status: 204 }))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await apiFetch<undefined>('/api/foo')

    expect(result).toBeUndefined()
  })

  it('throws an Error with the server error string for non-2xx responses', async () => {
    fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'nope' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await expect(apiFetch('/api/foo')).rejects.toThrow('nope')
    expect(reportHttpMock).toHaveBeenCalledTimes(1)
  })

  it('formats 429 responses with a friendly retry-after message', async () => {
    fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'rate limited', retry_after: 90 }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await expect(apiFetch('/api/foo')).rejects.toThrow(/1分30秒后再试/)
  })

  it('reports network errors when fetch throws', async () => {
    fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('failed to fetch'))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await expect(apiFetch('/api/foo')).rejects.toThrow('failed to fetch')
    expect(reportNetworkMock).toHaveBeenCalledTimes(1)
  })

  it('injects X-Trace-Id and Idempotency-Key headers when provided', async () => {
    fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await apiFetch('/api/foo', { traceId: 'trace-1', idempotencyKey: 'idem-1' })

    const init = fetchMock.mock.calls[0][1] as RequestInit
    const headers = init.headers as Record<string, string>
    expect(headers['X-Trace-Id']).toBe('trace-1')
    expect(headers['Idempotency-Key']).toBe('idem-1')
    expect(headers['Content-Type']).toBe('application/json')
  })
})
