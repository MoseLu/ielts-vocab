// ── Admin Dashboard ─────────────────────────────────────────────────────────────
// Real-time admin panel: overview stats, user list with search/filter/sort,
// and per-user detail (progress, wrong words, study sessions).

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../lib'
import { PageSkeleton, SegmentedControl, Skeleton } from './ui'

// ── Types ─────────────────────────────────────────────────────────────────────

interface UserStats {
  total_correct: number
  total_wrong: number
  accuracy: number
  books_in_progress: number
  books_completed: number
  total_study_seconds: number
  total_words_studied: number
  wrong_words_count: number
  session_count: number
  recent_sessions_7d: number
  last_active: string | null
}

interface AdminUser {
  id: number
  username: string
  email: string
  avatar_url: string | null
  is_admin: boolean
  created_at: string
  stats: UserStats
}

interface DailyActivity {
  day: string
  sessions: number
  users: number
  study_seconds: number
  words: number
}

interface ModeStats {
  mode: string
  count: number
  words: number
}

interface TtsBook {
  book_id: string
  title: string
  color: string
  total: number
  cached: number
  generating?: boolean
  status?: 'idle' | 'running' | 'done' | 'error' | 'interrupted'
}

interface TopBook {
  book_id: string
  sessions: number
  users: number
}

interface Overview {
  total_users: number
  active_users_today: number
  active_users_7d: number
  new_users_today: number
  new_users_7d: number
  total_sessions: number
  total_study_seconds: number
  total_words_studied: number
  avg_accuracy: number
  daily_activity: DailyActivity[]
  mode_stats: ModeStats[]
  top_books: TopBook[]
}

interface UserDetail {
  user: AdminUser
  book_progress: Array<{
    book_id: string
    correct_count: number
    wrong_count: number
    is_completed: boolean
    current_index: number
    updated_at: string
  }>
  wrong_words: Array<{
    word: string
    phonetic: string
    pos: string
    definition: string
    wrong_count: number
    updated_at: string
  }>
  sessions: Array<{
    id: number
    mode: string
    book_id: string
    chapter_id: string
    words_studied: number
    correct_count: number
    wrong_count: number
    accuracy: number
    duration_seconds: number
    started_at: string
    ended_at: string | null
    studied_words: string[]
    studied_words_total: number
  }>
  daily_study: Array<{
    day: string
    seconds: number
    words: number
    correct: number
    wrong: number
  }>
  chapter_daily: Array<{
    book_id: string
    chapter_id: string
    day: string
    mode: string
    sessions: number
    words: number
    correct: number
    wrong: number
    seconds: number
  }>
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtChapterId(chapterId: string | null | undefined): string {
  if (!chapterId) return '全部章节'
  if (/^\d+$/.test(chapterId)) return `第${chapterId}章`
  return chapterId
}

function fmtSeconds(s: number) {
  if (s < 60) return `${s}秒`
  if (s < 3600) return `${Math.floor(s / 60)}分钟`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return m > 0 ? `${h}小时${m}分` : `${h}小时`
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function parseDateValue(iso: string | null) {
  if (!iso) return null
  const value = new Date(iso)
  return Number.isNaN(value.getTime()) ? null : value
}

function fmtTime(iso: string | null) {
  const d = parseDateValue(iso)
  if (!d) return '—'
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function resolveSessionEnd(startedAt: string | null, endedAt: string | null, durationSeconds: number) {
  const explicitEnd = parseDateValue(endedAt)
  if (explicitEnd) return explicitEnd

  const start = parseDateValue(startedAt)
  if (!start || durationSeconds <= 0) return null
  return new Date(start.getTime() + durationSeconds * 1000)
}

function fmtSessionTimeRange(startedAt: string | null, endedAt: string | null, durationSeconds: number) {
  const start = parseDateValue(startedAt)
  if (!start) return '—'

  const end = resolveSessionEnd(startedAt, endedAt, durationSeconds)
  if (!end) return fmtTime(startedAt)
  return `${fmtTime(startedAt)} - ${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`
}

function buildSessionContent(session: UserDetail['sessions'][number]) {
  const parts = [
    bookLabels[session.book_id] || session.book_id || '',
    fmtChapterId(session.chapter_id),
    modeLabels[session.mode] || session.mode || '',
  ].filter(Boolean)
  return parts.join(' · ') || '未记录学习内容'
}

function buildSessionWordSample(words: string[], total: number) {
  if (!words.length || total <= 0) return '未记录到词样本'
  return total > words.length ? `${words.join('、')} 等${total}个词` : words.join('、')
}

const modeLabels: Record<string, string> = {
  smart: '智能模式',
  listening: '听音选义',
  meaning: '汉译英',
  dictation: '听写模式',
  radio: '随身听',
  quickmemory: '速记模式',
}

const bookLabels: Record<string, string> = {
  ielts_reading_premium: '雅思阅读精讲',
  ielts_listening_premium: '雅思听力精讲',
  ielts_comprehensive: '雅思全面词汇',
  ielts_ultimate: '雅思核心词汇',
  awl_academic: '学术词汇表',
}

// ── Mini bar chart ────────────────────────────────────────────────────────────

function MiniBarChart({ data, valueKey, labelKey, tone = 'indigo' }: {
  data: Record<string, any>[]
  valueKey: string
  labelKey: string
  tone?: 'indigo' | 'green'
}) {
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1)
  return (
    <div className="admin-mini-bar-chart">
      <svg className={`admin-mini-bar-chart-svg admin-mini-bar-chart-svg--${tone}`} viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden="true">
      {data.map((d, i) => {
        const h = Math.max(2, Math.round((d[valueKey] / max) * 56))
        const width = 100 / data.length
        const barWidth = Math.max(width - 1.5, 1)
        return (
          <rect
            key={i}
            className="admin-mini-bar-chart-bar"
            x={i * width}
            y={60 - h}
            width={barWidth}
            height={h}
            rx="1.5"
            ry="1.5"
          >
            <title>{`${d[labelKey]}: ${d[valueKey]}`}</title>
          </rect>
        )
      })}
      </svg>
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, tone = 'indigo' }: {
  label: string; value: string | number; sub?: string; tone?: 'indigo' | 'green' | 'amber' | 'blue'
}) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className={`admin-stat-value admin-stat-value--${tone}`}>{value}</div>
      {sub && <div className="admin-stat-sub">{sub}</div>}
    </div>
  )
}

