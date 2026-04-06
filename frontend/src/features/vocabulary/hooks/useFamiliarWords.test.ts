import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFamiliarWords } from './useFamiliarWords'
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

describe('useFamiliarWords', () => {
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

  it('updates the familiar state immediately and ignores stale status responses', async () => {
    const statusDeferred = createDeferred<{ words: string[] }>()

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/familiar/status') return statusDeferred.promise
      if (url === '/api/books/familiar') return new Promise(() => {})
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { result } = renderHook(() => useFamiliarWords({
      userId: 7,
      vocabulary: [word],
      showToast,
    }))

    expect(result.current.isFamiliar('alpha')).toBe(false)

    act(() => {
      void result.current.toggleFamiliar(word)
    })

    expect(result.current.isFamiliar('alpha')).toBe(true)
    expect(result.current.isPending('alpha')).toBe(true)

    statusDeferred.resolve({ words: [] })

    await waitFor(() => {
      expect(result.current.isFamiliar('alpha')).toBe(true)
    })
  })

  it('rolls back the optimistic state when the mutation fails', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/familiar/status') return Promise.resolve({ words: [] })
      if (url === '/api/books/familiar') return Promise.reject(new Error('熟字失败'))
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { result } = renderHook(() => useFamiliarWords({
      userId: 7,
      vocabulary: [word],
      showToast,
    }))

    await waitFor(() => {
      expect(result.current.isFamiliar('alpha')).toBe(false)
    })

    act(() => {
      void result.current.toggleFamiliar(word)
    })

    expect(result.current.isFamiliar('alpha')).toBe(true)

    await waitFor(() => {
      expect(result.current.isFamiliar('alpha')).toBe(false)
      expect(result.current.isPending('alpha')).toBe(false)
    })
    expect(showToast).toHaveBeenCalledWith('熟字失败', 'error')
  })
})
