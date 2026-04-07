import React from 'react'
import { act, fireEvent, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import PracticePage from './PracticePage'
import { setGlobalLearningContext } from '../../contexts/AIChatContext'

const apiFetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const playWordAudioMock = vi.fn()
const prepareWordAudioPlaybackMock = vi.fn(() => Promise.resolve(true))
const preloadWordAudioMock = vi.fn(() => Promise.resolve(true))
const recordWordResultMock = vi.fn()
const recordModeAnswerMock = vi.fn()
const useFavoriteWordsMock = vi.fn(() => ({
  isFavorite: () => false,
  isPending: () => false,
  toggleFavorite: vi.fn(),
}))

vi.mock('../../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: () => ({
    isConnected: true,
    isRecording: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}))

vi.mock('../../contexts/AIChatContext', () => ({
  setGlobalLearningContext: vi.fn(),
}))

vi.mock('../../lib/smartMode', () => ({
  loadSmartStats: vi.fn(() => ({})),
  recordWordResult: (...args: unknown[]) => recordWordResultMock(...args),
  chooseSmartDimension: vi.fn(() => 'meaning'),
  buildSmartQueue: vi.fn(() => []),
  syncSmartStatsToBackend: vi.fn(),
  loadSmartStatsFromBackend: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  recordModeAnswer: (...args: unknown[]) => recordModeAnswerMock(...args),
  logSession: vi.fn(),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: vi.fn(),
  flushStudySessionOnPageHide: vi.fn(),
  touchStudySessionActivity: vi.fn(),
  updateStudySessionSnapshot: vi.fn(),
}))

vi.mock('../../features/vocabulary/hooks', async () => {
  const actual = await vi.importActual<typeof import('../../features/vocabulary/hooks')>('../../features/vocabulary/hooks')
  return {
    ...actual,
    useFavoriteWords: (...args: unknown[]) => useFavoriteWordsMock(...args),
  }
})

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    buildApiUrl: (path: string) => path,
  }
})

vi.mock('./utils', async () => {
  const actual = await vi.importActual<typeof import('./utils')>('./utils')
  return {
    ...actual,
    playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
    prepareWordAudioPlayback: (...args: unknown[]) => prepareWordAudioPlaybackMock(...args),
    preloadWordAudio: (...args: unknown[]) => preloadWordAudioMock(...args),
    preloadWordAudioBatch: (...args: unknown[]) => preloadWordAudioMock(...args),
    stopAudio: vi.fn(),
  }
})

vi.mock('./PracticeControlBar', () => ({
  default: () => null,
}))

vi.mock('./WordListPanel', () => ({
  default: () => null,
}))

vi.mock('./RadioMode', () => ({
  default: () => null,
}))

vi.mock('./QuickMemoryMode', () => ({
  default: () => null,
}))

