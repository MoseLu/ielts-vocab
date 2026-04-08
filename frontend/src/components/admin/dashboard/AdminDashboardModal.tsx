import {
  AdminDetailTab,
  buildSessionContent,
  buildSessionWordSample,
  fmtChapterId,
  fmtDate,
  fmtDateTime,
  fmtSeconds,
  fmtSessionTimeRange,
  modeLabels,
  bookLabels,
  type UserDetail,
  type WrongWordsSort,
} from './AdminDashboard.types'
import { AdminDashboardFavoriteWordsPanel } from './AdminDashboardFavoriteWordsPanel'
import { MiniBarChart } from './AdminDashboardPrimitives'

type BookProgress = UserDetail['book_progress'][number]

const HIDDEN_PROGRESS_BOOK_IDS = new Set(['ielts_confusable_match'])

function getBookProgressPercent(progress: BookProgress) {
  if (progress.total_words > 0) {
    return Math.max(0, Math.min(progress.progress_percent, 100))
  }

  if (progress.total_chapters > 0) {
    return Math.max(0, Math.min(Math.round(progress.completed_chapters / progress.total_chapters * 100), 100))
  }

  return 0
}

interface AdminDashboardModalProps {
  selectedUser: UserDetail
  isFullscreen: boolean
  detailTab: AdminDetailTab
  detailDateFrom: string
  detailDateTo: string
  detailMode: string
  detailWrongWordsSort: WrongWordsSort
  currentUserId?: number
  currentUserAvatarUrl?: string | null
  onClose: () => void
  onToggleFullscreen: () => void
  onSetDetailTab: (value: AdminDetailTab) => void
  onSetDetailDateFrom: (value: string) => void
  onSetDetailDateTo: (value: string) => void
  onSetDetailMode: (value: string) => void
  onSetDetailWrongWordsSort: (value: WrongWordsSort) => void
  onFetchUserDetail: (userId: number, opts?: {
    dateFrom?: string
    dateTo?: string
    mode?: string
    bookId?: string
    wrongWordsSort?: WrongWordsSort
  }) => void
}

function resolveDisplayAvatarUrl(
  avatarUrl: string | null | undefined,
  userId: number,
  currentUserId?: number,
  currentUserAvatarUrl?: string | null,
) {
  if (avatarUrl) return avatarUrl
  if (currentUserId === userId && currentUserAvatarUrl) return currentUserAvatarUrl
  return null
}

