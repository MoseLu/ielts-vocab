// ── Admin Dashboard ─────────────────────────────────────────────────────────────
// Real-time admin panel: overview stats, user list with search/filter/sort,
// and per-user detail (progress, wrong words, study sessions).

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../lib'

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

function fmtDateTime(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${fmtDate(iso)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const modeLabels: Record<string, string> = {
  smart: '智能模式',
  listening: '听音选义',
  meaning: '看词选义',
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

function MiniBarChart({ data, valueKey, labelKey, color = '#6366f1' }: {
  data: Record<string, any>[]
  valueKey: string
  labelKey: string
  color?: string
}) {
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '60px' }}>
      {data.map((d, i) => {
        const h = Math.max(2, Math.round((d[valueKey] / max) * 56))
        return (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, gap: '2px' }} title={`${d[labelKey]}: ${d[valueKey]}`}>
            <div style={{ width: '100%', height: `${h}px`, background: color, borderRadius: '2px 2px 0 0', opacity: 0.85 }} />
          </div>
        )
      })}
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color = '#6366f1' }: {
  label: string; value: string | number; sub?: string; color?: string
}) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value" style={{ color }}>{value}</div>
      {sub && <div className="admin-stat-sub">{sub}</div>}
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
  const [ttsBooksLoading, setTtsBooksLoading] = useState(false)
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

  const handleGenerate = useCallback(async (bookId: string) => {
    try {
      await apiFetch(`/api/tts/generate/${bookId}`, { method: 'POST' })
      // Start polling
      const interval = setInterval(async () => {
        try {
          const data = await apiFetch<{ book_id: string; total: number; cached: number; generating: boolean }>(`/api/tts/status/${bookId}`)
          setTtsBooks(prev =>
            prev.map(b => b.book_id === bookId ? { ...b, ...data } : b)
          )
          if (!data.generating) clearInterval(interval)
        } catch { /* ignore */ }
      }, 2000)
    } catch (e) {
      console.error('Failed to start generation:', e)
    }
  }, [])

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
    <span style={{ marginLeft: '4px', opacity: sort === col ? 1 : 0.3, fontSize: '10px' }}>
      {sort === col ? (order === 'desc' ? '▼' : '▲') : '⇅'}
    </span>
  )

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <div>
          <h1 className="admin-title">管理控制台</h1>
          <p className="admin-subtitle">实时监控所有用户的学习数据</p>
        </div>
        <button
          className="admin-refresh-btn"
          onClick={() => tab === 'overview' ? fetchOverview() : fetchUsers(page, search, sort, order)}
          title="立即刷新"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          刷新
        </button>
      </div>

      {error && (
        <div className="admin-error" onClick={() => setError('')}>
          {error} <span style={{ opacity: 0.6, fontSize: '12px' }}>（点击关闭）</span>
        </div>
      )}

      {/* Tabs */}
      <div className="admin-tabs">
        <button className={`admin-tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          平台概览
        </button>
        <button className={`admin-tab ${tab === 'users' ? 'active' : ''}`} onClick={() => setTab('users')}>
          用户管理
          <span className="admin-tab-badge">{total}</span>
        </button>
        <button className={`admin-tab ${tab === 'tts' ? 'active' : ''}`} onClick={() => setTab('tts')}>
          词书音频
        </button>
      </div>

      {/* ── Overview Tab ── */}
      {tab === 'overview' && (
        <div className="admin-overview">
          {overviewLoading && !overview && (
            <div className="admin-loading">加载中...</div>
          )}
          {overview && (
            <>
              {/* Key metrics */}
              <div className="admin-stat-grid">
                <StatCard label="总用户数" value={overview.total_users} sub={`今日新增 ${overview.new_users_today}`} color="#6366f1" />
                <StatCard label="今日活跃" value={overview.active_users_today} sub={`7日活跃 ${overview.active_users_7d}`} color="#10b981" />
                <StatCard label="总学习时长" value={fmtSeconds(overview.total_study_seconds)} sub={`共 ${overview.total_sessions} 次练习`} color="#f59e0b" />
                <StatCard label="总学习单词" value={overview.total_words_studied.toLocaleString()} sub={`平均准确率 ${overview.avg_accuracy}%`} color="#3b82f6" />
              </div>

              {/* Daily activity chart */}
              <div className="admin-chart-section">
                <div className="admin-section-title">近14天每日学习趋势</div>
                {overview.daily_activity.length === 0 ? (
                  <div className="admin-empty">暂无数据</div>
                ) : (
                  <div className="admin-chart-wrapper">
                    <div style={{ marginBottom: '8px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>练习次数</span>
                    </div>
                    <MiniBarChart
                      data={overview.daily_activity}
                      valueKey="sessions"
                      labelKey="day"
                      color="#6366f1"
                    />
                    <div className="admin-chart-labels">
                      {overview.daily_activity.map((d, i) => (
                        <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>
                      ))}
                    </div>
                    <div style={{ marginTop: '16px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>学习单词数</span>
                    </div>
                    <MiniBarChart
                      data={overview.daily_activity}
                      valueKey="words"
                      labelKey="day"
                      color="#10b981"
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
                              <div className="admin-mode-bar" style={{ width: `${pct}%` }} />
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
                {loading ? (
                  <tr><td colSpan={9} className="admin-loading-cell">加载中...</td></tr>
                ) : users.length === 0 ? (
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
          <h2 className="admin-section-title">词书 TTS 音频</h2>
          <p className="admin-section-desc">为词书预生成例句音频，用户听写时直接命中本地缓存。</p>
          {ttsBooksLoading ? (
            <div className="loading-spinner" />
          ) : ttsBooks.length === 0 ? (
            <div style={{ color: '#ef4444', padding: '16px' }}>
              加载失败，请刷新重试或检查管理员登录状态
            </div>
          ) : (
            <div className="tts-books-grid">
              {ttsBooks.map(book => (
                <div
                  key={book.book_id}
                  className={`tts-book-card ${book.cached === book.total && book.total > 0 ? 'done' : ''}`}
                  style={{ '--book-color': book.color } as React.CSSProperties}
                >
                  <div className="tts-book-title">{book.title}</div>
                  <div className="tts-book-progress">
                    <div className="tts-progress-bar">
                      <div
                        className="tts-progress-fill"
                        style={{ width: `${book.total > 0 ? (book.cached / book.total) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="tts-progress-text">
                      {book.cached} / {book.total} 条
                    </span>
                  </div>
                  <button
                    className={`tts-generate-btn ${book.generating ? 'loading' : ''} ${book.cached === book.total && book.total > 0 ? 'done' : ''}`}
                    onClick={() => handleGenerate(book.book_id)}
                    disabled={book.generating || (book.cached === book.total && book.total > 0)}
                  >
                    {book.generating ? '生成中...' : book.cached === book.total && book.total > 0 ? '已完成' : '生成'}
                  </button>
                </div>
              ))}
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
            <div style={{ display: 'flex', alignItems: 'center' }}>
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
            <span style={{ color: 'var(--text-tertiary)', fontSize: '12px' }}>至</span>
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
                {{ chart: '每日趋势', chapter_daily: '章节明细', sessions: '练习记录', progress: '词书进度', wrong_words: '错词本' }[t]}
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
                    <div className="admin-section-title" style={{ marginBottom: '8px' }}>近30天每日学习时长（分钟）</div>
                    <MiniBarChart
                      data={selectedUser.daily_study.map(d => ({ ...d, minutes: Math.round(d.seconds / 60) }))}
                      valueKey="minutes" labelKey="day" color="#6366f1"
                    />
                    <div className="admin-chart-labels">
                      {selectedUser.daily_study.map((d, i) => <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>)}
                    </div>
                    <div className="admin-section-title" style={{ marginTop: '20px', marginBottom: '8px' }}>近30天每日学习单词数</div>
                    <MiniBarChart data={selectedUser.daily_study} valueKey="words" labelKey="day" color="#10b981" />
                    <div className="admin-chart-labels">
                      {selectedUser.daily_study.map((d, i) => <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>)}
                    </div>
                    <div className="admin-section-title" style={{ marginTop: '20px', marginBottom: '8px' }}>近30天每日准确情况</div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ color: 'var(--text-tertiary)' }}>
                          <th style={{ textAlign: 'left', padding: '4px 8px' }}>日期</th>
                          <th style={{ textAlign: 'right', padding: '4px 8px' }}>正确</th>
                          <th style={{ textAlign: 'right', padding: '4px 8px' }}>错误</th>
                          <th style={{ textAlign: 'right', padding: '4px 8px' }}>准确率</th>
                          <th style={{ textAlign: 'right', padding: '4px 8px' }}>时长</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedUser.daily_study.map((d, i) => {
                          const tot = d.correct + d.wrong
                          const acc = tot > 0 ? Math.round(d.correct / tot * 100) : 0
                          return (
                            <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                              <td style={{ padding: '6px 8px' }}>{d.day}</td>
                              <td style={{ textAlign: 'right', padding: '6px 8px', color: '#10b981' }}>{d.correct}</td>
                              <td style={{ textAlign: 'right', padding: '6px 8px', color: '#ef4444' }}>{d.wrong}</td>
                              <td style={{ textAlign: 'right', padding: '6px 8px' }}>{tot > 0 ? `${acc}%` : '—'}</td>
                              <td style={{ textAlign: 'right', padding: '6px 8px' }}>{fmtSeconds(d.seconds)}</td>
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
                            <td style={{ color: '#10b981' }}>{b.correct_count}</td>
                            <td style={{ color: '#ef4444' }}>{b.wrong_count}</td>
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
                    <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '12px' }}>
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
                            <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={w.definition}>{w.definition}</td>
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
                    <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '12px' }}>
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
                              <td style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.book_id}>{bookLabels[r.book_id] || r.book_id || '—'}</td>
                              <td className="admin-cell-muted">{fmtChapterId(r.chapter_id)}</td>
                              <td>{modeLabels[r.mode] || r.mode || '—'}</td>
                              <td>{r.sessions}</td><td>{r.words}</td>
                              <td style={{ color: '#10b981' }}>{r.correct}</td>
                              <td style={{ color: '#ef4444' }}>{r.wrong}</td>
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
                  <table className="admin-detail-table">
                    <thead><tr><th>时间</th><th>模式</th><th>词书</th><th>章节</th><th>单词数</th><th>正确</th><th>错误</th><th>准确率</th><th>时长</th></tr></thead>
                    <tbody>
                      {selectedUser.sessions.map((s, i) => (
                        <tr key={i}>
                          <td className="admin-cell-muted">{fmtDateTime(s.started_at)}</td>
                          <td>{modeLabels[s.mode] || s.mode || '—'}</td>
                          <td className="admin-cell-muted">{bookLabels[s.book_id] || s.book_id || '—'}</td>
                          <td className="admin-cell-muted">{fmtChapterId(s.chapter_id)}</td>
                          <td>{s.words_studied}</td>
                          <td style={{ color: '#10b981' }}>{s.correct_count}</td>
                          <td style={{ color: '#ef4444' }}>{s.wrong_count}</td>
                          <td><span className={`admin-accuracy ${s.accuracy >= 80 ? 'good' : s.accuracy >= 60 ? 'mid' : s.accuracy > 0 ? 'low' : ''}`}>{s.accuracy > 0 ? `${s.accuracy}%` : '—'}</span></td>
                          <td>{fmtSeconds(s.duration_seconds)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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

