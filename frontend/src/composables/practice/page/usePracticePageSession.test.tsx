import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePracticePageSession } from './usePracticePageSession'

const cancelSessionMock = vi.fn()
const flushStudySessionOnPageHideMock = vi.fn()
const logSessionMock = vi.fn()
const markStudySessionRecoveryHandledMock = vi.fn()
const resolveStudySessionDurationSecondsMock = vi.fn(() => 120)
const startSessionMock = vi.fn(async () => 101)
const touchStudySessionActivityMock = vi.fn()
const updateStudySessionSnapshotMock = vi.fn()
const syncSmartStatsToBackendMock = vi.fn()

vi.mock('../../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  cancelSession: (...args: unknown[]) => cancelSessionMock(...args),
  flushStudySessionOnPageHide: (...args: unknown[]) => flushStudySessionOnPageHideMock(...args),
  logSession: (...args: unknown[]) => logSessionMock(...args),
  markStudySessionRecoveryHandled: (...args: unknown[]) => markStudySessionRecoveryHandledMock(...args),
  prepareStudySessionForLearningAction: undefined,
  finalizeStudySessionSegment: undefined,
  isStudySessionActive: undefined,
  resolveStudySessionDurationSeconds: (...args: unknown[]) => resolveStudySessionDurationSecondsMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  touchStudySessionActivity: (...args: unknown[]) => touchStudySessionActivityMock(...args),
  updateStudySessionSnapshot: (...args: unknown[]) => updateStudySessionSnapshotMock(...args),
}))

vi.mock('../../../lib/appSettings', () => ({
  readAppSettingsFromStorage: () => ({}),
  writeAppSettingsToStorage: (value: unknown) => value,
}))

vi.mock('../../../lib/smartMode', () => ({
  syncSmartStatsToBackend: (...args: unknown[]) => syncSmartStatsToBackendMock(...args),
}))

function createParams(mode: 'listening' | 'quickmemory' = 'listening') {
  return {
    mode,
    errorMode: false,
    chapterId: '1',
    practiceBookId: 'ielts_listening_premium',
    practiceChapterId: '1',
    correctCount: 0,
    wrongCount: 0,
  }
}

describe('usePracticePageSession', () => {
  beforeEach(() => {
    cancelSessionMock.mockReset()
    flushStudySessionOnPageHideMock.mockReset()
    logSessionMock.mockReset()
    markStudySessionRecoveryHandledMock.mockReset()
    resolveStudySessionDurationSecondsMock.mockReset()
    resolveStudySessionDurationSecondsMock.mockReturnValue(120)
    startSessionMock.mockReset()
    startSessionMock.mockResolvedValue(101)
    touchStudySessionActivityMock.mockReset()
    updateStudySessionSnapshotMock.mockReset()
    syncSmartStatsToBackendMock.mockReset()
    localStorage.clear()
  })

  it('finalizes the active non-quickmemory segment before switching into quickmemory', async () => {
    const { result, rerender } = renderHook(
      ({ mode }) => usePracticePageSession(createParams(mode)),
      { initialProps: { mode: 'listening' as const } },
    )

    await act(async () => {
      result.current.beginSession({
        bookId: 'ielts_listening_premium',
        chapterId: '1',
      })
      await result.current.prepareSessionForLearningAction()
      await Promise.resolve()
    })

    act(() => {
      result.current.registerAnsweredWord('alpha')
      result.current.sessionCorrectRef.current = 1
    })

    await act(async () => {
      rerender({ mode: 'quickmemory' as const })
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(markStudySessionRecoveryHandledMock).toHaveBeenCalledTimes(1)
    expect(updateStudySessionSnapshotMock).toHaveBeenCalledWith(expect.objectContaining({
      sessionId: 101,
      mode: 'listening',
      wordsStudied: 1,
      correctCount: 1,
      wrongCount: 0,
    }))
    expect(logSessionMock).toHaveBeenCalledWith(expect.objectContaining({
      sessionId: 101,
      mode: 'listening',
      wordsStudied: 1,
      correctCount: 1,
      wrongCount: 0,
      durationSeconds: 120,
    }))
    expect(syncSmartStatsToBackendMock).toHaveBeenCalledWith({
      bookId: 'ielts_listening_premium',
      chapterId: '1',
      mode: 'listening',
    })
    expect(startSessionMock).toHaveBeenCalledTimes(1)
  })
})
