import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '../../../lib'
import type {
  AdminAssetMnemonicStatus,
  AdminAssetSummary,
  AdminAssetWord,
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

interface AssetWordsResponse {
  items: AdminAssetWord[]
  total: number
  pages: number
  summary: AdminAssetSummary
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '加载失败'
}

export function useAdminDashboard() {
  const [tab, setTab] = useState<AdminTab>('overview')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [feedbackItems, setFeedbackItems] = useState<AdminWordFeedback[]>([])
  const [assetItems, setAssetItems] = useState<AdminAssetWord[]>([])
  const [feedbackTotal, setFeedbackTotal] = useState(0)
  const [assetTotal, setAssetTotal] = useState(0)
  const [assetSummary, setAssetSummary] = useState<AdminAssetSummary | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [assetPage, setAssetPage] = useState(1)
  const [assetPages, setAssetPages] = useState(1)
  const [search, setSearch] = useState('')
  const [assetSearch, setAssetSearch] = useState('')
  const [assetBookId, setAssetBookId] = useState('')
  const [assetMnemonicStatus, setAssetMnemonicStatus] = useState<AdminAssetMnemonicStatus>('all')
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
  const [assetLoading, setAssetLoading] = useState(false)
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

  const fetchAssets = useCallback(async (
    nextPage: number,
    nextSearch: string,
    nextBookId: string,
    nextMnemonicStatus: AdminAssetMnemonicStatus,
  ) => {
    setAssetLoading(true)

    try {
      const params = new URLSearchParams({
        page: String(nextPage),
        per_page: '20',
        search: nextSearch,
        book_id: nextBookId,
        mnemonic_status: nextMnemonicStatus,
      })
      const data = await apiFetch<AssetWordsResponse>(`/api/admin/assets/words?${params}`)
      setAssetItems(data.items)
      setAssetTotal(data.total)
      setAssetPages(data.pages)
      setAssetSummary(data.summary)
    } catch (assetError) {
      setError(getErrorMessage(assetError))
    } finally {
      setAssetLoading(false)
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
    if (tab !== 'assets') return
    void fetchAssets(assetPage, assetSearch, assetBookId, assetMnemonicStatus)
  }, [fetchAssets, tab])

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

      if (tab === 'assets') {
        void fetchAssets(assetPage, assetSearch, assetBookId, assetMnemonicStatus)
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
  }, [
    assetBookId,
    assetMnemonicStatus,
    assetPage,
    assetSearch,
    fetchAssets,
    fetchFeedback,
    fetchOverview,
    fetchUsers,
    order,
    page,
    search,
    sort,
    tab,
  ])

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

  const handleAssetSearchSubmit = useCallback(() => {
    setAssetPage(1)
    void fetchAssets(1, assetSearch, assetBookId, assetMnemonicStatus)
  }, [assetBookId, assetMnemonicStatus, assetSearch, fetchAssets])

  const handleAssetSearchClear = useCallback(() => {
    setAssetSearch('')
    setAssetBookId('')
    setAssetMnemonicStatus('all')
    setAssetPage(1)
    void fetchAssets(1, '', '', 'all')
  }, [fetchAssets])

  const handleAssetBookChange = useCallback((nextBookId: string) => {
    setAssetBookId(nextBookId)
    setAssetPage(1)
    void fetchAssets(1, assetSearch, nextBookId, assetMnemonicStatus)
  }, [assetMnemonicStatus, assetSearch, fetchAssets])

  const handleAssetMnemonicStatusChange = useCallback((nextStatus: AdminAssetMnemonicStatus) => {
    setAssetMnemonicStatus(nextStatus)
    setAssetPage(1)
    void fetchAssets(1, assetSearch, assetBookId, nextStatus)
  }, [assetBookId, assetSearch, fetchAssets])

  const handleAssetPageChange = useCallback((nextPage: number) => {
    setAssetPage(nextPage)
    void fetchAssets(nextPage, assetSearch, assetBookId, assetMnemonicStatus)
  }, [assetBookId, assetMnemonicStatus, assetSearch, fetchAssets])

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
    assetItems,
    feedbackTotal,
    assetTotal,
    assetSummary,
    total,
    page,
    pages,
    assetPage,
    assetPages,
    search,
    assetSearch,
    assetBookId,
    assetMnemonicStatus,
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
    assetLoading,
    overviewLoading,
    error,
    setTab,
    setSearch,
    setAssetSearch,
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
    handleAssetSearchSubmit,
    handleAssetSearchClear,
    handleAssetBookChange,
    handleAssetMnemonicStatusChange,
    handleAssetPageChange,
    handleSelectUser,
    closeDetail,
    dismissError: () => setError(''),
  }
}
