import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'
import { setGlobalLearningContext } from '../../contexts/AIChatContext'
import { chooseSmartDimension, loadSmartStats } from '../../lib/smartMode'
import { STORAGE_KEYS } from '../../constants'
import { getWrongWordsProgressStorageKey, getWrongWordsStorageKey } from '../../features/vocabulary/wrongWordsStore'

const apiFetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const useFavoriteWordsMock = vi.fn(() => ({
  isFavorite: () => false,
  isPending: () => false,
  toggleFavorite: vi.fn(),
}))

function setAuthenticatedUser(id: number | string) {
  localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id }))
}

function seedScopedWrongWords(userId: number | string, words: unknown[]) {
  setAuthenticatedUser(userId)
  localStorage.setItem(getWrongWordsStorageKey(userId), JSON.stringify(words))
}

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

vi.mock('./PracticeControlBar', () => ({
  default: ({ vocabularyLength }: { vocabularyLength: number }) => <div data-testid="practice-control-bar">total:{vocabularyLength}</div>,
}))

vi.mock('./WordListPanel', () => ({ default: () => null }))
vi.mock('./RadioMode', () => ({ default: () => null }))
vi.mock('./DictationMode', () => ({ default: () => null }))
vi.mock('./QuickMemoryMode', () => ({ default: () => null }))
vi.mock('../settings/SettingsPanel', () => ({ default: () => null }))
vi.mock('../ui/Loading', () => ({
  Loading: ({ text }: { text: string }) => <div>{text}</div>,
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

vi.mock('./OptionsMode', () => ({
  default: ({
    currentWord,
    spellingInput,
    spellingResult,
    onSpellingInputChange,
    onSpellingSubmit,
  }: {
    currentWord: { word: string }
    spellingInput: string
    spellingResult: 'correct' | 'wrong' | null
    onSpellingInputChange: (value: string) => void
    onSpellingSubmit: () => void
  }) => (
    <div data-testid="options-mode">
      current:{currentWord.word}
      <input data-testid="meaning-input" value={spellingInput} onChange={event => onSpellingInputChange(event.target.value)} />
      <button data-testid="submit-recall" onClick={() => onSpellingSubmit()}>submit</button>
      <span data-testid="meaning-result">{spellingResult ?? 'idle'}</span>
    </div>
  ),
}))

describe('PracticePage error mode profile and persistence', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    vi.mocked(setGlobalLearningContext).mockReset()
    vi.mocked(loadSmartStats).mockReturnValue({})
    vi.mocked(chooseSmartDimension).mockReturnValue('meaning')
    localStorage.clear()
  })

  it('merges backend learner profile insights into practice AI context', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: true }))
    seedScopedWrongWords(42, [{ word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 2 }])

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/wrong-words') return Promise.resolve({ words: [] })
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
            { dimension: 'listening', label: '听音辨义', correct: 2, wrong: 5, attempts: 7, accuracy: 29, weakness: 0.71 },
            { dimension: 'meaning', label: '默写模式', correct: 6, wrong: 3, attempts: 9, accuracy: 67, weakness: 0.33 },
            { dimension: 'dictation', label: '拼写默写', correct: 4, wrong: 2, attempts: 6, accuracy: 67, weakness: 0.33 },
          ],
          focus_words: [{
            word: 'remote-focus',
            definition: 'from backend profile',
            wrong_count: 5,
            dominant_dimension: 'listening',
            dominant_dimension_label: '听音辨义',
            dominant_wrong: 4,
            focus_score: 14,
          }],
          repeated_topics: [{
            title: 'kind of 和 a kind of',
            count: 3,
            word_context: 'kind',
            latest_answer: 'try another explanation',
            latest_at: '2026-03-31T10:00:00',
          }],
          next_actions: ['先做听音辨义错词回顾'],
          mode_breakdown: [],
          activity_summary: {
            total_events: 0,
            study_sessions: 0,
            quick_memory_reviews: 0,
            wrong_word_records: 0,
            assistant_questions: 0,
            chapter_updates: 0,
            books_touched: 0,
            chapters_touched: 0,
            words_touched: 0,
            total_duration_seconds: 0,
            correct_count: 0,
            wrong_count: 0,
          },
          activity_source_breakdown: [],
          recent_activity: [],
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
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

  it('preserves is_completed:true after answering the last wrong word', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: false }))
    seedScopedWrongWords(1, [{
      word: 'only',
      phonetic: '/o/',
      pos: 'n.',
      definition: 'only definition',
      wrong_count: 1,
      listening_confusables: [
        { word: 'owner', phonetic: '/owner/', pos: 'n.', definition: 'owner definition' },
        { word: 'honor', phonetic: '/honor/', pos: 'n.', definition: 'honor definition' },
        { word: 'lonely', phonetic: '/lonely/', pos: 'adj.', definition: 'lonely definition' },
      ],
    }])

    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
        <PracticePage user={{ id: 1 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:only')
    })

    fireEvent.change(screen.getByTestId('meaning-input'), { target: { value: 'ONLY' } })
    fireEvent.click(screen.getByTestId('submit-recall'))

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(getWrongWordsProgressStorageKey(1)) || '{}')
      expect(stored._last?.is_completed).toBe(true)
    })
  })
})
