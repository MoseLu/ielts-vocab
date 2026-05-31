import { act, renderHook } from '@testing-library/react'
import { useHomePage } from './useHomePage'

const navigationState = vi.hoisted(() => ({
  navigate: vi.fn(),
}))

const hooksState = vi.hoisted(() => ({
  vocabBooks: {
    books: [],
    loading: false,
    error: null as string | null,
    refetch: vi.fn(),
  },
  allBookProgress: {
    progressMap: {},
    loading: false,
    error: null as string | null,
    refetch: vi.fn(),
  },
  myBooks: {
    myBookIds: new Set<string>(),
    loading: false,
    error: null as string | null,
    refetch: vi.fn(),
    addBook: vi.fn(),
    removeBook: vi.fn(),
  },
  learningStats: {
    learnerProfile: null,
    alltime: null,
  },
  homeTodos: {
    primaryItems: [],
    overflowItems: [],
    error: null,
  },
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigationState.navigate,
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useVocabBooks: () => hooksState.vocabBooks,
  useAllBookProgress: () => hooksState.allBookProgress,
  useMyBooks: () => hooksState.myBooks,
  useLearningStats: () => hooksState.learningStats,
}))

vi.mock('../../../features/home/hooks/useHomeTodos', () => ({
  useHomeTodos: () => hooksState.homeTodos,
}))

vi.mock('../../../hooks/useResponsiveSkeletonCount', () => ({
  useResponsivePageSkeletonCount: () => ({ containerRef: { current: null }, count: 6 }),
}))

describe('useHomePage book data recovery', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  beforeEach(() => {
    hooksState.vocabBooks.books = []
    hooksState.vocabBooks.loading = false
    hooksState.vocabBooks.error = null
    hooksState.vocabBooks.refetch.mockReset()
    hooksState.allBookProgress.progressMap = {}
    hooksState.allBookProgress.loading = false
    hooksState.allBookProgress.error = null
    hooksState.allBookProgress.refetch.mockReset()
    hooksState.myBooks.myBookIds = new Set()
    hooksState.myBooks.loading = false
    hooksState.myBooks.error = null
    hooksState.myBooks.refetch.mockReset()
  })

  it('retries all home book data sources after a startup request failure', () => {
    vi.useFakeTimers()
    hooksState.vocabBooks.error = '服务暂时不可用'
    hooksState.allBookProgress.error = '服务暂时不可用'
    hooksState.myBooks.error = '服务暂时不可用'

    renderHook(() => useHomePage())

    expect(hooksState.vocabBooks.refetch).not.toHaveBeenCalled()

    act(() => {
      vi.advanceTimersByTime(900)
    })

    expect(hooksState.vocabBooks.refetch).toHaveBeenCalledTimes(1)
    expect(hooksState.allBookProgress.refetch).toHaveBeenCalledTimes(1)
    expect(hooksState.myBooks.refetch).toHaveBeenCalledTimes(1)
  })

  it('does not retry an empty book list when the data sources resolved cleanly', () => {
    vi.useFakeTimers()

    renderHook(() => useHomePage())

    act(() => {
      vi.advanceTimersByTime(900)
    })

    expect(hooksState.vocabBooks.refetch).not.toHaveBeenCalled()
    expect(hooksState.allBookProgress.refetch).not.toHaveBeenCalled()
    expect(hooksState.myBooks.refetch).not.toHaveBeenCalled()
  })
})
