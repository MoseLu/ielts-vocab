import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '../../../lib'
import type {
  AdminDetailTab,
  AdminTab,
  AdminUser,
  AdminWordFeedback,
  Overview,
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

interface WordFeedbackResponse {
  items: AdminWordFeedback[]
  total: number
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '加载失败'
}

export function useAdminDashboard() {
  const [tab, setTab] = useState<AdminTab>('overview')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [feedbackItems, setFeedbackItems] = useState<AdminWordFeedback[]>([])
  const [feedbackTotal, setFeedbackTotal] = useState(0)
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
  const [loading, setLoading] = useState(false)
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [error, setError] = useState('')

  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

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

  const fetchFeedback = useCallback(async () => {
    setFeedbackLoading(true)

    try {
      const data = await apiFetch<WordFeedbackResponse>('/api/admin/word-feedback?limit=50')
      setFeedbackItems(data.items)
      setFeedbackTotal(data.total)
    } catch (feedbackError) {
      setError(getErrorMessage(feedbackError))
    } finally {
      setFeedbackLoading(false)
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

  useEffect(() => {
    void fetchOverview()
    void fetchUsers(1, '', 'created_at', 'desc')
  }, [fetchOverview, fetchUsers])

  useEffect(() => {
    if (tab !== 'feedback') return
    void fetchFeedback()
  }, [fetchFeedback, tab])

  useEffect(() => {
    refreshTimer.current = setInterval(() => {
      if (tab === 'overview') {
        void fetchOverview()
        return
      }

      if (tab === 'feedback') {
        void fetchFeedback()
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
  }, [fetchFeedback, fetchOverview, fetchUsers, order, page, search, sort, tab])

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
    feedbackItems,
    feedbackTotal,
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
    loading,
    feedbackLoading,
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
    handleSearchSubmit,
    handleSearchClear,
    handleSort,
    handlePageChange,
    handleSelectUser,
    closeDetail,
    dismissError: () => setError(''),
  }
}
