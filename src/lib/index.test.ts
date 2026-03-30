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
})
