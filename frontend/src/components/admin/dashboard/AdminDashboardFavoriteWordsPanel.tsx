import {
  bookLabels,
  fmtChapterId,
  fmtDateTime,
  type UserDetail,
} from './AdminDashboard.types'
import {
  downloadFavoriteWordsExport,
  type FavoriteWordExportFormat,
} from './adminFavoriteWordsExport'

interface AdminDashboardFavoriteWordsPanelProps {
  favoriteWords: UserDetail['favorite_words']
  username: string
}

function resolveBookLabel(word: UserDetail['favorite_words'][number]) {
  return bookLabels[word.source_book_id || ''] || word.source_book_title || word.source_book_id || '—'
}

function resolveChapterLabel(word: UserDetail['favorite_words'][number]) {
  if (word.source_chapter_title) return word.source_chapter_title
  if (word.source_chapter_id) return fmtChapterId(word.source_chapter_id)
  return '—'
}

export function AdminDashboardFavoriteWordsPanel({
  favoriteWords,
  username,
}: AdminDashboardFavoriteWordsPanelProps) {
  const handleExport = (format: FavoriteWordExportFormat) => {
    downloadFavoriteWordsExport(favoriteWords, username, format)
  }

  if (favoriteWords.length === 0) {
    return <div className="admin-empty">暂无收藏单词</div>
  }

  return (
    <>
      <div className="admin-detail-summary admin-detail-summary--row">
        <span>共 {favoriteWords.length} 个收藏词，支持导出 CSV、TXT、JSON</span>
        <div className="admin-detail-actions">
          <button className="admin-detail-action-btn is-primary" onClick={() => handleExport('csv')}>导出 CSV</button>
          <button className="admin-detail-action-btn" onClick={() => handleExport('txt')}>导出 TXT</button>
          <button className="admin-detail-action-btn" onClick={() => handleExport('json')}>导出 JSON</button>
        </div>
      </div>
      <table className="admin-detail-table admin-detail-table--favorite-words">
        <thead>
          <tr>
            <th>单词</th>
            <th>音标</th>
            <th>词性</th>
            <th>释义</th>
            <th>来源词书</th>
            <th>来源章节</th>
            <th>收藏时间</th>
          </tr>
        </thead>
        <tbody>
          {favoriteWords.map((word, index) => (
            <tr key={`${word.normalized_word}-${index}`}>
              <td><strong>{word.word}</strong></td>
              <td className="admin-cell-muted">{word.phonetic || '—'}</td>
              <td className="admin-cell-muted">{word.pos || '—'}</td>
              <td className="admin-cell-ellipsis admin-cell-ellipsis--wide" title={word.definition}>{word.definition || '—'}</td>
              <td className="admin-cell-ellipsis" title={resolveBookLabel(word)}>{resolveBookLabel(word)}</td>
              <td className="admin-cell-muted">{resolveChapterLabel(word)}</td>
              <td className="admin-cell-muted">{fmtDateTime(word.created_at || word.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
