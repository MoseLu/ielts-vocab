import React from 'react'
import { act, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import TestMode from './TestMode'
import type { AppSettings, Word } from './types'
import { STORAGE_KEYS } from '../../constants'
import { buildLearningScope } from '../../lib/learningScope'
import { getQuickMemoryStorageKey } from '../../lib/quickMemory'

const apiFetchMock = vi.fn(() => Promise.resolve({}))
const showToastMock = vi.fn()
const startSessionMock = vi.fn(() => Promise.resolve(1))
const logSessionMock = vi.fn(() => Promise.resolve())
const cancelSessionMock = vi.fn(() => Promise.resolve())
const flushStudySessionOnPageHideMock = vi.fn()
const touchStudySessionActivityMock = vi.fn()
const updateStudySessionSnapshotMock = vi.fn()
const prepareWordAudioPlaybackMock = vi.fn(() => Promise.resolve(true))
const preloadWordAudioMock = vi.fn(() => Promise.resolve(true))
const stopAudioMock = vi.fn()
let finishInitialAudio: (() => void) | null = null
const playWordAudioMock = vi.fn((
  _word: string,
  _settings: AppSettings,
  onEnded?: () => void,
) => {
  finishInitialAudio = onEnded ?? null
  return Promise.resolve(true)
})

vi.mock('./utils', () => ({
  playWordAudio: (...args: Parameters<typeof playWordAudioMock>) => playWordAudioMock(...args),
  prepareWordAudioPlayback: (...args: unknown[]) => prepareWordAudioPlaybackMock(...args),
  preloadWordAudioBatch: (...args: unknown[]) => preloadWordAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  prepareStudySessionForLearningAction: undefined,
  finalizeStudySessionSegment: undefined,
  resolveStudySessionDurationSeconds: () => 1,
  logSession: (...args: unknown[]) => logSessionMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: (...args: unknown[]) => cancelSessionMock(...args),
  flushStudySessionOnPageHide: (...args: unknown[]) => flushStudySessionOnPageHideMock(...args),
  touchStudySessionActivity: (...args: unknown[]) => touchStudySessionActivityMock(...args),
  updateStudySessionSnapshot: (...args: unknown[]) => updateStudySessionSnapshotMock(...args),
}))

vi.mock('../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../lib/apiClient', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

const settings: AppSettings = {}
const vocabulary: Word[] = [
  { word: 'within', phonetic: '/wɪˈðɪn/', pos: 'PREP.', definition: 'inside' },
]

function renderTestMode(onWrongWord = vi.fn()) {
  return {
    onWrongWord,
    ...render(
      <TestMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={onWrongWord}
      />,
    ),
  }
}

function completeInitialAudio() {
  const onEnded = finishInitialAudio
  expect(onEnded).not.toBeNull()
  act(() => { onEnded?.() })
}

describe('TestMode', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiFetchMock.mockClear()
    apiFetchMock.mockImplementation(() => Promise.resolve({}))
    showToastMock.mockClear()
    startSessionMock.mockClear()
    logSessionMock.mockClear()
    cancelSessionMock.mockClear()
    flushStudySessionOnPageHideMock.mockClear()
    touchStudySessionActivityMock.mockClear()
    updateStudySessionSnapshotMock.mockClear()
    prepareWordAudioPlaybackMock.mockClear()
    preloadWordAudioMock.mockClear()
    stopAudioMock.mockClear()
    playWordAudioMock.mockClear()
    finishInitialAudio = null
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 1 }))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts with audio only and waits for playback completion before timing choices', async () => {
    renderTestMode()

    expect(playWordAudioMock).toHaveBeenCalledWith('within', settings, expect.any(Function), { sourcePreference: 'generated' })
    expect(screen.queryByText('within')).toBeNull()
    expect(screen.queryByText('/wɪˈðɪn/')).toBeNull()
    expect(screen.queryByText('inside')).toBeNull()
    expect(screen.getByRole('button', { name: '认识' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '不熟悉' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '不认识' })).toBeDisabled()

    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(screen.getByRole('button', { name: '认识' })).toBeInTheDocument()
    expect(screen.queryByText('✗ 不认识')).toBeNull()

    completeInitialAudio()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '认识' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '不熟悉' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '不认识' })).toBeEnabled()
  })

  it('hides known after 2.5 seconds and auto reveals unknown after 4 seconds', async () => {
    const { onWrongWord } = renderTestMode()
    completeInitialAudio()

    await act(async () => { await vi.advanceTimersByTimeAsync(2500) })
    expect(screen.queryByRole('button', { name: '认识' })).toBeNull()
    expect(screen.getByRole('button', { name: '不熟悉' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '不认识' })).toBeEnabled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500)
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(screen.getByText('✗ 不认识')).toBeInTheDocument()
    expect(screen.getByText('within')).toBeInTheDocument()
    expect(screen.getByText('/wɪˈðɪn/')).toBeInTheDocument()
    expect(screen.getByText('inside')).toBeInTheDocument()
    expect(onWrongWord).toHaveBeenCalledWith(vocabulary[0])
  })

  it('records unfamiliar as a fuzzy unknown and reveals quick-memory content', async () => {
    const { onWrongWord } = renderTestMode()
    completeInitialAudio()

    await act(async () => {
      screen.getByRole('button', { name: '不熟悉' }).click()
      await Promise.resolve()
    })

    expect(screen.getByText('△ 不熟悉')).toBeInTheDocument()
    expect(screen.getByText('模糊')).toBeInTheDocument()
    expect(screen.getByText('within')).toBeInTheDocument()
    expect(onWrongWord).toHaveBeenCalledWith(vocabulary[0])

    const storageKey = getQuickMemoryStorageKey(1, buildLearningScope({ bookId: 'book-1', chapterId: '1' }))
    expect(JSON.parse(localStorage.getItem(storageKey) ?? '{}').within).toMatchObject({
      status: 'unknown',
      fuzzyCount: 1,
      unknownCount: 1,
    })

    const syncCall = apiFetchMock.mock.calls.find(([url]) => url === '/api/ai/quick-memory/sync')
    expect(JSON.parse(String((syncCall?.[1] as { body?: string })?.body ?? '{}'))).toMatchObject({
      source: 'quickmemory',
      sourceMode: 'test',
    })
  })

  it('shows the reveal UI after one known click while session start is pending', async () => {
    let resolveSession: (sessionId: number) => void = () => {}
    startSessionMock.mockImplementationOnce(() => new Promise<number>(resolve => {
      resolveSession = resolve
    }))
    renderTestMode()
    completeInitialAudio()

    await act(async () => {
      screen.getByRole('button', { name: '认识' }).click()
      await Promise.resolve()
    })

    expect(screen.getByText('✓ 认识')).toBeInTheDocument()
    expect(screen.getByText('within')).toBeInTheDocument()
    expect(screen.getByText('inside')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '认识' })).toBeNull()

    await act(async () => {
      resolveSession(1)
      await Promise.resolve()
    })
  })
})
