import type {
  AdminAssetMnemonicStatus,
  AdminAssetSummary,
  AdminAssetWord,
} from './AdminDashboard.types'

interface AdminAssetsPanelProps {
  assets: AdminAssetWord[]
  total: number
  page: number
  pages: number
  search: string
  bookId: string
  mnemonicStatus: AdminAssetMnemonicStatus
  summary: AdminAssetSummary | null
  loading: boolean
  onSearchSubmit: () => void
  onSearchClear: () => void
  onSearchChange: (value: string) => void
  onBookChange: (value: string) => void
  onMnemonicStatusChange: (value: AdminAssetMnemonicStatus) => void
  onPageChange: (page: number) => void
}

const mnemonicStatusOptions: Array<{ value: AdminAssetMnemonicStatus; label: string }> = [
  { value: 'all', label: '全部助记' },
  { value: 'with_mnemonic', label: '已有助记' },
  { value: 'missing_mnemonic', label: '缺少助记' },
]

function buildVisiblePages(page: number, pages: number) {
  const start = Math.max(1, page - 2)
  const end = Math.min(pages, page + 2)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
}

export function AdminAssetsPanel({
  assets,
  total,
  page,
  pages,
  search,
  bookId,
  mnemonicStatus,
  summary,
  loading,
  onSearchSubmit,
  onSearchClear,
  onSearchChange,
  onBookChange,
  onMnemonicStatusChange,
  onPageChange,
}: AdminAssetsPanelProps) {
  const visiblePages = buildVisiblePages(page, pages)

  return (
    <div className="admin-assets">
      <form className="admin-search-row admin-assets-toolbar" onSubmit={e => { e.preventDefault(); onSearchSubmit() }}>
        <div className="admin-assets-toolbar-main">
          <input
            className="admin-search-input admin-assets-search"
            placeholder="搜索单词、释义或助记..."
            value={search}
            onChange={e => onSearchChange(e.target.value)}
          />
          <select className="admin-filter-select" value={bookId} onChange={e => onBookChange(e.target.value)}>
            <option value="">全部词书</option>
            <option value="ielts_reading_premium">雅思阅读高频词汇</option>
            <option value="ielts_listening_premium">雅思听力高频词汇</option>
          </select>
          <select
            className="admin-filter-select"
            value={mnemonicStatus}
            onChange={e => onMnemonicStatusChange(e.target.value as AdminAssetMnemonicStatus)}
          >
            {mnemonicStatusOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <button type="submit" className="admin-search-btn">搜索</button>
          {(search || bookId || mnemonicStatus !== 'all') && (
            <button type="button" className="admin-search-clear" onClick={onSearchClear}>清除</button>
          )}
        </div>
        <span className="admin-total-hint">
          共 {total} 条
          {summary ? ` · 已配 ${summary.with_mnemonic} · 缺失 ${summary.missing_mnemonic}` : ''}
        </span>
      </form>

      <div className="admin-table-wrap">
        {loading ? (
          <div className="admin-loading">正在加载资产...</div>
        ) : (
          <table className="admin-table admin-assets-table">
            <thead>
              <tr>
                <th>单词</th>
                <th>音标 / 词性</th>
                <th>释义</th>
                <th>助记类型</th>
                <th>助记片段</th>
              </tr>
            </thead>
            <tbody>
              {assets.length === 0 ? (
                <tr><td colSpan={5} className="admin-empty-cell">暂无资产</td></tr>
              ) : assets.map(item => (
                <tr key={item.id}>
                  <td data-label="单词">
                    <strong className="admin-asset-word">{item.word}</strong>
                  </td>
                  <td data-label="音标 / 词性">
                    <div className="admin-asset-meta">
                      <span>{item.phonetic || '—'}</span>
                      <em>{item.pos || '—'}</em>
                    </div>
                  </td>
                  <td data-label="释义" className="admin-asset-definition">{item.definition || '暂无释义'}</td>
                  <td data-label="助记类型">
                    {item.memory_text ? (
                      <span className="admin-asset-memory-badge">{item.memory_badge || '助记'}</span>
                    ) : (
                      <span className="admin-asset-missing">未生成</span>
                    )}
                  </td>
                  <td data-label="助记片段" className="admin-asset-memory-cell">
                    {item.memory_text ? (
                      <span className="admin-asset-memory-text">{item.memory_text}</span>
                    ) : (
                      <span className="admin-asset-missing">暂无片段</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {pages > 1 && (
        <div className="admin-pagination">
          <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>上一页</button>
          {visiblePages[0] > 1 && (
            <>
              <button onClick={() => onPageChange(1)}>1</button>
              {visiblePages[0] > 2 && <span className="admin-pagination-ellipsis">...</span>}
            </>
          )}
          {visiblePages.map(p => (
            <button key={p} className={p === page ? 'active' : ''} onClick={() => onPageChange(p)}>{p}</button>
          ))}
          {visiblePages[visiblePages.length - 1] < pages && (
            <>
              {visiblePages[visiblePages.length - 1] < pages - 1 && <span className="admin-pagination-ellipsis">...</span>}
              <button onClick={() => onPageChange(pages)}>{pages}</button>
            </>
          )}
          <button disabled={page >= pages} onClick={() => onPageChange(page + 1)}>下一页</button>
        </div>
      )}
    </div>
  )
}
