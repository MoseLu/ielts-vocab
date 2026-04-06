import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'
import { setGlobalLearningContext } from '../../contexts/AIChatContext'
import { chooseSmartDimension, loadSmartStats } from '../../lib/smartMode'
import { STORAGE_KEYS } from '../../constants'
import {
  getWrongWordsProgressStorageKey,
  getWrongWordsStorageKey,
} from '../../features/vocabulary/wrongWordsStore'

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

function seedScopedWrongWordsProgress(userId: number | string, snapshot: unknown) {
  setAuthenticatedUser(userId)
  localStorage.setItem(getWrongWordsProgressStorageKey(userId), JSON.stringify(snapshot))
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
    total,
    progressValue,
    onOptionSelect,
    correctIndex,
    wrongSelections = [],
    showResult,
    spellingInput,
    spellingResult,
    onSpellingInputChange,
    onSpellingSubmit,
  }: {
    currentWord: { word: string }
    total: number
    progressValue: number
    onOptionSelect: (idx: number) => void
    correctIndex: number
    wrongSelections?: number[]
    showResult: boolean
    spellingInput: string
    spellingResult: 'correct' | 'wrong' | null
    onSpellingInputChange: (value: string) => void
    onSpellingSubmit: () => void
  }) => (
    <div data-testid="options-mode">
      current:{currentWord.word};total:{total};progress:{progressValue};wrongs:{wrongSelections.join(',')};result:{showResult ? 'done' : 'pending'}
      <button data-testid="answer-correct" onClick={() => onOptionSelect(correctIndex)}>correct</button>
      <button data-testid="answer-wrong" onClick={() => onOptionSelect(correctIndex === 0 ? 1 : 0)}>wrong</button>
      <input data-testid="meaning-input" value={spellingInput} onChange={event => onSpellingInputChange(event.target.value)} />
      <button data-testid="submit-recall" onClick={() => onSpellingSubmit()}>submit</button>
      <span data-testid="meaning-result">{spellingResult ?? 'idle'}</span>
    </div>
  ),
}))

describe('PracticePage error mode', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    vi.mocked(setGlobalLearningContext).mockReset()
    vi.mocked(loadSmartStats).mockReturnValue({})
    vi.mocked(chooseSmartDimension).mockReturnValue('meaning')
    localStorage.clear()
  })

  it('ignores stale global wrong-word cache when a logged-in user loads error review', async () => {
    setAuthenticatedUser(42)
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'local-only', phonetic: '/l/', pos: 'n.', definition: 'from local cache', wrong_count: 1 },
    ]))

    apiFetchMock.mockResolvedValue({
      words: [
        {
          word: 'remote-1',
          phonetic: '/r1/',
          pos: 'n.',
          definition: 'remote word 1',
          wrong_count: 1,
          listening_confusables: [
            { word: 'remote-a', phonetic: '/ra/', pos: 'n.', definition: 'remote distractor a' },
            { word: 'remote-b', phonetic: '/rb/', pos: 'n.', definition: 'remote distractor b' },
            { word: 'remote-c', phonetic: '/rc/', pos: 'n.', definition: 'remote distractor c' },
          ],
        },
        {
          word: 'remote-2',
          phonetic: '/r2/',
          pos: 'v.',
          definition: 'remote word 2',
          wrong_count: 1,
          listening_confusables: [
            { word: 'remote-d', phonetic: '/rd/', pos: 'v.', definition: 'remote distractor d' },
            { word: 'remote-e', phonetic: '/re/', pos: 'v.', definition: 'remote distractor e' },
            { word: 'remote-f', phonetic: '/rf/', pos: 'v.', definition: 'remote distractor f' },
          ],
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('practice-control-bar')).toHaveTextContent('total:2')
    })

    expect(JSON.parse(localStorage.getItem(getWrongWordsStorageKey(42)) || '[]')).toHaveLength(2)
    expect(JSON.parse(localStorage.getItem('wrong_words') || '[]')).toHaveLength(1)
  })

  it('records error-review results in the logged-in user scoped wrong-word store', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: false }))
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'legacy-global', phonetic: '/l/', pos: 'n.', definition: 'legacy global cache', wrong_count: 1 },
    ]))
    seedScopedWrongWords(42, [
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 2 },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition', wrong_count: 2 },
    ])

    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:alpha')
    })

    fireEvent.change(screen.getByTestId('meaning-input'), { target: { value: 'WRONG' } })
    fireEvent.click(screen.getByTestId('submit-recall'))

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:beta')
    }, { timeout: 2500 })
  })

  it('restores saved wrong-word review progress instead of restarting from the first word', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: true }))
    seedScopedWrongWords(42, [
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 1 },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition', wrong_count: 1 },
      { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma definition', wrong_count: 1 },
    ])
    seedScopedWrongWordsProgress(42, {
      _last: {
        current_index: 1,
        correct_count: 2,
        wrong_count: 1,
        is_completed: false,
        queue_words: ['alpha', 'beta', 'gamma'],
        updatedAt: '2026-03-30T12:00:00.000Z',
      },
    })

    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:beta')
    })
  })

  it('accepts typed english recall answers in meaning mode and advances on correct submit', async () => {
    localStorage.setItem('app_settings', JSON.stringify({ shuffle: false, repeatWrong: false }))
    seedScopedWrongWords(42, [
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 1 },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition', wrong_count: 1 },
    ])

    apiFetchMock.mockResolvedValue({ words: [] })

    render(
      <MemoryRouter initialEntries={['/practice?mode=errors']}>
        <PracticePage user={{ id: 42 }} mode="meaning" showToast={() => {}} onModeChange={() => {}} onDayChange={() => {}} />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:alpha')
    })

    fireEvent.change(screen.getByTestId('meaning-input'), { target: { value: 'ALPHA' } })
    fireEvent.click(screen.getByTestId('submit-recall'))

    await waitFor(() => {
      expect(screen.getByTestId('options-mode')).toHaveTextContent('current:beta')
    }, { timeout: 2500 })
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
    seedScopedWrongWords(42, [
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition', wrong_count: 4 },
      { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition', wrong_count: 3 },
      { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma definition', wrong_count: 2 },
      { word: 'delta', phonetic: '/d/', pos: 'n.', definition: 'delta definition', wrong_count: 1 },
    ])

    apiFetchMock.mockResolvedValue({ words: [] })

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
        mode: 'review',
        weakestDimension: 'meaning',
        weakFocusWords: expect.arrayContaining(['beta']),
        recentWrongWords: expect.arrayContaining(['alpha', 'beta']),
        trapStrategy: expect.stringContaining('错词'),
      }))
    })
  })
})
