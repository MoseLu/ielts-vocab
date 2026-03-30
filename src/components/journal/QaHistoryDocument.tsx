import { renderJournalMarkdown } from '../../lib/journalMarkdown'
import type { LearningNote } from '../../lib/schemas'

interface QaHistoryDocumentProps {
  notes: LearningNote[]
  notesLoading: boolean
  notesError: string
  notesTotal: number
  selectedNote: LearningNote | null
  cursorStack: (number | null)[]
  hasMore: boolean
  onSelectNote: (noteId: number) => void
  onPreviousPage: () => void
  onNextPage: () => void
  formatDateTime: (iso: string) => string
  toPlainTextSnippet: (text: string, maxLen?: number) => string
}

export default function QaHistoryDocument({
  notes,
  notesLoading,
  notesError,
  notesTotal,
  selectedNote,
  cursorStack,
  hasMore,
  onSelectNote,
  onPreviousPage,
  onNextPage,
  formatDateTime,
  toPlainTextSnippet,
}: QaHistoryDocumentProps) {
  return (
    <div className="journal-doc-shell journal-doc-shell--notes">
      <aside className="journal-doc-sidebar">
        <div className="journal-doc-sidebar-head">
          <div className="journal-doc-sidebar-copy">
            <span className="journal-doc-sidebar-kicker">Q&A History</span>
            <h2 className="journal-doc-sidebar-title">问答历史</h2>
            <p className="journal-doc-sidebar-subtitle">按时间查看提问上下文与 AI 回答。</p>
          </div>
          <span className="journal-doc-sidebar-stat">{notesTotal} 条</span>
        </div>

        <div className="journal-doc-sidebar-body">
          {notesLoading ? (
            <div className="journal-loading">加载中...</div>
          ) : notesError ? (
            <div className="journal-error">{notesError}</div>
          ) : notes.length === 0 ? (
            <div className="journal-empty journal-empty--sidebar">
              <p>暂无问答记录。</p>
              <p>学习时向 AI 助手提问后会自动出现在这里。</p>
            </div>
          ) : (
            <div className="journal-doc-list">
              {notes.map(note => (
                <button
                  key={note.id}
                  className={`journal-doc-item ${selectedNote?.id === note.id ? 'active' : ''}`}
                  onClick={() => onSelectNote(note.id)}
                >
                  <span className="journal-doc-item-eyebrow">{formatDateTime(note.created_at)}</span>
                  <strong className="journal-doc-item-title">{toPlainTextSnippet(note.question, 44)}</strong>
                  <span className="journal-doc-item-copy">{toPlainTextSnippet(note.answer, 88)}</span>
                  <span className="journal-doc-item-meta">
                    {note.word_context ? `单词：${note.word_context}` : '无单词上下文'}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {notes.length > 0 && (cursorStack.length > 1 || hasMore) && (
          <div className="journal-pagination">
            <button
              className="journal-page-btn"
              disabled={cursorStack.length <= 1}
              onClick={onPreviousPage}
            >
              上一页
            </button>
            <span className="journal-page-info">第 {cursorStack.length} 页</span>
            <button
              className="journal-page-btn"
              disabled={!hasMore}
              onClick={onNextPage}
            >
              下一页
            </button>
          </div>
        )}
      </aside>

      <article className="journal-doc-main journal-doc-main--notes">
        <div className="journal-doc-main-toolbar">
          <span className="journal-doc-breadcrumb">学习日志 / 问答历史</span>
        </div>

        <div className="journal-doc-main-scroll">
          {selectedNote ? (
            <>
              <header className="journal-doc-hero journal-doc-hero--note">
                <div className="journal-doc-hero-topline">
                  {selectedNote.word_context ? (
                    <span className="journal-word-badge">{selectedNote.word_context}</span>
                  ) : (
                    <span className="journal-word-none">无单词上下文</span>
                  )}
                  <span className="journal-doc-meta-chip">{formatDateTime(selectedNote.created_at)}</span>
                </div>
                <h1 className="journal-doc-title journal-doc-title--note">{selectedNote.question}</h1>
                <p className="journal-doc-lead">
                  保留提问上下文，并将 AI 回答作为可阅读的长文档内容展示。
                </p>
              </header>

              <div className="journal-note-detail-grid">
                <section className="journal-note-detail-card">
                  <span className="journal-note-detail-label">提问内容</span>
                  <div className="journal-note-detail-question">{selectedNote.question}</div>
                </section>

                <section className="journal-note-detail-card journal-note-detail-card--answer">
                  <span className="journal-note-detail-label">AI 回答</span>
                  <div
                    className="journal-note-detail-answer markdown-content"
                    dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(selectedNote.answer) }}
                  />
                </section>
              </div>
            </>
          ) : (
            <div className="journal-empty journal-empty--main">
              <p>左侧没有可阅读的问答历史。</p>
            </div>
          )}
        </div>
      </article>
    </div>
  )
}
