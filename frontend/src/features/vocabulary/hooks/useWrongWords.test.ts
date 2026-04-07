import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useWrongWords } from './useWrongWords'

const apiFetchMock = vi.fn()
const authState = vi.hoisted(() => ({
  user: { id: 2, username: 'luo' },
}))

vi.mock('../../../contexts', () => ({
  useAuth: () => ({
    user: authState.user,
  }),
}))

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('useWrongWords', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    localStorage.clear()
  })

  it('requests the compact backend payload when details are disabled', async () => {
    apiFetchMock.mockResolvedValue({
      words: [
        {
          word: 'Alpha',
          phonetic: '/ˈalfə/',
          pos: 'n.',
          definition: 'first',
          wrong_count: 2,
        },
      ],
    })

    const { result } = renderHook(() => useWrongWords({ includeDetails: false }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/wrong-words?details=compact')
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.words).toHaveLength(1)
      expect(result.current.words[0]?.word).toBe('Alpha')
    })
  })
})
