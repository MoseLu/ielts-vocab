import { PageSkeleton, SegmentedControl } from '../../ui'
import { AdminTableSkeleton, MiniBarChart, StatCard } from './AdminDashboardPrimitives'
import {
  bookLabels,
  fmtDate,
  fmtDateTime,
  fmtSeconds,
  modeLabels,
  type AdminTab,
  type AdminUser,
  type AdminWordFeedback,
  type Overview,
  wordFeedbackSourceLabels,
} from './AdminDashboard.types'

interface AdminDashboardViewProps {
  tab: AdminTab
  overview: Overview | null
  overviewLoading: boolean
  users: AdminUser[]
  feedbackItems: AdminWordFeedback[]
  feedbackTotal: number
  total: number
  page: number
  pages: number
  search: string
  sort: string
  order: 'asc' | 'desc'
  currentUserId?: number
  currentUserAvatarUrl?: string | null
  loading: boolean
  feedbackLoading: boolean
  error: string
  onDismissError: () => void
  onTabChange: (value: AdminTab) => void
  onSearchSubmit: () => void
  onSearchClear: () => void
  onSearchChange: (value: string) => void
  onSort: (column: string) => void
  onPageChange: (page: number) => void
  onSelectUser: (userId: number) => void
}

const DEFAULT_AVATAR_URL = '/default-avatar.jpg'

function resolveDisplayAvatarUrl(
  avatarUrl: string | null | undefined,
  userId: number,
  currentUserId?: string | number,
  currentUserAvatarUrl?: string | null,
) {
  if (avatarUrl) return avatarUrl
  if (
    currentUserId != null &&
    String(currentUserId) === String(userId)
  ) return currentUserAvatarUrl || DEFAULT_AVATAR_URL
  return null
}

function SortIcon({ current, order, column }: { current: string; order: 'asc' | 'desc'; column: string }) {
  return (
    <span className={`admin-sort-icon ${current === column ? 'is-active' : ''}`}>
      {current === column ? (order === 'desc' ? '▼' : '▲') : '⇅'}
    </span>
  )
}

