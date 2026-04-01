import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'
import { setGlobalLearningContext } from '../../contexts/AIChatContext'
import { loadSmartStats } from '../../lib/smartMode'

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
  default: ({ vocabularyLength }: { vocabularyLength: number }) => (
    <div data-testid="practice-control-bar">total:{vocabularyLength}</div>
  ),
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

vi.mock('./QuickMemoryMode', () => ({
  default: () => null,
}))

vi.mock('../SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../ui/Loading', () => ({
  Loading: ({ text }: { text: string }) => <div>{text}</div>,
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

vi.mock('./OptionsMode', () => ({
  default: ({
    currentWord,
    total,
    progressValue,
  }: {
    currentWord: { word: string }
    total: number
    progressValue: number
  }) => (
    <div data-testid="options-mode">
      current:{currentWord.word};total:{total};progress:{progressValue}
    </div>
  ),
}))

describe('PracticePage error mode filters', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    vi.mocked(setGlobalLearningContext).mockReset()
    vi.mocked(loadSmartStats).mockReturnValue({})
    localStorage.clear()

    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: false }))
    localStorage.setItem('wrong_words', JSON.stringify([
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 6,
        first_wrong_at: '2026-03-31T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: 'beta definition',
        wrong_count: 4,
        first_wrong_at: '2026-03-31T05:00:00.000Z',
        meaning_wrong: 2,
      },
      {
        word: 'gamma',
        phonetic: '/g/',
        pos: 'n.',
        definition: 'gamma definition',
        wrong_count: 8,
        first_wrong_at: '2026-03-28T05:00:00.000Z',
        meaning_wrong: 4,
      },
      {
        word: 'delta',
        phonetic: '/d/',
        pos: 'n.',
        definition: 'delta definition',
        wrong_count: 9,
        first_wrong_at: '2026-03-31T05:00:00.000Z',
        listening_wrong: 4,
      },
    ]))
  })

  it('uses the selected date and wrong-count filters to narrow the error review queue', async () => {
    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors&dim=meaning&startDate=2026-03-31&endDate=2026-03-31&minWrong=5']}>
        <PracticePage
          user={{ id: 42 }}
          mode="meaning"
          showToast={() => {}}
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:alpha')
      expect(screen.getByTestId('options-mode')).toHaveTextContent('total:1')
    })
  })
})
