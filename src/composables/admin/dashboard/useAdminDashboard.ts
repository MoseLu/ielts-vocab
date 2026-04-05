import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '../../../lib'
import type {
  AdminDetailTab,
  AdminTab,
  AdminUser,
  Overview,
  TtsBook,
  UserDetail,
  WrongWordsSort,
} from '../../../components/admin/dashboard/AdminDashboard.types'

type SortOrder = 'asc' | 'desc'

interface UserDetailFilters {
  dateFrom?: string
  dateTo?: string
  mode?: string
  bookId?: string
  wrongWordsSort?: WrongWordsSort
}

interface UsersResponse {
  users: AdminUser[]
  total: number
  pages: number
}

interface TtsBooksResponse {
  books: TtsBook[]
}

interface TtsBookStatus {
  book_id: string
  total: number
  cached: number
  generating: boolean
  status: TtsBook['status']
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '加载失败'
}

export function useAdminDashboard() {
  const [tab, setTab] = useState<AdminTab>('overview')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('created_at')
  const [order, setOrder] = useState<SortOrder>('desc')
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [detailTab, setDetailTab] = useState<AdminDetailTab>('progress')
  const [detailDateFrom, setDetailDateFrom] = useState('')
  const [detailDateTo, setDetailDateTo] = useState('')
  const [detailMode, setDetailMode] = useState('')
  const [detailWrongWordsSort, setDetailWrongWordsSort] = useState<WrongWordsSort>('last_error')
  const [ttsBooks, setTtsBooks] = useState<TtsBook[]>([])
  const [ttsBooksLoading, setTtsBooksLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [error, setError] = useState('')

  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const ttsPollingTimers = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())

  const clearTtsPolling = useCallback((bookId: string) => {
    const timer = ttsPollingTimers.current.get(bookId)
    if (timer == null) return

    clearInterval(timer)
    ttsPollingTimers.current.delete(bookId)
  }, [])

  const clearAllTtsPolling = useCallback(() => {
    ttsPollingTimers.current.forEach(timer => clearInterval(timer))
    ttsPollingTimers.current.clear()
  }, [])

  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true)

    try {
      setOverview(await apiFetch<Overview>('/api/admin/overview'))
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setOverviewLoading(false)
    }
  }, [])

  const fetchUsers = useCallback(async (
    nextPage: number,
    nextSearch: string,
    nextSort: string,
    nextOrder: SortOrder,
  ) => {
    setLoading(true)

    try {
      const params = new URLSearchParams({
        page: String(nextPage),
        per_page: '20',
        search: nextSearch,
        sort: nextSort,
        order: nextOrder,
      })
      const data = await apiFetch<UsersResponse>(`/api/admin/users?${params}`)
      setUsers(data.users)
      setTotal(data.total)
      setPages(data.pages)
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchUserDetail = useCallback(async (userId: number, filters?: UserDetailFilters) => {
    try {
      const params = new URLSearchParams()
      params.set('wrong_words_sort', filters?.wrongWordsSort ?? 'last_error')
      if (filters?.dateFrom) params.set('date_from', filters.dateFrom)
      if (filters?.dateTo) params.set('date_to', filters.dateTo)
      if (filters?.mode) params.set('mode', filters.mode)
      if (filters?.bookId) params.set('book_id', filters.bookId)

      const query = params.toString()
      const endpoint = `/api/admin/users/${userId}${query ? `?${query}` : ''}`
      setSelectedUser(await apiFetch<UserDetail>(endpoint))
    } catch (error) {
      setError(getErrorMessage(error))
    }
  }, [])

  const fetchTtsBooks = useCallback(async () => {
    setTtsBooksLoading(true)

    try {
      const data = await apiFetch<TtsBooksResponse>('/api/tts/books-summary')
      setTtsBooks(data.books || [])
    } catch (error) {
      console.error('Failed to fetch TTS books:', error)
    } finally {
      setTtsBooksLoading(false)
    }
  }, [])

  const startTtsPolling = useCallback((bookId: string) => {
    if (ttsPollingTimers.current.has(bookId)) return

    const timer = setInterval(async () => {
      try {
        const data = await apiFetch<TtsBookStatus>(`/api/tts/status/${bookId}`)
        setTtsBooks(previous =>
          previous.map(book => (book.book_id === bookId ? { ...book, ...data } : book)),
        )

        if (!data.generating) {
          clearTtsPolling(bookId)
        }
      } catch {
        // Ignore transient polling failures and keep the current state.
      }
    }, 2000)

    ttsPollingTimers.current.set(bookId, timer)
  }, [clearTtsPolling])

  const handleGenerate = useCallback(async (bookId: string) => {
    try {
      await apiFetch(`/api/tts/generate/${bookId}`, { method: 'POST' })
      startTtsPolling(bookId)
    } catch (error) {
      console.error('Failed to start generation:', error)
    }
  }, [startTtsPolling])

  useEffect(() => {
    void fetchOverview()
    void fetchUsers(1, '', 'created_at', 'desc')
  }, [fetchOverview, fetchUsers])

  useEffect(() => {
    if (tab === 'tts' && ttsBooks.length === 0) {
      void fetchTtsBooks()
    }
  }, [fetchTtsBooks, tab, ttsBooks.length])

  useEffect(() => {
    if (tab !== 'tts') {
      clearAllTtsPolling()
      return
    }

    ttsBooks.forEach(book => {
      if (book.generating || book.status === 'running') {
        startTtsPolling(book.book_id)
      } else {
        clearTtsPolling(book.book_id)
      }
    })
  }, [clearAllTtsPolling, clearTtsPolling, startTtsPolling, tab, ttsBooks])

  useEffect(() => {
    refreshTimer.current = setInterval(() => {
      if (tab === 'overview') {
        void fetchOverview()
        return
      }

      void fetchUsers(page, search, sort, order)
    }, 30000)

    return () => {
      if (refreshTimer.current != null) {
        clearInterval(refreshTimer.current)
        refreshTimer.current = null
      }
    }
  }, [fetchOverview, fetchUsers, order, page, search, sort, tab])

  useEffect(() => {
    return () => {
      clearAllTtsPolling()
    }
  }, [clearAllTtsPolling])

  const handleSearchSubmit = useCallback(() => {
    setPage(1)
    void fetchUsers(1, search, sort, order)
  }, [fetchUsers, order, search, sort])

  const handleSearchClear = useCallback(() => {
    setSearch('')
    setPage(1)
    void fetchUsers(1, '', sort, order)
  }, [fetchUsers, order, sort])

  const handleSort = useCallback((column: string) => {
    const nextOrder: SortOrder = sort === column && order === 'desc' ? 'asc' : 'desc'
    setSort(column)
    setOrder(nextOrder)
    void fetchUsers(page, search, column, nextOrder)
  }, [fetchUsers, order, page, search, sort])

  const handlePageChange = useCallback((nextPage: number) => {
    setPage(nextPage)
    void fetchUsers(nextPage, search, sort, order)
  }, [fetchUsers, order, search, sort])

  const handleSelectUser = useCallback((userId: number) => {
    const defaultWrongWordsSort: WrongWordsSort = 'last_error'
    setDetailDateFrom('')
    setDetailDateTo('')
    setDetailMode('')
    setDetailWrongWordsSort(defaultWrongWordsSort)
    setDetailTab('progress')
    void fetchUserDetail(userId, { wrongWordsSort: defaultWrongWordsSort })
  }, [fetchUserDetail])

  const closeDetail = useCallback(() => {
    setSelectedUser(null)
    setIsFullscreen(false)
  }, [])

  return {
    tab,
    overview,
    users,
    total,
    page,
    pages,
    search,
    sort,
    order,
    selectedUser,
    isFullscreen,
    detailTab,
    detailDateFrom,
    detailDateTo,
    detailMode,
    detailWrongWordsSort,
    ttsBooks,
    ttsBooksLoading,
    loading,
    overviewLoading,
    error,
    setTab,
    setSearch,
    setIsFullscreen,
    setDetailTab,
    setDetailDateFrom,
    setDetailDateTo,
    setDetailMode,
    setDetailWrongWordsSort,
    fetchUserDetail,
    handleGenerate,
    handleSearchSubmit,
    handleSearchClear,
    handleSort,
    handlePageChange,
    handleSelectUser,
    closeDetail,
    dismissError: () => setError(''),
  }
}