function AdminTableSkeleton() {
  return (
    <div className="admin-table-skeleton" aria-hidden="true">
      <div className="admin-table-skeleton-head">
        {Array.from({ length: 9 }, (_, index) => (
          <Skeleton key={index} width="100%" height={14} />
        ))}
      </div>
      <div className="admin-table-skeleton-body">
        {Array.from({ length: 6 }, (_, rowIndex) => (
          <div key={rowIndex} className="admin-table-skeleton-row">
            <Skeleton width="80%" height={16} />
            <Skeleton width="92%" height={16} />
            <Skeleton width="68%" height={16} />
            <Skeleton width="60%" height={16} />
            <Skeleton width="52%" height={16} />
            <Skeleton width="48%" height={16} />
            <Skeleton width="54%" height={16} />
            <Skeleton width="72%" height={16} />
            <Skeleton width="76%" height={16} />
          </div>
        ))}
      </div>
    </div>
  )
}

function TtsBooksSkeleton() {
  return (
    <div className="admin-tts-skeleton" aria-hidden="true">
      {Array.from({ length: 6 }, (_, index) => (
        <div key={index} className="tts-book-card tts-book-card--skeleton">
          <Skeleton width="58%" height={18} />
          <div className="tts-book-progress">
            <Skeleton width="100%" height={8} />
            <Skeleton width="46%" height={14} />
          </div>
          <Skeleton variant="rectangular" width="40%" height={38} />
        </div>
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const [tab, setTab] = useState<'overview' | 'users' | 'tts'>('overview')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<string>('created_at')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [detailTab, setDetailTab] = useState<'progress' | 'wrong_words' | 'sessions' | 'chart' | 'chapter_daily'>('progress')
  const [detailDateFrom, setDetailDateFrom] = useState('')
  const [detailDateTo, setDetailDateTo] = useState('')
  const [detailMode, setDetailMode] = useState('')
  const [detailBook, setDetailBook] = useState('')
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [ttsBooks, setTtsBooks] = useState<TtsBook[]>([])
  const [ttsBooksLoading, setTtsBooksLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [error, setError] = useState('')
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true)
    try {
      const data = await apiFetch<Overview>('/api/admin/overview')
      setOverview(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setOverviewLoading(false)
    }
  }, [])

  const fetchUsers = useCallback(async (p = page, s = search, srt = sort, ord = order) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(p),
        per_page: '20',
        search: s,
        sort: srt,
        order: ord,
      })
      const data = await apiFetch<{ users: AdminUser[]; total: number; pages: number }>(`/api/admin/users?${params}`)
      setUsers(data.users)
      setTotal(data.total)
      setPages(data.pages)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, search, sort, order])

  const fetchUserDetail = useCallback(async (
    userId: number,
    opts?: { dateFrom?: string; dateTo?: string; mode?: string; bookId?: string }
  ) => {
    try {
      const params = new URLSearchParams()
      if (opts?.dateFrom) params.set('date_from', opts.dateFrom)
      if (opts?.dateTo)   params.set('date_to',   opts.dateTo)
      if (opts?.mode)     params.set('mode',       opts.mode)
      if (opts?.bookId)   params.set('book_id',    opts.bookId)
      const qs = params.toString()
      const data = await apiFetch<UserDetail>(`/api/admin/users/${userId}${qs ? `?${qs}` : ''}`)
      setSelectedUser(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    }
  }, [])

  const fetchTtsBooks = useCallback(async () => {
    setTtsBooksLoading(true)
    try {
      const data = await apiFetch<{ books: TtsBook[] }>('/api/tts/books-summary')
      setTtsBooks(data.books || [])
    } catch (e) {
      console.error('Failed to fetch TTS books:', e)
    } finally {
      setTtsBooksLoading(false)
    }
  }, [])

  const startPolling = useCallback((bookId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await apiFetch<{ book_id: string; total: number; cached: number; generating: boolean; status: TtsBook['status'] }>(`/api/tts/status/${bookId}`)
        setTtsBooks(prev =>
          prev.map(b => b.book_id === bookId ? { ...b, ...data } : b)
        )
        if (!data.generating) clearInterval(interval)
      } catch { /* ignore */ }
    }, 2000)
  }, [])

  const handleGenerate = useCallback(async (bookId: string) => {
    try {
      await apiFetch(`/api/tts/generate/${bookId}`, { method: 'POST' })
      startPolling(bookId)
    } catch (e) {
      console.error('Failed to start generation:', e)
    }
  }, [startPolling])

  // Initial load
  useEffect(() => {
    fetchOverview()
    fetchUsers(1, '', 'created_at', 'desc')
  }, [])

  // Load TTS books when TTS tab is opened
  useEffect(() => {
    if (tab === 'tts' && ttsBooks.length === 0) {
      fetchTtsBooks()
    }
  }, [tab, ttsBooks.length, fetchTtsBooks])

  // Auto-restore polling for any book still marked as generating after data loads
  useEffect(() => {
    if (tab !== 'tts' || ttsBooks.length === 0) return
    ttsBooks.forEach(book => {
      if (book.generating || book.status === 'running') startPolling(book.book_id)
    })
  }, [ttsBooks, tab])

  // Auto-refresh every 30s
  useEffect(() => {
    refreshTimer.current = setInterval(() => {
      if (tab === 'overview') fetchOverview()
      else fetchUsers(page, search, sort, order)
    }, 30000)
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current)
    }
  }, [tab, page, search, sort, order, fetchOverview, fetchUsers])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchUsers(1, search, sort, order)
  }

  const handleSort = (col: string) => {
    const newOrder = sort === col && order === 'desc' ? 'asc' : 'desc'
    setSort(col)
    setOrder(newOrder)
    fetchUsers(page, search, col, newOrder)
  }

  const handlePageChange = (p: number) => {
    setPage(p)
    fetchUsers(p, search, sort, order)
  }

  const SortIcon = ({ col }: { col: string }) => (
    <span className={`admin-sort-icon ${sort === col ? 'is-active' : ''}`}>
      {sort === col ? (order === 'desc' ? '▼' : '▲') : '⇅'}
    </span>
  )

  return (
    <div className="admin-dashboard">
      {error && (
        <div className="admin-error" onClick={() => setError('')}>
          {error} <span className="admin-error-dismiss">（点击关闭）</span>
        </div>
      )}

      {/* Tabs */}
      <SegmentedControl
        className="admin-tabs"
        ariaLabel="管理台导航"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'overview', label: '平台概览' },
          { value: 'users', label: '用户管理', badge: total },
          { value: 'tts', label: '词书音频' },
        ]}
      />

      {/* ── Overview Tab ── */}
      {tab === 'overview' && (
        <div className="admin-overview">
          {overviewLoading && !overview && (
            <PageSkeleton variant="admin" />
          )}
          {overview && (
            <>
              {/* Key metrics */}
              <div className="admin-stat-grid">
                <StatCard label="总用户数" value={overview.total_users} sub={`今日新增 ${overview.new_users_today}`} tone="indigo" />
                <StatCard label="今日活跃" value={overview.active_users_today} sub={`7日活跃 ${overview.active_users_7d}`} tone="green" />
                <StatCard label="总学习时长" value={fmtSeconds(overview.total_study_seconds)} sub={`共 ${overview.total_sessions} 次练习`} tone="amber" />
                <StatCard label="总学习单词" value={overview.total_words_studied.toLocaleString()} sub={`平均准确率 ${overview.avg_accuracy}%`} tone="blue" />
              </div>

              {/* Daily activity chart */}
              <div className="admin-chart-section">
                <div className="admin-section-title">近14天每日学习趋势</div>
                {overview.daily_activity.length === 0 ? (
                  <div className="admin-empty">暂无数据</div>
                ) : (
                  <div className="admin-chart-wrapper">
                    <div className="admin-summary-heading admin-summary-heading--compact">
                      <span className="admin-summary-heading-text">练习次数</span>
                    </div>
                    <MiniBarChart
                      data={overview.daily_activity}
                      valueKey="sessions"
                      labelKey="day"
                      tone="indigo"
                    />
                    <div className="admin-chart-labels">
                      {overview.daily_activity.map((d, i) => (
                        <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>
                      ))}
                    </div>
                    <div className="admin-summary-heading">
                      <span className="admin-summary-heading-text">学习单词数</span>
                    </div>
                    <MiniBarChart
                      data={overview.daily_activity}
                      valueKey="words"
                      labelKey="day"
                      tone="green"
                    />
                    <div className="admin-chart-labels">
                      {overview.daily_activity.map((d, i) => (
                        <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="admin-two-col">
                {/* Mode distribution */}
                <div className="admin-card">
                  <div className="admin-section-title">练习模式分布</div>
                  {overview.mode_stats.length === 0 ? (
                    <div className="admin-empty">暂无数据</div>
                  ) : (
                    <div className="admin-mode-list">
                      {overview.mode_stats.map((m, i) => {
                        const totalSessions = overview.mode_stats.reduce((s, x) => s + x.count, 0)
                        const pct = totalSessions > 0 ? Math.round(m.count / totalSessions * 100) : 0
                        return (
                          <div key={i} className="admin-mode-row">
                            <div className="admin-mode-name">{modeLabels[m.mode] || m.mode}</div>
                            <div className="admin-mode-bar-wrap">
                              <progress className="admin-mode-bar" max={100} value={pct} />
                            </div>
                            <div className="admin-mode-count">{m.count}次 ({pct}%)</div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>

                {/* Top books */}
                <div className="admin-card">
                  <div className="admin-section-title">热门词书 TOP 5</div>
                  {overview.top_books.length === 0 ? (
                    <div className="admin-empty">暂无数据</div>
                  ) : (
                    <div className="admin-book-list">
                      {overview.top_books.map((b, i) => (
                        <div key={i} className="admin-book-row">
                          <span className="admin-book-rank">#{i + 1}</span>
                          <span className="admin-book-name">{bookLabels[b.book_id] || b.book_id}</span>
                          <span className="admin-book-meta">{b.sessions}次练习 · {b.users}人</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Users Tab ── */}
      {tab === 'users' && (
        <div className="admin-users">
          {/* Search + filter */}
          <form className="admin-search-row" onSubmit={handleSearch}>
            <input
              className="admin-search-input"
              placeholder="搜索用户名或邮箱..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <button type="submit" className="admin-search-btn">搜索</button>
            {search && (
              <button type="button" className="admin-search-clear" onClick={() => {
                setSearch('')
                fetchUsers(1, '', sort, order)
              }}>清除</button>
            )}
            <span className="admin-total-hint">共 {total} 位用户</span>
          </form>

          {/* Table */}
          <div className="admin-table-wrap">
            {loading ? (
              <AdminTableSkeleton />
            ) : (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('username')} className="sortable">
                      用户名 <SortIcon col="username" />
                    </th>
                    <th>邮箱</th>
                    <th onClick={() => handleSort('study_time')} className="sortable">
                      学习时长 <SortIcon col="study_time" />
                    </th>
                    <th onClick={() => handleSort('words_studied')} className="sortable">
                      学习单词 <SortIcon col="words_studied" />
                    </th>
                    <th onClick={() => handleSort('accuracy')} className="sortable">
                      准确率 <SortIcon col="accuracy" />
                    </th>
                    <th>错词数</th>
                    <th>7日练习</th>
                    <th onClick={() => handleSort('last_active')} className="sortable">
                      最近活跃 <SortIcon col="last_active" />
                    </th>
                    <th onClick={() => handleSort('created_at')} className="sortable">
                      注册时间 <SortIcon col="created_at" />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr><td colSpan={9} className="admin-empty-cell">暂无数据</td></tr>
                  ) : users.map(u => (
                    <tr key={u.id} className="admin-user-row" onClick={() => {
                      setSelectedUserId(u.id)
                      setDetailDateFrom(''); setDetailDateTo(''); setDetailMode(''); setDetailBook('')
                      fetchUserDetail(u.id)
                      setDetailTab('progress')
                    }}>
                      <td>
                        <div className="admin-user-name-cell">
                          {u.avatar_url ? (
                            <img src={u.avatar_url} alt="" className="admin-avatar" />
                          ) : (
                            <div className="admin-avatar-placeholder">{(u.username || '?')[0].toUpperCase()}</div>
                          )}
                          <span>{u.username}</span>
                          {u.is_admin && <span className="admin-badge">管理员</span>}
                        </div>
                      </td>
                      <td className="admin-cell-muted">{u.email || '—'}</td>
                      <td>{fmtSeconds(u.stats.total_study_seconds)}</td>
                      <td>{u.stats.total_words_studied.toLocaleString()}</td>
                      <td>
                        <span className={`admin-accuracy ${u.stats.accuracy >= 80 ? 'good' : u.stats.accuracy >= 60 ? 'mid' : u.stats.accuracy > 0 ? 'low' : ''}`}>
                          {u.stats.accuracy > 0 ? `${u.stats.accuracy}%` : '—'}
                        </span>
                      </td>
                      <td>{u.stats.wrong_words_count > 0 ? u.stats.wrong_words_count : '—'}</td>
                      <td>
                        <span className={`admin-sessions-badge ${u.stats.recent_sessions_7d > 0 ? 'active' : ''}`}>
                          {u.stats.recent_sessions_7d > 0 ? `${u.stats.recent_sessions_7d}次` : '—'}
                        </span>
                      </td>
                      <td className="admin-cell-muted">{fmtDate(u.stats.last_active)}</td>
                      <td className="admin-cell-muted">{fmtDate(u.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="admin-pagination">
              <button disabled={page <= 1} onClick={() => handlePageChange(page - 1)}>上一页</button>
              {Array.from({ length: pages }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  className={p === page ? 'active' : ''}
                  onClick={() => handlePageChange(p)}
                >
                  {p}
                </button>
              ))}
              <button disabled={page >= pages} onClick={() => handlePageChange(page + 1)}>下一页</button>
            </div>
          )}
        </div>
      )}

      {/* ── TTS Tab ── */}
      {tab === 'tts' && (
        <div className="admin-tts-panel">
          {ttsBooksLoading ? (
            <TtsBooksSkeleton />
          ) : ttsBooks.length === 0 ? (
            <div className="admin-tts-error">
              加载失败，请刷新重试或检查管理员登录状态
            </div>
          ) : (
            <div className="tts-books-grid">
              {ttsBooks.map(book => {
                const isDone = book.status === 'done' || (book.cached === book.total && book.total > 0)
                const isRunning = book.generating || book.status === 'running'
                const isInterrupted = book.status === 'interrupted'
                const isError = book.status === 'error'
                const cardClass = `tts-book-card ${isDone ? 'done' : ''} ${isInterrupted || isError ? 'interrupted' : ''}`
                const btnLabel = isRunning ? '生成中...' : isDone ? '已完成' : isInterrupted ? '续传' : isError ? '重试' : '生成'
                const btnClass = `tts-generate-btn ${isRunning ? 'loading' : ''} ${isDone ? 'done' : ''} ${isInterrupted || isError ? 'interrupted' : ''}`
                return (
                  <div key={book.book_id} className={cardClass}>
                    <div className="tts-book-title">{book.title}</div>
                    <div className="tts-book-progress">
                      <progress className="tts-progress-bar" max={book.total || 1} value={book.cached} />
                      <span className="tts-progress-text">
                        {book.cached} / {book.total} 条
                        {isInterrupted && <span className="tts-progress-flag tts-progress-flag--warning">已中断</span>}
                        {isError && <span className="tts-progress-flag tts-progress-flag--error">出错</span>}
                      </span>
                    </div>
                    <button
                      className={btnClass}
                      onClick={() => handleGenerate(book.book_id)}
                      disabled={isRunning || isDone}
                    >
                      {btnLabel}
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── User Detail Modal ── */}
      {selectedUser && (() => {
        const modalHeader = (
          <div className="admin-modal-header">
            <div className="admin-modal-user-info">
              {selectedUser.user.avatar_url ? (
                <img src={selectedUser.user.avatar_url} alt="" className="admin-modal-avatar" />
              ) : (
                <div className="admin-avatar-placeholder large">
                  {(selectedUser.user.username || '?')[0].toUpperCase()}
                </div>
              )}
              <div className="admin-modal-user-meta-row">
                <span className="admin-modal-username-hl">{selectedUser.user.username}</span>
                {selectedUser.user.is_admin && <span className="admin-badge">管理员</span>}
                <span className="admin-modal-meta-sep">·</span>
                <span className="admin-modal-meta-item">{selectedUser.user.email || '未绑定邮箱'}</span>
                <span className="admin-modal-meta-sep">·</span>
                <span className="admin-modal-meta-item">注册于 {fmtDate(selectedUser.user.created_at)}</span>
              </div>
            </div>
            <div className="admin-modal-actions">
              <button
                className="admin-modal-toggle-fs"
                onClick={() => setIsFullscreen(f => !f)}
                title={isFullscreen ? '退出全屏' : '全屏显示'}
              >
                {isFullscreen ? (
                  /* Minimize2 — compress arrows pointing inward (exit fullscreen) */
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                    <polyline points="4 14 10 14 10 20"/>
                    <polyline points="20 10 14 10 14 4"/>
                    <line x1="10" y1="14" x2="3" y2="21"/>
                    <line x1="21" y1="3" x2="14" y2="10"/>
                  </svg>
                ) : (
                  /* Maximize2 — expand arrows pointing outward (enter fullscreen) */
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                    <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
                    <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
                  </svg>
                )}
              </button>
              <button className="admin-modal-close" onClick={() => { setSelectedUser(null); setIsFullscreen(false) }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        )

        const modalStats = (
          <div className="admin-modal-stats">
            <div className="admin-modal-stat">
              <div className="admin-modal-stat-val">{fmtSeconds(selectedUser.user.stats.total_study_seconds)}</div>
              <div className="admin-modal-stat-lbl">总学习时长</div>
            </div>
            <div className="admin-modal-stat">
              <div className="admin-modal-stat-val">{selectedUser.user.stats.total_words_studied}</div>
              <div className="admin-modal-stat-lbl">学习单词</div>
            </div>
            <div className="admin-modal-stat">
              <div className="admin-modal-stat-val">{selectedUser.user.stats.accuracy > 0 ? `${selectedUser.user.stats.accuracy}%` : '—'}</div>
              <div className="admin-modal-stat-lbl">准确率</div>
            </div>
            <div className="admin-modal-stat">
              <div className="admin-modal-stat-val">{selectedUser.user.stats.wrong_words_count}</div>
              <div className="admin-modal-stat-lbl">错词数</div>
            </div>
            <div className="admin-modal-stat">
              <div className="admin-modal-stat-val">{selectedUser.user.stats.session_count}</div>
              <div className="admin-modal-stat-lbl">练习次数</div>
            </div>
            <div className="admin-modal-stat">
              <div className="admin-modal-stat-val">{selectedUser.user.stats.books_completed}</div>
              <div className="admin-modal-stat-lbl">完成词书</div>
            </div>
          </div>
        )

        const modalFilters = (
          <div className="admin-detail-filters">
            <input type="date" className="admin-filter-date" value={detailDateFrom}
              onChange={e => setDetailDateFrom(e.target.value)} title="开始日期" />
            <span className="admin-filter-separator">至</span>
            <input type="date" className="admin-filter-date" value={detailDateTo}
              onChange={e => setDetailDateTo(e.target.value)} title="结束日期" />
            <select className="admin-filter-select" value={detailMode} onChange={e => setDetailMode(e.target.value)}>
              <option value="">全部模式</option>
              {Object.entries(modeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <button className="admin-filter-apply"
              onClick={() => selectedUserId && fetchUserDetail(selectedUserId, {
                dateFrom: detailDateFrom, dateTo: detailDateTo, mode: detailMode, bookId: detailBook
              })}>查询</button>
            <button className="admin-filter-reset" onClick={() => {
              setDetailDateFrom(''); setDetailDateTo(''); setDetailMode(''); setDetailBook('')
              if (selectedUserId) fetchUserDetail(selectedUserId)
            }}>重置</button>
          </div>
        )

        const modalTabs = (
          <div className="admin-detail-tabs">
            {(['chart', 'chapter_daily', 'sessions', 'progress', 'wrong_words'] as const).map(t => (
              <button key={t} className={`admin-detail-tab ${detailTab === t ? 'active' : ''}`} onClick={() => setDetailTab(t)}>
                {{ chart: '每日趋势', chapter_daily: '章节明细', sessions: '学习明细', progress: '词书进度', wrong_words: '错词本' }[t]}
              </button>
            ))}
          </div>
        )

        const modalBodyContent = (
          <>
            {detailTab === 'chart' && (
              <div className="admin-detail-chart">
                {selectedUser.daily_study.length === 0 ? (
                  <div className="admin-empty">暂无学习记录</div>
                ) : (
                  <>
                    <div className="admin-section-title admin-section-title--tight">近30天每日学习时长（分钟）</div>
                    <MiniBarChart
                      data={selectedUser.daily_study.map(d => ({ ...d, minutes: Math.round(d.seconds / 60) }))}
                      valueKey="minutes" labelKey="day" tone="indigo"
                    />
                    <div className="admin-chart-labels">
                      {selectedUser.daily_study.map((d, i) => <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>)}
                    </div>
                    <div className="admin-section-title admin-section-title--stacked">近30天每日学习单词数</div>
                    <MiniBarChart data={selectedUser.daily_study} valueKey="words" labelKey="day" tone="green" />
                    <div className="admin-chart-labels">
                      {selectedUser.daily_study.map((d, i) => <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>)}
                    </div>
                    <div className="admin-section-title admin-section-title--stacked">近30天每日准确情况</div>
                    <table className="admin-inline-table">
                      <thead>
                        <tr className="admin-inline-table-head">
                          <th className="admin-inline-table-cell admin-inline-table-cell--left">日期</th>
                          <th className="admin-inline-table-cell admin-inline-table-cell--right">正确</th>
                          <th className="admin-inline-table-cell admin-inline-table-cell--right">错误</th>
                          <th className="admin-inline-table-cell admin-inline-table-cell--right">准确率</th>
                          <th className="admin-inline-table-cell admin-inline-table-cell--right">时长</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedUser.daily_study.map((d, i) => {
                          const tot = d.correct + d.wrong
                          const acc = tot > 0 ? Math.round(d.correct / tot * 100) : 0
                          return (
                            <tr key={i} className="admin-inline-table-row">
                              <td className="admin-inline-table-cell">{d.day}</td>
                              <td className="admin-inline-table-cell admin-inline-table-cell--right admin-cell-positive">{d.correct}</td>
                              <td className="admin-inline-table-cell admin-inline-table-cell--right admin-cell-negative">{d.wrong}</td>
                              <td className="admin-inline-table-cell admin-inline-table-cell--right">{tot > 0 ? `${acc}%` : '—'}</td>
                              <td className="admin-inline-table-cell admin-inline-table-cell--right">{fmtSeconds(d.seconds)}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}

            {detailTab === 'progress' && (
              <div>
                {selectedUser.book_progress.length === 0 ? (
                  <div className="admin-empty">暂无学习进度</div>
                ) : (
                  <table className="admin-detail-table">
                    <thead><tr><th>词书</th><th>正确</th><th>错误</th><th>准确率</th><th>状态</th><th>更新时间</th></tr></thead>
                    <tbody>
                      {selectedUser.book_progress.map((b, i) => {
                        const tot = b.correct_count + b.wrong_count
                        const acc = tot > 0 ? Math.round(b.correct_count / tot * 100) : 0
                        return (
                          <tr key={i}>
                            <td>{bookLabels[b.book_id] || b.book_id}</td>
                            <td className="admin-cell-positive">{b.correct_count}</td>
                            <td className="admin-cell-negative">{b.wrong_count}</td>
                            <td>{tot > 0 ? `${acc}%` : '—'}</td>
                            <td><span className={`admin-status-badge ${b.is_completed ? 'completed' : 'ongoing'}`}>{b.is_completed ? '已完成' : '学习中'}</span></td>
                            <td className="admin-cell-muted">{fmtDate(b.updated_at)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {detailTab === 'wrong_words' && (
              <div>
                {selectedUser.wrong_words.length === 0 ? (
                  <div className="admin-empty">暂无错词</div>
                ) : (
                  <>
                    <div className="admin-detail-summary">
                      共 {selectedUser.user.stats.wrong_words_count} 个错词，显示前 {selectedUser.wrong_words.length} 个（按错误次数排序）
                    </div>
                    <table className="admin-detail-table">
                      <thead><tr><th>单词</th><th>音标</th><th>词性</th><th>释义</th><th>错误次数</th><th>最近错误</th></tr></thead>
                      <tbody>
                        {selectedUser.wrong_words.map((w, i) => (
                          <tr key={i}>
                            <td><strong>{w.word}</strong></td>
                            <td className="admin-cell-muted">{w.phonetic || '—'}</td>
                            <td className="admin-cell-muted">{w.pos || '—'}</td>
                            <td className="admin-cell-ellipsis admin-cell-ellipsis--wide" title={w.definition}>{w.definition}</td>
                            <td><span className={`admin-wrong-count ${w.wrong_count >= 5 ? 'high' : w.wrong_count >= 3 ? 'mid' : ''}`}>{w.wrong_count}次</span></td>
                            <td className="admin-cell-muted">{fmtDate(w.updated_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}

            {detailTab === 'chapter_daily' && (
              <div>
                {!selectedUser.chapter_daily || selectedUser.chapter_daily.length === 0 ? (
                  <div className="admin-empty">暂无章节学习记录</div>
                ) : (
                  <>
                    <div className="admin-detail-summary">
                      按用户 · 词书 · 章节 · 日期 · 模式 多维汇总，共 {selectedUser.chapter_daily.length} 条记录
                    </div>
                    <table className="admin-detail-table">
                      <thead><tr><th>日期</th><th>词书</th><th>章节</th><th>模式</th><th>次数</th><th>单词</th><th>正确</th><th>错误</th><th>正确率</th><th>时长</th></tr></thead>
                      <tbody>
                        {selectedUser.chapter_daily.map((r, i) => {
                          const tot = r.correct + r.wrong
                          const acc = tot > 0 ? Math.round(r.correct / tot * 100) : 0
                          return (
                            <tr key={i}>
                              <td className="admin-cell-muted">{r.day}</td>
                              <td className="admin-cell-ellipsis" title={r.book_id}>{bookLabels[r.book_id] || r.book_id || '—'}</td>
                              <td className="admin-cell-muted">{fmtChapterId(r.chapter_id)}</td>
                              <td>{modeLabels[r.mode] || r.mode || '—'}</td>
                              <td>{r.sessions}</td><td>{r.words}</td>
                              <td className="admin-cell-positive">{r.correct}</td>
                              <td className="admin-cell-negative">{r.wrong}</td>
                              <td><span className={`admin-accuracy ${acc >= 80 ? 'good' : acc >= 60 ? 'mid' : acc > 0 ? 'low' : ''}`}>{tot > 0 ? `${acc}%` : '—'}</span></td>
                              <td>{fmtSeconds(r.seconds)}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}

            {detailTab === 'sessions' && (
              <div>
                {selectedUser.sessions.length === 0 ? (
                  <div className="admin-empty">暂无练习记录</div>
                ) : (
                  <>
                    <div className="admin-detail-summary">
                      以下按单次学习会话展示开始到结束时间、学习内容和总时长；单词列为该次会话记录到的词样本。
                    </div>
                    <table className="admin-detail-table">
                      <thead><tr><th>学习时间</th><th>学了什么</th><th>词样本</th><th>总时长</th></tr></thead>
                      <tbody>
                        {selectedUser.sessions.map((s, i) => {
                          const sessionContent = buildSessionContent(s)
                          const sessionWords = buildSessionWordSample(s.studied_words, s.studied_words_total)
                          return (
                            <tr key={i}>
                              <td>
                                <div>{fmtDate(s.started_at)}</div>
                                <div className="admin-cell-muted">{fmtSessionTimeRange(s.started_at, s.ended_at, s.duration_seconds)}</div>
                              </td>
                              <td>
                                <div className="admin-cell-ellipsis admin-cell-ellipsis--wide" title={sessionContent}>
                                  <strong>{sessionContent}</strong>
                                </div>
                                <div className="admin-cell-muted">
                                  {s.words_studied > 0 ? `共练习 ${s.words_studied} 词` : '未记录练习词数'}
                                </div>
                              </td>
                              <td className="admin-cell-muted">
                                <div className="admin-cell-ellipsis admin-cell-ellipsis--wide" title={sessionWords}>{sessionWords}</div>
                              </td>
                              <td>{fmtSeconds(s.duration_seconds)}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}
          </>
        )

        return (
        <div
          className={`admin-modal-overlay${isFullscreen ? ' admin-modal-overlay-fs' : ''}`}
          onClick={e => !isFullscreen && e.target === e.currentTarget && (setSelectedUser(null), setIsFullscreen(false))}
        >
          <div className={`admin-modal${isFullscreen ? ' admin-modal-fs' : ''}`}>
            {modalHeader}

            {isFullscreen ? (
              <div className="admin-modal-fs-content">
                <div className="admin-modal-fs-sidebar">
                  {modalStats}
                  {modalFilters}
                  {modalTabs}
                </div>
                <div className="admin-modal-fs-main">
                  <div className="admin-modal-body">
                    {modalBodyContent}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {modalStats}
                {modalFilters}
                {modalTabs}
                <div className="admin-modal-body">
                  {modalBodyContent}
                </div>
              </>
            )}
          </div>
        </div>
        )
      })()}
    </div>
  )
}

