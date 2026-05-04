import { Modal } from '../../ui'
import type { useWrongWordsCustomBookExport } from '../../../composables/errors/page/useWrongWordsCustomBookExport'

type CustomBookExportState = ReturnType<typeof useWrongWordsCustomBookExport>

interface ErrorsCustomBookExportModalProps {
  exportState: CustomBookExportState
}

export function ErrorsCustomBookExportModal({ exportState }: ErrorsCustomBookExportModalProps) {
  const {
    isOpen,
    phase,
    books,
    selectedBookId,
    loadingBooks,
    saving,
    error,
    chapterTitle,
    wordCount,
    savedTarget,
    setSelectedBookId,
    close,
    save,
    openQuickMemory,
  } = exportState

  return (
    <Modal
      isOpen={isOpen}
      onClose={close}
      title={phase === 'success' ? '已保存到自定义词书' : '保存到自定义词书'}
      size="sm"
    >
      {phase === 'success' ? (
        <div className="errors-custom-book-modal">
          <p className="errors-custom-book-summary">
            已生成章节「{chapterTitle}」。
            {savedTarget?.rejectedCount ? `有 ${savedTarget.rejectedCount} 个词未导入。` : ''}
          </p>
          <div className="ui-modal__actions">
            <button type="button" className="errors-clear-btn" onClick={close}>
              留在错词本
            </button>
            <button type="button" className="errors-practice-btn" onClick={openQuickMemory}>
              前往快速记忆
            </button>
          </div>
        </div>
      ) : (
        <div className="errors-custom-book-modal">
          <p className="errors-custom-book-summary">
            将 {wordCount} 个词保存为章节「{chapterTitle}」。
          </p>

          {loadingBooks ? (
            <p className="errors-custom-book-muted">正在加载自定义词书...</p>
          ) : books.length === 0 ? (
            <p className="errors-custom-book-muted">暂无可选自定义词书，请先创建一本自定义词书。</p>
          ) : (
            <div className="errors-custom-book-list" role="radiogroup" aria-label="选择自定义词书">
              {books.map(book => (
                <label key={book.id} className="errors-custom-book-option">
                  <input
                    type="radio"
                    name="errors-custom-book"
                    aria-label={book.title || book.id}
                    checked={selectedBookId === book.id}
                    onChange={() => setSelectedBookId(book.id)}
                  />
                  <span>
                    <strong>{book.title || book.id}</strong>
                    <small>{Math.max(0, Number(book.word_count) || 0)} 词</small>
                  </span>
                </label>
              ))}
            </div>
          )}

          {error && <div className="errors-custom-book-error">{error}</div>}

          <div className="ui-modal__actions">
            <button type="button" className="errors-clear-btn" onClick={close}>
              取消
            </button>
            <button
              type="button"
              className="errors-practice-btn"
              disabled={saving || loadingBooks || !selectedBookId || wordCount === 0}
              onClick={save}
            >
              {saving ? '保存中...' : '保存为章节'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