vi.mock('../settings/SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../ui', () => ({
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

async function flushMicrotasks() {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
  })
}

describe('PracticePage dictation retry flow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    prepareWordAudioPlaybackMock.mockClear()
    preloadWordAudioMock.mockClear()
    localStorage.clear()
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: false }))

    apiFetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/progress') return { progress: [] }
      return {}
    })

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      json: async () => ({
        vocabulary: [
          { word: 'alpha', phonetic: '/ˈæl.fə/', pos: 'n.', definition: 'first' },
          { word: 'beta', phonetic: '/ˈbeɪ.tə/', pos: 'n.', definition: 'second' },
        ],
      }),
    } as Response)
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('keeps replaying the current dictation item until the spelling is correct', async () => {
    const { container } = render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="dictation"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await flushMicrotasks()

    expect(container.querySelector('.spelling-input')).not.toBeNull()
    expect(container.querySelector('.skip-btn')).toBeNull()

    act(() => {
      vi.advanceTimersByTime(300)
    })
    await flushMicrotasks()
    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['alpha'])

    const input = container.querySelector('.spelling-input') as HTMLInputElement
    const submit = container.querySelector('.spelling-submit-btn') as HTMLButtonElement

    fireEvent.change(input, { target: { value: 'alpga' } })
    fireEvent.click(submit)

    expect(recordWordResultMock).toHaveBeenLastCalledWith('alpha', 'dictation', false)
    expect(recordModeAnswerMock).toHaveBeenLastCalledWith('dictation', false)
    expect(container.textContent).toContain('拼写错误')
    expect(container.textContent).toContain('正确拼写')
    expect(container.textContent).toContain('你的输入')
    expect(container.textContent).toContain('alpha')
    expect(container.textContent).toContain('alpga')
    expect(container.textContent).toContain('系统正在重播发音，稍后重新拼写。')

    const savedAfterWrong = JSON.parse(localStorage.getItem('day_progress') || '{}')
    expect(savedAfterWrong['1']).toMatchObject({
      current_index: 0,
      wrong_count: 1,
      correct_count: 0,
      is_completed: false,
    })

    act(() => {
      vi.advanceTimersByTime(350)
    })
    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['alpha', 'alpha'])

    act(() => {
      vi.advanceTimersByTime(2400)
    })
    await flushMicrotasks()

    const stillLockedInput = container.querySelector('.spelling-input') as HTMLInputElement
    expect(stillLockedInput.value).toBe('alpga')
    expect(stillLockedInput.disabled).toBe(true)
    expect(container.textContent).toContain('拼写错误')
    expect(playWordAudioMock.mock.calls.map(call => call[0])).not.toContain('beta')

    act(() => {
      vi.advanceTimersByTime(300)
    })
    await flushMicrotasks()

    const currentInput = container.querySelector('.spelling-input') as HTMLInputElement
    expect(currentInput.value).toBe('')
    expect(currentInput.disabled).toBe(false)
    expect(container.textContent).not.toContain('拼写错误')
    expect(playWordAudioMock.mock.calls.map(call => call[0])).not.toContain('beta')

    fireEvent.change(container.querySelector('.spelling-input') as HTMLInputElement, { target: { value: 'alpha' } })
    fireEvent.click(container.querySelector('.spelling-submit-btn') as HTMLButtonElement)

    expect(recordWordResultMock).toHaveBeenLastCalledWith('alpha', 'dictation', true)
    expect(recordModeAnswerMock).toHaveBeenLastCalledWith('dictation', true)

    const savedAfterCorrect = JSON.parse(localStorage.getItem('day_progress') || '{}')
    expect(savedAfterCorrect['1']).toMatchObject({
      current_index: 1,
      wrong_count: 1,
      correct_count: 1,
    })

    act(() => {
      vi.advanceTimersByTime(1500)
    })
    await flushMicrotasks()

    act(() => {
      vi.advanceTimersByTime(300)
    })
    await flushMicrotasks()

    expect(playWordAudioMock.mock.calls.map(call => call[0])).toContain('beta')
    expect(vi.mocked(setGlobalLearningContext)).toHaveBeenCalled()
  })

  it('locks wrong feedback after Enter submit until the user edits the input', async () => {
    const { container } = render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="dictation"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await flushMicrotasks()

    act(() => {
      vi.advanceTimersByTime(300)
    })

    const input = container.querySelector('.spelling-input') as HTMLInputElement

    fireEvent.change(input, { target: { value: 'alpga' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    act(() => {
      vi.advanceTimersByTime(3500)
    })
    await flushMicrotasks()

    const lockedInput = container.querySelector('.spelling-input') as HTMLInputElement
    expect(lockedInput.value).toBe('alpga')
    expect(lockedInput.disabled).toBe(false)
    expect(container.textContent).toContain('拼写错误')
    expect(container.textContent).toContain('alpga')
    expect(playWordAudioMock.mock.calls.map(call => call[0])).not.toContain('beta')

    fireEvent.change(lockedInput, { target: { value: 'alpha' } })

    expect(container.textContent).toContain('拼写错误')
    expect(container.textContent).toContain('alpga')
    expect((container.querySelector('.spelling-input') as HTMLInputElement).value).toBe('alpha')

    act(() => {
      vi.advanceTimersByTime(120)
    })
    await flushMicrotasks()

    expect(container.textContent).not.toContain('拼写错误')
    expect((container.querySelector('.spelling-input') as HTMLInputElement).value).toBe('alpha')
  })

  it('replays dictation audio when Tab is pressed from the spelling input', async () => {
    const { container } = render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="dictation"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await flushMicrotasks()

    act(() => {
      vi.advanceTimersByTime(300)
    })

    playWordAudioMock.mockClear()

    const input = container.querySelector('.spelling-input') as HTMLInputElement
    input.focus()

    fireEvent.keyDown(input, { key: 'Tab', code: 'Tab' })

    expect(playWordAudioMock.mock.calls.map(call => call[0])).toEqual(['alpha'])
  })
})