export function AdminDashboardView({
  tab,
  overview,
  overviewLoading,
  users,
  feedbackItems,
  feedbackTotal,
  total,
  page,
  pages,
  search,
  sort,
  order,
  currentUserId,
  currentUserAvatarUrl,
  loading,
  feedbackLoading,
  error,
  onDismissError,
  onTabChange,
  onSearchSubmit,
  onSearchClear,
  onSearchChange,
  onSort,
  onPageChange,
  onSelectUser,
}: AdminDashboardViewProps) {
  return (
    <div className="admin-dashboard">
      {error && (
        <div className="admin-error" onClick={onDismissError}>
          {error} <span className="admin-error-dismiss">（点击关闭）</span>
        </div>
      )}

      <SegmentedControl
        className="admin-tabs"
        ariaLabel="管理台导航"
        value={tab}
        onChange={onTabChange}
        options={[
          { value: 'overview', label: '平台概览' },
          { value: 'users', label: '用户管理', badge: total },
          { value: 'feedback', label: '问题反馈' },
        ]}
      />

      {tab === 'overview' && (
        <div className="admin-overview">
          {overviewLoading && !overview && <PageSkeleton variant="admin" />}
          {overview && (
            <>
              <div className="admin-stat-grid">
                <StatCard label="总用户数" value={overview.total_users} sub={`今日新增 ${overview.new_users_today}`} tone="indigo" />
                <StatCard label="今日活跃" value={overview.active_users_today} sub={`7日活跃 ${overview.active_users_7d}`} tone="green" />
                <StatCard label="总学习时长" value={fmtSeconds(overview.total_study_seconds)} sub={`共 ${overview.total_sessions} 次练习`} tone="amber" />
                <StatCard label="总学习单词" value={overview.total_words_studied.toLocaleString()} sub={`平均准确率 ${overview.avg_accuracy}%`} tone="blue" />
              </div>

              <div className="admin-chart-section">
                <div className="admin-section-title">近14天每日学习趋势</div>
                {overview.daily_activity.length === 0 ? (
                  <div className="admin-empty">暂无数据</div>
                ) : (
                  <div className="admin-chart-wrapper">
                    <div className="admin-summary-heading admin-summary-heading--compact">
                      <span className="admin-summary-heading-text">练习次数</span>
                    </div>
                    <MiniBarChart data={overview.daily_activity} valueKey="sessions" labelKey="day" tone="indigo" />
                    <div className="admin-chart-labels">
                      {overview.daily_activity.map((d, i) => (
                        <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>
                      ))}
                    </div>
                    <div className="admin-summary-heading">
                      <span className="admin-summary-heading-text">学习单词数</span>
                    </div>
                    <MiniBarChart data={overview.daily_activity} valueKey="words" labelKey="day" tone="green" />
                    <div className="admin-chart-labels">
                      {overview.daily_activity.map((d, i) => (
                        <span key={i} className="admin-chart-label">{d.day.slice(5)}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="admin-two-col">
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

      {tab === 'users' && (
        <div className="admin-users">
          <form className="admin-search-row" onSubmit={e => { e.preventDefault(); onSearchSubmit() }}>
            <input
              className="admin-search-input"
              placeholder="搜索用户名或邮箱..."
              value={search}
              onChange={e => onSearchChange(e.target.value)}
            />
            <button type="submit" className="admin-search-btn">搜索</button>
            {search && (
              <button type="button" className="admin-search-clear" onClick={onSearchClear}>清除</button>
            )}
            <span className="admin-total-hint">共 {total} 位用户</span>
          </form>

          <div className="admin-table-wrap">
            {loading ? (
              <AdminTableSkeleton />
            ) : (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th onClick={() => onSort('username')} className="sortable">用户名 <SortIcon current={sort} order={order} column="username" /></th>
                    <th>邮箱</th>
                    <th onClick={() => onSort('study_time')} className="sortable">学习时长 <SortIcon current={sort} order={order} column="study_time" /></th>
                    <th onClick={() => onSort('words_studied')} className="sortable">学习单词 <SortIcon current={sort} order={order} column="words_studied" /></th>
                    <th onClick={() => onSort('accuracy')} className="sortable">准确率 <SortIcon current={sort} order={order} column="accuracy" /></th>
                    <th>错词数</th>
                    <th>7日练习</th>
                    <th onClick={() => onSort('last_active')} className="sortable">最近活跃 <SortIcon current={sort} order={order} column="last_active" /></th>
                    <th onClick={() => onSort('created_at')} className="sortable">注册时间 <SortIcon current={sort} order={order} column="created_at" /></th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr><td colSpan={9} className="admin-empty-cell">暂无数据</td></tr>
                  ) : users.map(u => {
                    const displayAvatarUrl = resolveDisplayAvatarUrl(
                      u.avatar_url,
                      u.id,
                      currentUserId,
                      currentUserAvatarUrl,
                    )

                    return (
                      <tr key={u.id} className="admin-user-row" onClick={() => onSelectUser(u.id)}>
                        <td data-label="用户">
                          <div className="admin-user-name-cell">
                            {displayAvatarUrl ? (
                              <img src={displayAvatarUrl} alt="" className="admin-avatar" />
                            ) : (
                              <div className="admin-avatar-placeholder">{(u.username || '?')[0].toUpperCase()}</div>
                            )}
                            <span className={`admin-user-name${u.is_admin ? ' admin-user-name--admin' : ''}`}>{u.username}</span>
                          </div>
                        </td>
                        <td className="admin-cell-muted" data-label="邮箱">{u.email || '—'}</td>
                        <td data-label="学习时长">{fmtSeconds(u.stats.total_study_seconds)}</td>
                        <td data-label="学习单词">{u.stats.total_words_studied.toLocaleString()}</td>
                        <td data-label="准确率">
                          <span className={`admin-accuracy ${u.stats.accuracy >= 80 ? 'good' : u.stats.accuracy >= 60 ? 'mid' : u.stats.accuracy > 0 ? 'low' : ''}`}>
                            {u.stats.accuracy > 0 ? `${u.stats.accuracy}%` : '—'}
                          </span>
                        </td>
                        <td data-label="错词数">{u.stats.wrong_words_count > 0 ? u.stats.wrong_words_count : '—'}</td>
                        <td data-label="7日练习">
                          <span className={`admin-sessions-badge ${u.stats.recent_sessions_7d > 0 ? 'active' : ''}`}>
                            {u.stats.recent_sessions_7d > 0 ? `${u.stats.recent_sessions_7d}次` : '—'}
                          </span>
                        </td>
                        <td className="admin-cell-muted" data-label="最近活跃">{fmtDate(u.stats.last_active)}</td>
                        <td className="admin-cell-muted" data-label="注册时间">{fmtDate(u.created_at)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>

          {pages > 1 && (
            <div className="admin-pagination">
              <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>上一页</button>
              {Array.from({ length: pages }, (_, i) => i + 1).map(p => (
                <button key={p} className={p === page ? 'active' : ''} onClick={() => onPageChange(p)}>{p}</button>
              ))}
              <button disabled={page >= pages} onClick={() => onPageChange(page + 1)}>下一页</button>
            </div>
          )}
        </div>
      )}

      {tab === 'feedback' && (
        <div className="admin-feedback">
          <div className="admin-feedback-header">
            <div className="admin-section-title">最近单词卡片反馈</div>
            <span className="admin-total-hint">共 {feedbackTotal} 条</span>
          </div>

          <div className="admin-table-wrap">
            {feedbackLoading ? (
              <div className="admin-loading">正在加载反馈...</div>
            ) : (
              <table className="admin-table admin-feedback-table">
                <thead>
                  <tr>
                    <th>词汇</th>
                    <th>问题类型</th>
                    <th>用户</th>
                    <th>来源</th>
                    <th>上下文</th>
                    <th>提交时间</th>
                  </tr>
                </thead>
                <tbody>
                  {feedbackItems.length === 0 ? (
                    <tr><td colSpan={6} className="admin-empty-cell">暂无反馈</td></tr>
                  ) : feedbackItems.map(item => (
                    <tr key={item.id}>
                      <td data-label="词汇">
                        <div className="admin-feedback-word">
                          <strong>{item.word}</strong>
                          <span>{[item.phonetic, item.pos].filter(Boolean).join(' ') || '—'}</span>
                          <em>{item.definition || '暂无释义'}</em>
                        </div>
                      </td>
                      <td data-label="问题类型">
                        <div className="admin-feedback-tags">
                          {(item.feedback_type_labels.length ? item.feedback_type_labels : item.feedback_types).map(label => (
                            <span key={`${item.id}-${label}`} className="admin-feedback-tag">{label}</span>
                          ))}
                        </div>
                      </td>
                      <td data-label="用户">
                        <div className="admin-feedback-user">
                          <strong>{item.username}</strong>
                          <span>{item.email || '—'}</span>
                        </div>
                      </td>
                      <td data-label="来源">
                        {wordFeedbackSourceLabels[item.source] || item.source}
                      </td>
                      <td data-label="上下文">
                        <div className="admin-feedback-context">
                          <strong>{[item.source_book_title, item.source_chapter_title].filter(Boolean).join(' · ') || '未标注词书来源'}</strong>
                          <span>{item.example_en || item.comment || item.example_zh || '未附带例句'}</span>
                        </div>
                      </td>
                      <td className="admin-cell-muted" data-label="提交时间">{fmtDateTime(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
