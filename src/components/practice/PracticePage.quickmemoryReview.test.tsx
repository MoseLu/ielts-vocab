import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'

const apiFetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)

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
  recordModeAnswer: vi.fn(),
  logSession: vi.fn(),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: vi.fn(),
}))

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    buildApiUrl: (path: string) => path,
  }
})

vi.mock('./PracticeControlBar', () => ({
  default: () => <div data-testid="practice-control-bar" />,
}))

vi.mock('./WordListPanel', () => ({
  default: () => null,
}))

vi.mock('./RadioMode', () => ({
  default: () => null,
}))

vi.mock('./DictationMode', () => ({
  default: () => null,
}))

vi.mock('./OptionsMode', () => ({
  default: () => null,
}))

vi.mock('../SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../ui/Loading', () => ({
  Loading: ({ text }: { text: string }) => <div>{text}</div>,
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

vi.mock('./QuickMemoryMode', () => ({
  default: ({ vocabulary }: { vocabulary: Array<{ word: string }> }) => (
    <div data-testid="quickmemory-mode">
      reviewWords:{vocabulary.map(word => word.word).join(',')}
    </div>
  ),
}))

describe('PracticePage quick-memory review mode', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    localStorage.clear()
  })

  it('loads the dedicated Ebbinghaus review queue instead of the day vocabulary list', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
            { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
          ],
          summary: {
            due_count: 1,
            upcoming_count: 1,
            returned_count: 2,
            review_window_days: 3,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due']}>
        <PracticePage
          user={{ id: 42 }}
          currentDay={1}
          mode="quickmemory"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha,beta')
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/quick-memory/review-queue?limit=10&within_days=3')
    expect(startSessionMock).toHaveBeenCalled()
  })
})
