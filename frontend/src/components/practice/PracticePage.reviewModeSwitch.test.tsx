import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import PracticePage from './PracticePage'

const {
  apiFetchMock,
  practiceControlBarMock,
  startSessionMock,
} = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  practiceControlBarMock: vi.fn(),
  startSessionMock: vi.fn().mockResolvedValue(null),
}))

vi.mock('../../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: () => ({
    isConnected: false,
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
  recordWordResult: vi.fn(),
  chooseSmartDimension: vi.fn(() => 'meaning'),
  buildSmartQueue: vi.fn(() => []),
  syncSmartStatsToBackend: vi.fn(),
  loadSmartStatsFromBackend: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  recordModeAnswer: vi.fn(),
  resolveStudySessionDurationSeconds: () => 0,
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
    useFavoriteWords: () => ({
      isFavorite: () => false,
      isPending: () => false,
      toggleFavorite: vi.fn(),
    }),
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

vi.mock('./PracticeControlBar', () => ({
  default: (props: { mode: string; onModeChange: (mode: string) => void }) => {
    practiceControlBarMock(props)
    return <button type="button" onClick={() => props.onModeChange('meaning')}>switch-meaning</button>
  },
}))

vi.mock('./QuickMemoryMode', () => ({
  default: ({ vocabulary }: { vocabulary: Array<{ word: string }> }) => (
    <div data-testid="quickmemory-mode">{vocabulary.map(word => word.word).join(',')}</div>
  ),
}))

vi.mock('./OptionsMode', () => ({
  default: ({ mode }: { mode: string }) => <div data-testid="options-mode">{mode}</div>,
}))

vi.mock('./WordListPanel', () => ({ default: () => null }))
vi.mock('./RadioMode', () => ({ default: () => null }))
vi.mock('./DictationMode', () => ({ default: () => null }))
vi.mock('./FollowMode', () => ({ default: () => null }))
vi.mock('../settings/SettingsPanel', () => ({ default: () => null }))
vi.mock('../ui/Loading', () => ({
  Loading: ({ text }: { text: string }) => <div>{text}</div>,
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

describe('PracticePage due-review mode switching', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    practiceControlBarMock.mockClear()
    startSessionMock.mockClear()
    localStorage.clear()
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      reviewLimitCustomized: true,
      shuffle: true,
    }))
  })

  it('persists the selected practice mode in the due-review route', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockResolvedValue({
      words: [{ word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' }],
      summary: {
        due_count: 1,
        upcoming_count: 0,
        returned_count: 1,
        review_window_days: 3,
        offset: 0,
        limit: 10,
        total_count: 1,
        has_more: false,
        next_offset: null,
      },
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage user={{ id: 42 }} currentDay={1} mode="quickmemory" showToast={() => {}} onModeChange={() => {}} />
      </MemoryRouter>,
    )

    await screen.findByTestId('quickmemory-mode')
    await user.click(screen.getByRole('button', { name: 'switch-meaning' }))

    await waitFor(() => {
      expect(practiceControlBarMock).toHaveBeenCalledWith(expect.objectContaining({ mode: 'meaning' }))
    })
    expect(await screen.findByTestId('options-mode')).toHaveTextContent('meaning')
  })
})
