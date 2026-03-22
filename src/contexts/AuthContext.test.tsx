// ── Tests for src/contexts/AuthContext.tsx ────────────────────────────────────

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAuth } from './AuthContext'

// Minimal AuthProvider wrapper
import { AuthProvider } from './AuthContext'
import { render } from '@testing-library/react'

// Re-mock fetch for these tests (test-specific overrides)
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  localStorage.clear()
  mockFetch.mockReset()
  mockFetch.mockResolvedValue(new Response())
})

// ── useAuth error path ────────────────────────────────────────────────────────

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useAuth())).toThrow(
      'useAuth must be used within AuthProvider'
    )
    consoleSpy.mockRestore()
  })
})

// ── AuthProvider initialization ─────────────────────────────────────────────────

describe('AuthProvider', () => {
  it('starts with isLoading true, then resolves to false', async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('starts unauthenticated when no token in storage', async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('loads user from localStorage when token exists', async () => {
    const storedUser = {
      id: 42,
      username: 'testuser',
      email: 'test@example.com',
      avatar_url: null,
      created_at: '2024-01-01T00:00:00Z',
    }
    localStorage.setItem('auth_token', 'valid-token')
    localStorage.setItem('auth_user', JSON.stringify(storedUser))

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.id).toBe(42)
    expect(result.current.user?.username).toBe('testuser')
  })

  it('clears corrupted user data and logs out', async () => {
    localStorage.setItem('auth_token', 'valid-token')
    localStorage.setItem('auth_user', 'not valid json')

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.isAuthenticated).toBe(false)
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('loads user with legacy raw shape (no Zod schema)', async () => {
    const rawUser = {
      id: 99,
      username: 'legacyuser',
      email: 'legacy@example.com',
      created_at: '2024-06-01T00:00:00Z',
    }
    localStorage.setItem('auth_token', 'legacy-token')
    localStorage.setItem('auth_user', JSON.stringify(rawUser))

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.id).toBe(99)
    expect(result.current.user?.username).toBe('legacyuser')
  })
})

// ── login ─────────────────────────────────────────────────────────────────────

describe('login', () => {
  it('calls /api/auth/login and stores token/user on success', async () => {
    const mockUser = { id: 1, username: 'alice', email: 'a@b.com', avatar_url: null, created_at: '2024-01-01' }
    const mockToken = 'jwt-token-abc'
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ user: mockUser, token: mockToken }),
    })

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await act(async () => {
      await result.current.login('a@b.com', 'password123')
    })

    expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ email: 'a@b.com', password: 'password123' }),
    }))
    expect(localStorage.getItem('auth_token')).toBe(mockToken)
    expect(result.current.isAuthenticated).toBe(true)
  })

  it('throws with formatted error on API error response', async () => {
    // Use valid password so Zod validation passes, then API returns 401
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ error: 'Invalid credentials' }),
    })

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.login('a@b.com', 'password123')
      })
    ).rejects.toBeDefined()
  })

  it('throws when Zod validation of response fails', async () => {
    // Response doesn't match AuthResponseSchema
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ notUser: 'no' }),
    })

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.login('a@b.com', 'password123')
      })
    ).rejects.toThrow('服务器响应格式错误')
  })
})

// ── logout ────────────────────────────────────────────────────────────────────

describe('logout', () => {
  it('clears token and user and sets isAuthenticated to false', async () => {
    const mockUser = { id: 1, username: 'alice', email: 'a@b.com', avatar_url: null, created_at: '2024-01-01' }
    localStorage.setItem('auth_token', 'my-token')
    localStorage.setItem('auth_user', JSON.stringify(mockUser))
    localStorage.setItem('my_books', JSON.stringify(['book1']))

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.isAuthenticated).toBe(true)

    act(() => {
      result.current.logout()
    })

    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('auth_user')).toBeNull()
    expect(localStorage.getItem('my_books')).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })
})

// ── updateUser ────────────────────────────────────────────────────────────────

describe('updateUser', () => {
  it('updates user state and localStorage', async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    })
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const updatedUser = { id: 1, username: 'alice', email: 'new@b.com', avatar_url: 'http://avatar.png', created_at: '2024-01-01' }
    act(() => {
      result.current.updateUser(updatedUser)
    })

    expect(result.current.user).toEqual(updatedUser)
    expect(JSON.parse(localStorage.getItem('auth_user')!)).toEqual(updatedUser)
  })
})
