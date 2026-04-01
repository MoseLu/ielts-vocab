import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'
import { QUICK_MEMORY_MASTERY_TARGET } from '../../lib/quickMemory'

const apiFetchMock = vi.fn()
const startSessionMock = vi.fn().mockResolvedValue(null)
const practiceControlBarMock = vi.fn(() => <div data-testid="practice-control-bar" />)
const fetchMock = vi.fn()

vi.stubGlobal('fetch', fetchMock)

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
  default: (props: unknown) => practiceControlBarMock(props),
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
  default: ({
    vocabulary,
    reviewHasMore,
    onContinueReview,
    onQuickMemoryRecordChange,
  }: {
    vocabulary: Array<{ word: string }>
    reviewHasMore?: boolean
    onContinueReview?: () => void
    onQuickMemoryRecordChange?: (word: { word: string }, record: {
      status: 'known' | 'unknown'
      firstSeen: number
      lastSeen: number
      knownCount: number
      unknownCount: number
      nextReview: number
      fuzzyCount: number
    }) => void
  }) => (
    <div data-testid="quickmemory-mode">
      reviewWords:{vocabulary.map(word => word.word).join(',')}
      {vocabulary[0] && onQuickMemoryRecordChange ? (
        <button
          type="button"
          onClick={() => onQuickMemoryRecordChange(vocabulary[0], {
            status: 'known',
            firstSeen: 1000,
            lastSeen: 2000,
            knownCount: QUICK_MEMORY_MASTERY_TARGET,
            unknownCount: 0,
            nextReview: 0,
            fuzzyCount: 0,
          })}
        >
          finish-ebbinghaus
        </button>
      ) : null}
      {reviewHasMore && onContinueReview ? (
        <button type="button" onClick={onContinueReview}>
          continue-review
        </button>
      ) : null}
    </div>
  ),
}))

describe('PracticePage quick-memory review mode', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startSessionMock.mockClear()
    practiceControlBarMock.mockClear()
    fetchMock.mockReset()
    localStorage.clear()
  })

  it('loads the dedicated Ebbinghaus review queue instead of the day vocabulary list', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0') {
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
            offset: 0,
            limit: 10,
            total_count: 2,
            has_more: false,
            next_offset: null,
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

    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0')
    expect(startSessionMock).toHaveBeenCalled()
  })

  it('loads the next review batch after the current 20-word batch is finished', async () => {
    const user = userEvent.setup()

    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '2',
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=2&within_days=3&offset=0') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
            { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
          ],
          summary: {
            due_count: 4,
            upcoming_count: 0,
            returned_count: 2,
            review_window_days: 3,
            offset: 0,
            limit: 2,
            total_count: 4,
            has_more: true,
            next_offset: 2,
          },
        })
      }

      if (url === '/api/ai/quick-memory/review-queue?limit=2&within_days=3&offset=2') {
        return Promise.resolve({
          words: [
            { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma def' },
            { word: 'delta', phonetic: '/d/', pos: 'n.', definition: 'delta def' },
          ],
          summary: {
            due_count: 4,
            upcoming_count: 0,
            returned_count: 2,
            review_window_days: 3,
            offset: 2,
            limit: 2,
            total_count: 4,
            has_more: false,
            next_offset: null,
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

    await user.click(screen.getByRole('button', { name: 'continue-review' }))

    await waitFor(() => {
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:gamma,delta')
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/quick-memory/review-queue?limit=2&within_days=3&offset=0')
    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/quick-memory/review-queue?limit=2&within_days=3&offset=2')
  })

  it('filters the review queue by the selected book chapter and keeps chapter context in the toolbar', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      shuffle: true,
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&book_id=book-a&chapter_id=2') {
        return Promise.resolve({
          words: [{
            word: 'gamma',
            phonetic: '/g/',
            pos: 'n.',
            definition: 'gamma def',
            book_id: 'book-a',
            book_title: 'Book A',
            chapter_id: '2',
            chapter_title: 'Chapter 2',
          }],
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
            contexts: [{
              book_id: 'book-a',
              book_title: 'Book A',
              chapter_id: '2',
              chapter_title: 'Chapter 2',
              due_count: 1,
              upcoming_count: 0,
              total_count: 1,
              next_review: 1,
            }],
            selected_context: {
              book_id: 'book-a',
              book_title: 'Book A',
              chapter_id: '2',
              chapter_title: 'Chapter 2',
              due_count: 1,
              upcoming_count: 0,
              total_count: 1,
              next_review: 1,
            },
          },
        })
      }

      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })
    fetchMock.mockResolvedValue({
      json: async () => ({
        chapters: [
          { id: '1', title: 'Chapter 1' },
          { id: '2', title: 'Chapter 2' },
        ],
      }),
    })

    render(
      <MemoryRouter initialEntries={['/practice?review=due&book=book-a&chapter=2']}>
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
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:gamma')
    })

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&book_id=book-a&chapter_id=2',
    )
    const lastToolbarProps = practiceControlBarMock.mock.calls.at(-1)?.[0] as {
      bookId?: string
      chapterId?: string
      currentChapterTitle?: string
    }
    expect(lastToolbarProps.bookId).toBe('book-a')
    expect(lastToolbarProps.chapterId).toBe('2')
    expect(lastToolbarProps.currentChapterTitle).toBe('Chapter 2')
  })

  it('removes mastered wrong words only after quick-memory completion', async () => {
    const user = userEvent.setup()

    localStorage.setItem('app_settings', JSON.stringify({
      reviewInterval: '3',
      reviewLimit: '10',
      shuffle: true,
    }))
    localStorage.setItem('wrong_words', JSON.stringify([
      { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def', wrong_count: 2 },
    ]))

    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0') {
        return Promise.resolve({
          words: [
            { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
          ],
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
      }

      if (url === '/api/ai/wrong-words/alpha' && options?.method === 'DELETE') {
        return Promise.resolve({ message: '已移除' })
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
      expect(screen.getByTestId('quickmemory-mode')).toHaveTextContent('reviewWords:alpha')
    })

    await user.click(screen.getByRole('button', { name: 'finish-ebbinghaus' }))

    expect(JSON.parse(localStorage.getItem('wrong_words') || '[]')).toEqual([])
    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/wrong-words/alpha', { method: 'DELETE' })
  })
})
