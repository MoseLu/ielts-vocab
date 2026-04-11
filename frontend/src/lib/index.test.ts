import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, setAuthSessionActive } from './index'

describe('apiFetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setAuthSessionActive(true)
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
})
