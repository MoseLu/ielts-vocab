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
  it('merges backend learner profile insights into practice AI context', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: true }))
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 2 },
    ]))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/wrong-words') {
        return Promise.resolve({ words: [] })
      }

      if (url === '/api/ai/learner-profile') {
        return Promise.resolve({
          date: '2026-03-31',
          summary: {
            date: '2026-03-31',
            today_words: 12,
            today_accuracy: 72,
            today_duration_seconds: 900,
            today_sessions: 2,
            streak_days: 3,
            weakest_mode: 'listening',
            weakest_mode_label: '听音选义',
            weakest_mode_accuracy: 61,
            due_reviews: 4,
            trend_direction: 'stable',
          },
          dimensions: [
            {
              dimension: 'listening',
              label: '听音辨义',
              correct: 2,
              wrong: 5,
              attempts: 7,
              accuracy: 29,
              weakness: 0.71,
            },
            {
              dimension: 'meaning',
              label: '词义辨析',
              correct: 6,
              wrong: 3,
              attempts: 9,
              accuracy: 67,
              weakness: 0.33,
            },
            {
              dimension: 'dictation',
              label: '拼写默写',
              correct: 4,
              wrong: 2,
              attempts: 6,
              accuracy: 67,
              weakness: 0.33,
            },
          ],
          focus_words: [
            {
              word: 'remote-focus',
              definition: 'from backend profile',
              wrong_count: 5,
              dominant_dimension: 'listening',
              dominant_dimension_label: '听音辨义',
              dominant_wrong: 4,
              focus_score: 14,
            },
          ],
          repeated_topics: [
            {
              title: 'kind of 和 a kind of',
              count: 3,
              word_context: 'kind',
              latest_answer: 'try another explanation',
              latest_at: '2026-03-31T10:00:00',
            },
          ],
          next_actions: ['先做听音辨义错词回顾'],
          mode_breakdown: [],
        })
      }

      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
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
    })

    await waitFor(() => {
      expect(setGlobalLearningContext).toHaveBeenLastCalledWith(expect.objectContaining({
        currentWord: 'alpha',
        weakestDimension: 'listening',
        weakFocusWords: expect.arrayContaining(['remote-focus']),
      }))
    })
  })
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

describe('PracticePage error mode', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    vi.mocked(setGlobalLearningContext).mockReset()
    vi.mocked(loadSmartStats).mockReturnValue({})
    localStorage.clear()
  })

  it('merges backend wrong words into the review queue instead of using stale local cache only', async () => {
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'local-only', phonetic: '/l/', pos: 'n.', definition: 'from local cache' },
    ]))

    apiFetchMock.mockResolvedValue({
      words: [
        { word: 'remote-1', phonetic: '/r1/', pos: 'n.', definition: 'remote word 1' },
        { word: 'remote-2', phonetic: '/r2/', pos: 'v.', definition: 'remote word 2' },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
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
      expect(screen.getByTestId('practice-control-bar')).toHaveTextContent('total:3')
    })

    expect(screen.getByTestId('options-mode')).toHaveTextContent('total:3')
    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/wrong-words')
    expect(JSON.parse(localStorage.getItem('wrong_words') || '[]')).toHaveLength(3)
  })

  it('restores saved wrong-word review progress instead of restarting from the first word', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: true }))
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition' },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition' },
      { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma definition' },
    ]))
    localStorage.setItem('wrong_words_progress', JSON.stringify({
      _last: {
        current_index: 1,
        correct_count: 2,
        wrong_count: 1,
        is_completed: false,
        queue_words: ['alpha', 'beta', 'gamma'],
        updatedAt: '2026-03-30T12:00:00.000Z',
      },
    }))

    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
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
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:beta')
    })

    expect(screen.getByTestId('options-mode')).toHaveTextContent('total:3')
    expect(screen.getByTestId('options-mode')).toHaveTextContent('progress:0.3333333333333333')
  })

  it('pushes weak words and trap strategy into the AI context during error review', async () => {
    vi.mocked(loadSmartStats).mockReturnValue({
      alpha: {
        listening: { correct: 1, wrong: 1 },
        meaning: { correct: 0, wrong: 4 },
        dictation: { correct: 1, wrong: 0 },
      },
      beta: {
        listening: { correct: 1, wrong: 0 },
        meaning: { correct: 0, wrong: 3 },
        dictation: { correct: 0, wrong: 1 },
      },
      gamma: {
        listening: { correct: 0, wrong: 2 },
        meaning: { correct: 1, wrong: 1 },
        dictation: { correct: 0, wrong: 0 },
      },
      delta: {
        listening: { correct: 3, wrong: 0 },
        meaning: { correct: 2, wrong: 0 },
        dictation: { correct: 2, wrong: 0 },
      },
    })

    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: true }))
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 4 },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition', wrong_count: 3 },
      { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma definition', wrong_count: 2 },
      { word: 'delta', phonetic: '/d/', pos: 'n.', definition: 'delta definition', wrong_count: 1 },
    ]))

    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
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
    })

    await waitFor(() => {
      expect(setGlobalLearningContext).toHaveBeenLastCalledWith(expect.objectContaining({
        currentWord: 'alpha',
        mode: 'review',
        weakestDimension: 'meaning',
        weakFocusWords: expect.arrayContaining(['beta']),
        recentWrongWords: expect.arrayContaining(['alpha', 'beta']),
        trapStrategy: expect.stringContaining('错词'),
      }))
    })
  })
})