export function AdminDashboardModal({
  selectedUser,
  isFullscreen,
  detailTab,
  detailDateFrom,
  detailDateTo,
  detailMode,
  detailWrongWordsSort,
  currentUserId,
  currentUserAvatarUrl,
  onClose,
  onToggleFullscreen,
  onSetDetailTab,
  onSetDetailDateFrom,
  onSetDetailDateTo,
  onSetDetailMode,
  onSetDetailWrongWordsSort,
  onFetchUserDetail,
}: AdminDashboardModalProps) {
  const visibleBookProgress = selectedUser.book_progress.filter(book => !HIDDEN_PROGRESS_BOOK_IDS.has(book.book_id))
  const displayAvatarUrl = resolveDisplayAvatarUrl(
    selectedUser.user.avatar_url,
    selectedUser.user.id,
    currentUserId,
    currentUserAvatarUrl,
  )

  const modalHeader = (
    <div className="admin-modal-header">
      <div className="admin-modal-user-info">
        {displayAvatarUrl ? (
          <img src={displayAvatarUrl} alt="" className="admin-modal-avatar" />
        ) : (
          <div className="admin-avatar-placeholder large">
            {(selectedUser.user.username || '?')[0].toUpperCase()}
          </div>
        )}
        <div className="admin-modal-user-meta-row">
          <span className={`admin-modal-username-hl${selectedUser.user.is_admin ? ' admin-modal-username-hl--admin' : ''}`}>
            {selectedUser.user.username}
          </span>
          <span className="admin-modal-meta-sep">·</span>
          <span className="admin-modal-meta-item">{selectedUser.user.email || '未绑定邮箱'}</span>
          <span className="admin-modal-meta-sep">·</span>
          <span className="admin-modal-meta-item">注册于 {fmtDate(selectedUser.user.created_at)}</span>
        </div>
      </div>
      <div className="admin-modal-actions">
        <button
          className="admin-modal-toggle-fs"
          onClick={onToggleFullscreen}
          title={isFullscreen ? '退出全屏' : '全屏显示'}
        >
          {isFullscreen ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
              <polyline points="4 14 10 14 10 20"/>
              <polyline points="20 10 14 10 14 4"/>
              <line x1="10" y1="14" x2="3" y2="21"/>
              <line x1="21" y1="3" x2="14" y2="10"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
              <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
              <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
            </svg>
          )}
        </button>
        <button className="admin-modal-close" onClick={onClose}>
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
      <input type="date" className="admin-filter-date" value={detailDateFrom} onChange={e => onSetDetailDateFrom(e.target.value)} title="开始日期" />
      <span className="admin-filter-separator">至</span>
      <input type="date" className="admin-filter-date" value={detailDateTo} onChange={e => onSetDetailDateTo(e.target.value)} title="结束日期" />
      <select className="admin-filter-select" value={detailMode} onChange={e => onSetDetailMode(e.target.value)}>
        <option value="">全部模式</option>
        {Object.entries(modeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <button className="admin-filter-apply" onClick={() => onFetchUserDetail(selectedUser.user.id, {
        dateFrom: detailDateFrom,
        dateTo: detailDateTo,
        mode: detailMode,
        wrongWordsSort: detailWrongWordsSort,
      })}>查询</button>
      <button className="admin-filter-reset" onClick={() => {
        onSetDetailDateFrom('')
        onSetDetailDateTo('')
        onSetDetailMode('')
        onFetchUserDetail(selectedUser.user.id, { wrongWordsSort: detailWrongWordsSort })
      }}>重置</button>
    </div>
  )

  const modalTabs = (
    <div className="admin-detail-tabs">
      {(['chart', 'chapter_daily', 'sessions', 'progress', 'favorite_words', 'wrong_words'] as const).map(t => (
        <button key={t} className={`admin-detail-tab ${detailTab === t ? 'active' : ''}`} onClick={() => onSetDetailTab(t)}>
          {{ chart: '每日趋势', chapter_daily: '章节明细', sessions: '学习明细', progress: '词书进度', favorite_words: '收藏词书', wrong_words: '错词本' }[t]}
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
                valueKey="minutes"
                labelKey="day"
                tone="indigo"
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
          {visibleBookProgress.length === 0 ? (
            <div className="admin-empty">暂无学习进度</div>
          ) : (
            <table className="admin-detail-table">
              <thead>
                <tr>
                  <th>词书</th>
                  <th>学习进度</th>
                  <th>章节</th>
                  <th>答题表现</th>
                  <th>状态</th>
                  <th>更新时间</th>
                </tr>
              </thead>
              <tbody>
                {visibleBookProgress.map((b, i) => {
                  const tot = b.correct_count + b.wrong_count
                  const acc = tot > 0 ? Math.round(b.correct_count / tot * 100) : 0
                  const progressPercent = getBookProgressPercent(b)
                  const learnedWords = b.total_words > 0 ? Math.min(b.current_index, b.total_words) : b.current_index
                  return (
                    <tr key={i}>
                      <td>{bookLabels[b.book_id] || b.book_id}</td>
                      <td>
                        <div className="admin-book-progress">
                          <div className="admin-book-progress__meta">
                            <strong>{progressPercent}%</strong>
                            <span>{b.total_words > 0 ? `${learnedWords} / ${b.total_words} 词` : `${learnedWords} 词`}</span>
                          </div>
                          <div className="admin-book-progress__track" aria-hidden="true">
                            <span className="admin-book-progress__fill" style={{ width: `${progressPercent}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="admin-cell-muted">
                        {b.total_chapters > 0 ? `${b.completed_chapters} / ${b.total_chapters} 章` : '—'}
                      </td>
                      <td>
                        <div className="admin-book-performance">
                          <span className="admin-cell-positive">对 {b.correct_count}</span>
                          <span className="admin-cell-negative">错 {b.wrong_count}</span>
                          <span className="admin-cell-muted">{tot > 0 ? `准确率 ${acc}%` : '暂无答题记录'}</span>
                        </div>
                      </td>
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
      {detailTab === 'favorite_words' && (
        <div>
          <AdminDashboardFavoriteWordsPanel
            favoriteWords={selectedUser.favorite_words}
            username={selectedUser.user.username}
          />
        </div>
      )}
      {detailTab === 'wrong_words' && (
        <div>
          {selectedUser.wrong_words.length === 0 ? (
            <div className="admin-empty">暂无错词</div>
          ) : (
            <>
              <div className="admin-detail-summary admin-detail-summary--row">
                <span>
                  共 {selectedUser.user.stats.wrong_words_count} 个错词，显示前 {selectedUser.wrong_words.length} 个
                  {detailWrongWordsSort === 'last_error' ? '，当前按最近错误排序' : '，当前按错误次数排序'}
                </span>
                <label className="admin-detail-inline-filter">
                  <span className="admin-detail-inline-filter__label">错词排序</span>
                  <select
                    aria-label="错词排序"
                    className="admin-filter-select"
                    value={detailWrongWordsSort}
                    onChange={e => {
                      const nextSort = e.target.value as WrongWordsSort
                      onSetDetailWrongWordsSort(nextSort)
                      onFetchUserDetail(selectedUser.user.id, {
                        dateFrom: detailDateFrom,
                        dateTo: detailDateTo,
                        mode: detailMode,
                        wrongWordsSort: nextSort,
                      })
                    }}
                  >
                    <option value="last_error">最近错误时间</option>
                    <option value="wrong_count">错误次数</option>
                  </select>
                </label>
              </div>
              <table className="admin-detail-table admin-detail-table--wrong-words">
                <thead><tr><th>单词</th><th>音标</th><th>词性</th><th>释义</th><th>错误次数</th><th>最近错误</th></tr></thead>
                <tbody>
                  {selectedUser.wrong_words.map((w, i) => (
                    <tr key={i}>
                      <td><strong>{w.word}</strong></td>
                      <td className="admin-cell-muted">{w.phonetic || '—'}</td>
                      <td className="admin-cell-muted">{w.pos || '—'}</td>
                      <td className="admin-cell-ellipsis admin-cell-ellipsis--wide" title={w.definition}>{w.definition}</td>
                      <td><span className={`admin-wrong-count ${w.wrong_count >= 5 ? 'high' : w.wrong_count >= 3 ? 'mid' : ''}`}>{w.wrong_count}次</span></td>
                      <td className="admin-cell-muted">{fmtDateTime(w.last_wrong_at || w.updated_at)}</td>
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
      onClick={e => !isFullscreen && e.target === e.currentTarget && onClose()}
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
              <div className="admin-modal-body">{modalBodyContent}</div>
            </div>
          </div>
        ) : (
          <>
            {modalStats}
            {modalFilters}
            {modalTabs}
            <div className="admin-modal-body">{modalBodyContent}</div>
          </>
        )}
      </div>
    </div>
  )
}
