import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFavoriteWords } from './useFavoriteWords'
import type { Word } from '../../../components/practice/types'

const apiFetchMock = vi.fn()

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useFavoriteWords', () => {
  const word: Word = {
    word: 'Alpha',
    phonetic: '/ˈalfə/',
    pos: 'n.',
    definition: 'first',
  }
  const showToast = vi.fn()

  beforeEach(() => {
    apiFetchMock.mockReset()
    showToast.mockReset()
  })

  it('updates the favorite state immediately and ignores stale status responses', async () => {
    const statusDeferred = createDeferred<{ words: string[] }>()

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/favorites/status') return statusDeferred.promise
      if (url === '/api/books/favorites') return new Promise(() => {})
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { result } = renderHook(() => useFavoriteWords({
      userId: 7,
      vocabulary: [word],
      showToast,
    }))

    expect(result.current.isFavorite('alpha')).toBe(false)

    act(() => {
      void result.current.toggleFavorite(word)
    })

    expect(result.current.isFavorite('alpha')).toBe(true)
    expect(result.current.isPending('alpha')).toBe(true)

    statusDeferred.resolve({ words: [] })

    await waitFor(() => {
      expect(result.current.isFavorite('alpha')).toBe(true)
    })
  })

  it('rolls back the optimistic state when the mutation fails', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/favorites/status') return Promise.resolve({ words: [] })
      if (url === '/api/books/favorites') return Promise.reject(new Error('收藏失败'))
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { result } = renderHook(() => useFavoriteWords({
      userId: 7,
      vocabulary: [word],
      showToast,
    }))

    await waitFor(() => {
      expect(result.current.isFavorite('alpha')).toBe(false)
    })

    act(() => {
      void result.current.toggleFavorite(word)
    })

    expect(result.current.isFavorite('alpha')).toBe(true)

    await waitFor(() => {
      expect(result.current.isFavorite('alpha')).toBe(false)
      expect(result.current.isPending('alpha')).toBe(false)
    })
    expect(showToast).toHaveBeenCalledWith('收藏失败', 'error')
  })
})
