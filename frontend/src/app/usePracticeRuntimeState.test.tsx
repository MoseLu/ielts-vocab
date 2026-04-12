import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { normalizePracticeDay, usePracticeRuntimeState } from './usePracticeRuntimeState'

describe('normalizePracticeDay', () => {
  it('accepts positive integer day values', () => {
    expect(normalizePracticeDay('3')).toBe(3)
    expect(normalizePracticeDay(7)).toBe(7)
  })

  it('rejects empty and invalid day values', () => {
    expect(normalizePracticeDay(null)).toBeNull()
    expect(normalizePracticeDay('')).toBeNull()
    expect(normalizePracticeDay('abc')).toBeNull()
    expect(normalizePracticeDay(0)).toBeNull()
    expect(normalizePracticeDay(Number.NaN)).toBeNull()
  })
})

describe('usePracticeRuntimeState', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('drops an invalid stored current_day value during hydration', () => {
    localStorage.setItem('current_day', 'abc')

    const { result } = renderHook(() => usePracticeRuntimeState())

    expect(result.current.currentDay).toBeNull()
    expect(localStorage.getItem('current_day')).toBeNull()
  })

  it('stores only normalized day values and clears invalid updates', () => {
    const { result } = renderHook(() => usePracticeRuntimeState())

    act(() => {
      result.current.handleDayChange(5)
    })

    expect(result.current.currentDay).toBe(5)
    expect(localStorage.getItem('current_day')).toBe('5')

    act(() => {
      result.current.handleDayChange(Number.NaN as unknown as number)
    })

    expect(result.current.currentDay).toBeNull()
    expect(localStorage.getItem('current_day')).toBeNull()
  })
})
