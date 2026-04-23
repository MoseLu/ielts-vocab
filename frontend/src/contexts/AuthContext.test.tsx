import React from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { STORAGE_KEYS } from '../constants'
import { setAuthAccessExpiry } from '../lib'
import { AuthProvider, useAuth } from './AuthContext'

const apiFetchMock = vi.fn()
const apiRequestMock = vi.fn()
const showToastMock = vi.fn()

vi.mock('../lib', async () => {
  const actual = await vi.importActual<typeof import('../lib')>('../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    apiRequest: (...args: unknown[]) => apiRequestMock(...args),
  }
})

vi.mock('./ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

const wrapper = ({ children }: { children: React.ReactNode }) => <AuthProvider>{children}</AuthProvider>

const mockUser = {
  id: 1,
  username: 'alice',
  email: 'alice@example.com',
  avatar_url: null,
  is_admin: false,
  created_at: '2024-01-01T00:00:00Z',
}

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
    setAuthAccessExpiry(null)
    apiFetchMock.mockReset()
    apiRequestMock.mockReset()
    showToastMock.mockReset()
    vi.mocked(global.fetch).mockReset()
  })

  it('throws when used outside AuthProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider')

    consoleSpy.mockRestore()
  })
})

describe('AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    setAuthAccessExpiry(null)
    apiFetchMock.mockReset()
    apiRequestMock.mockReset()
    showToastMock.mockReset()
    vi.mocked(global.fetch).mockReset()
  })

  it('starts unauthenticated without a cached user', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 3000 })

    expect(apiFetchMock).not.toHaveBeenCalled()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('hydrates from cache and refreshes the user from /api/auth/me', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))
    apiFetchMock.mockResolvedValueOnce({ user: mockUser, access_expires_in: 3600 })

    const { result } = renderHook(() => useAuth(), { wrapper })

    expect(result.current.user?.username).toBe('alice')

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/auth/me')
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 3000 })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toMatchObject(mockUser)
    expect(Number(localStorage.getItem(STORAGE_KEYS.AUTH_ACCESS_EXPIRES_AT))).toBeGreaterThan(Date.now())
  })

  it('clears a cached user when /api/auth/me reports no active session', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))
    apiFetchMock.mockResolvedValueOnce({ user: null, authenticated: false, access_expires_in: 0 })
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'auth failed' }), { status: 401 }),
    )

    const { result } = renderHook(() => useAuth(), { wrapper })

    expect(result.current.user?.username).toBe('alice')

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_USER)).toBeNull()
    expect(showToastMock).not.toHaveBeenCalled()
  })

  it('restores the cached session when /api/auth/me needs a refresh token round-trip', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))
    apiFetchMock
      .mockResolvedValueOnce({ user: null, authenticated: false, access_expires_in: 0 })
      .mockResolvedValueOnce({ user: mockUser, access_expires_in: 3600 })
    vi.mocked(global.fetch).mockResolvedValueOnce(new Response(null, { status: 200 }))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 3000 })

    expect(vi.mocked(global.fetch)).toHaveBeenCalledWith('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      signal: expect.any(AbortSignal),
    })
    expect(apiFetchMock).toHaveBeenNthCalledWith(1, '/api/auth/me')
    expect(apiFetchMock).toHaveBeenNthCalledWith(2, '/api/auth/me')
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toMatchObject(mockUser)
  })

  it('keeps the cached session when refresh is temporarily unavailable', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))
    apiFetchMock.mockResolvedValueOnce({ user: null, authenticated: false, access_expires_in: 0 })
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'temporarily unavailable' }), { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'temporarily unavailable' }), { status: 503 }))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 3000 })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toMatchObject(mockUser)
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_USER)).not.toBeNull()
  })

  it('clears the session when the refresh event is fired', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))
    apiFetchMock.mockResolvedValueOnce({ user: mockUser, access_expires_in: 3600 })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })

    act(() => {
      window.dispatchEvent(new CustomEvent('auth:session-expired'))
    })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(false)
    })

    expect(localStorage.getItem(STORAGE_KEYS.AUTH_USER)).toBeNull()
    expect(showToastMock).toHaveBeenCalledTimes(1)
  })

  it('logs in and persists the returned user only', async () => {
    apiFetchMock.mockResolvedValueOnce({ user: mockUser, access_expires_in: 3600 })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await act(async () => {
      await result.current.login('alice@example.com', 'password123')
    })

    expect(apiFetchMock).toHaveBeenLastCalledWith('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: 'alice@example.com', password: 'password123' }),
    })
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toMatchObject(mockUser)
    expect(JSON.parse(localStorage.getItem(STORAGE_KEYS.AUTH_USER) ?? 'null')).toMatchObject(mockUser)
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)).toBeNull()
  })

  it('rejects invalid login responses', async () => {
    apiFetchMock.mockResolvedValueOnce({ user: { bad: 'shape' } })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.login('alice@example.com', 'password123')
      }),
    ).rejects.toThrow()
  })

  it('logs out through the API and clears persisted user state', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))
    localStorage.setItem('my_books', JSON.stringify(['book-1']))
    apiFetchMock.mockResolvedValueOnce({ user: mockUser, access_expires_in: 3600 })
    apiRequestMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })

    await act(async () => {
      await result.current.logout()
    })

    expect(apiRequestMock).toHaveBeenLastCalledWith('/api/auth/logout', {
      method: 'POST',
      skipAuthRefresh: true,
    })
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_USER)).toBeNull()
    expect(localStorage.getItem('my_books')).toBeNull()
  })

  it('clears local auth state before the logout request resolves', async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify(mockUser))

    let resolveLogout: (() => void) | null = null
    apiFetchMock.mockResolvedValueOnce({ user: mockUser, access_expires_in: 3600 })
    apiRequestMock.mockImplementationOnce(
      () =>
        new Promise(resolve => {
          resolveLogout = () => resolve(new Response(null, { status: 204 }))
        }),
    )

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })

    act(() => {
      void result.current.logout()
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_USER)).toBeNull()

    await act(async () => {
      resolveLogout?.()
    })
  })

  it('updates the cached user when updateUser is called', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const updatedUser = { ...mockUser, email: 'new@example.com', avatar_url: 'https://example.com/avatar.png' }

    act(() => {
      result.current.updateUser(updatedUser)
    })

    expect(result.current.user).toMatchObject(updatedUser)
    expect(JSON.parse(localStorage.getItem(STORAGE_KEYS.AUTH_USER) ?? 'null')).toMatchObject(updatedUser)
  })
})
