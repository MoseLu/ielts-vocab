import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readPracticeResultOutbox } from '../../../lib/practiceResult/outbox'
import { submitWordMasteryAttempt } from '../../../lib/gamePractice'
import { recordEbbinghausPracticeResult } from '../../../lib/ebbinghausReview'
import { usePracticeWordMasterySubmitter } from './usePracticeWordMasterySubmitter'
import type { Word } from '../../../features/practice/types'

vi.mock('../../../lib/gamePractice', () => ({
  submitWordMasteryAttempt: vi.fn(),
}))

vi.mock('../../../lib/ebbinghausReview', () => ({
  recordEbbinghausPracticeResult: vi.fn(),
}))

const word: Word = {
  word: 'abandon',
  phonetic: '/əˈbændən/',
  pos: 'v.',
  definition: '放弃',
}

describe('usePracticeWordMasterySubmitter', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('11111111-2222-4333-8444-555555555555')
    vi.mocked(recordEbbinghausPracticeResult).mockClear()
    vi.mocked(submitWordMasteryAttempt).mockClear()
    vi.mocked(submitWordMasteryAttempt).mockResolvedValue({
      state: {
        nodeType: 'word',
        status: 'passed',
        failedDimensions: [],
        bossFailures: 0,
        rewardFailures: 0,
      },
      game_state: {} as never,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('persists a result command before submitting word mastery', async () => {
    const sessionIdRef = { current: 42 }
    const { result } = renderHook(() => usePracticeWordMasterySubmitter({
      userId: 7,
      bookId: 'book-1',
      chapterId: '2',
      currentWord: word,
      errorMode: false,
      sessionIdRef,
    }))

    act(() => {
      result.current({
        dimension: 'meaning',
        analyticsMode: 'smart',
        passed: true,
        result: 'correct',
        attemptIndex: 0,
      })
    })

    expect(readPracticeResultOutbox('7')[0]).toMatchObject({
      status: 'sending',
      command: {
        mode: 'smart',
        dimension: 'meaning',
        word: 'abandon',
      },
    })
    await waitFor(() => expect(submitWordMasteryAttempt).toHaveBeenCalledTimes(1))
    expect(recordEbbinghausPracticeResult).toHaveBeenCalledWith(expect.objectContaining({
      word,
      passed: true,
      sourceMode: 'smart',
      bookId: 'book-1',
      chapterId: '2',
    }))
    await waitFor(() => expect(readPracticeResultOutbox('7')[0]).toMatchObject({ status: 'acked' }))
    expect(vi.mocked(submitWordMasteryAttempt).mock.calls[0]?.[0]).toMatchObject({
      word: 'abandon',
      dimension: 'meaning',
      sourceMode: 'smart',
      traceId: 'practice:11111111-2222-4333-8444-555555555555',
      idempotencyKey: 'practice:42:smart:book-1-chapter-2:abandon:meaning:0',
    })
  })

  it('can skip the Ebbinghaus plane for a corrected answer after an earlier miss', async () => {
    const { result } = renderHook(() => usePracticeWordMasterySubmitter({
      userId: 7,
      bookId: 'book-1',
      chapterId: '2',
      currentWord: word,
      errorMode: false,
      sessionIdRef: { current: 43 },
    }))

    act(() => {
      result.current({
        dimension: 'listening',
        analyticsMode: 'listening',
        passed: true,
        result: 'correct',
        attemptIndex: 1,
        recordEbbinghaus: false,
      })
    })

    await waitFor(() => expect(submitWordMasteryAttempt).toHaveBeenCalledTimes(1))
    expect(recordEbbinghausPracticeResult).not.toHaveBeenCalled()
  })
})
