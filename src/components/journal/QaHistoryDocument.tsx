import { Skeleton } from '../ui'
import { renderJournalMarkdown } from '../../lib/journalMarkdown'
import type {
  LearningNote,
  NoteMemoryTopic,
  NoteMemoryTopicRelatedNote,
} from '../../lib/schemas'

interface QaHistoryDocumentProps {
  notes: LearningNote[]
  memoryTopics?: NoteMemoryTopic[]
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

function normalizeTopicText(text: string | null | undefined): string {
  return (text || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[，。,.!?！？;:：]/g, '')
    .trim()
}

function topicKeyOf(note: LearningNote): string {
  const word = (note.word_context || '').trim().toLowerCase()
  if (word) return `word:${word}`
  return `question:${normalizeTopicText(note.question)}`
}

function toRelatedHistory(note: LearningNote): NoteMemoryTopicRelatedNote {
  return {
    id: note.id,
    question: note.question,
    answer: note.answer,
    word_context: note.word_context,
    created_at: note.created_at,
  }
}

function QaHistorySkeleton() {
  return (
    <div className="journal-doc-skeleton journal-doc-skeleton--notes" aria-hidden="true">
      <div className="journal-doc-skeleton-sidebar">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="journal-doc-skeleton-item">
            <Skeleton width="38%" height={12} />
            <Skeleton width="82%" height={15} />
            <Skeleton width="100%" height={13} />
            <Skeleton width="56%" height={12} />
          </div>
        ))}
      </div>
      <div className="journal-doc-skeleton-main">
        <Skeleton width="24%" height={12} />
        <Skeleton width="18%" height={24} />
        <Skeleton width="72%" height={16} />
        <div className="journal-doc-skeleton-note-grid">
          <div className="journal-doc-skeleton-note-card">
            <Skeleton width="32%" height={12} />
            <Skeleton width="100%" height={15} />
            <Skeleton width="94%" height={15} />
            <Skeleton width="66%" height={15} />
          </div>
          <div className="journal-doc-skeleton-note-card">
            <Skeleton width="26%" height={12} />
            {Array.from({ length: 6 }, (_, index) => (
              <Skeleton key={index} width={index === 5 ? '54%' : '100%'} height={14} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function QaHistoryDocument({
  notes,
  memoryTopics = [],
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
  const selectedTopicKey = selectedNote ? topicKeyOf(selectedNote) : ''
  const localRepeatedTopicNotes = selectedNote
    ? notes.filter(note => topicKeyOf(note) === selectedTopicKey)
    : []
  const matchedMemoryTopic = selectedNote
    ? memoryTopics.find(topic => topic.note_ids.includes(selectedNote.id))
    : undefined
  const relatedHistory = matchedMemoryTopic
    ? matchedMemoryTopic.related_notes.filter(note => note.id !== selectedNote?.id)
    : selectedNote
      ? notes
          .filter(note => note.id !== selectedNote.id && topicKeyOf(note) === selectedTopicKey)
          .map(toRelatedHistory)
      : []

  const repeatCount = matchedMemoryTopic?.count ?? localRepeatedTopicNotes.length
  const memorySummary = matchedMemoryTopic?.follow_up_hint || (
    selectedNote?.word_context
      ? `围绕 ${selectedNote.word_context} 的相关提问会优先成为 AI 的记忆线索。`
      : '当前问题会和相似提问自动归并到同一个主题下。'
  )

  if (notesLoading) {
    return (
      <div className="journal-doc-shell journal-doc-shell--notes">
        <QaHistorySkeleton />
      </div>
    )
  }

  return (
    <div className="journal-doc-shell journal-doc-shell--notes">
      <aside className="journal-doc-sidebar">
        <div className="journal-doc-sidebar-head">
          <div className="journal-doc-sidebar-copy">
            <span className="journal-doc-sidebar-kicker">Q&amp;A History</span>
            <h2 className="journal-doc-sidebar-title">问答历史</h2>
            <p className="journal-doc-sidebar-subtitle">按时间查看提问上下文和 AI 回答。</p>
          </div>
          <span className="journal-doc-sidebar-stat">{notesTotal} 条</span>
        </div>

        <div className="journal-doc-sidebar-body">
          {notesError ? (
            <div className="journal-error">{notesError}</div>
          ) : notes.length === 0 ? (
            <div className="journal-empty journal-empty--sidebar">
              <p>暂无问答记录。</p>
              <p>学习时向 AI 助手提问后，记录会自动出现在这里。</p>
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
                  保留提问上下文，并将 AI 回答整理成可阅读的知识记录。
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

                <section className="journal-note-detail-card journal-note-detail-card--memory">
                  <span className="journal-note-detail-label">重复追问主题</span>
                  <div className="journal-note-memory-summary">
                    <strong>{`当前主题已追问 ${repeatCount} 次`}</strong>
                    <span>{memorySummary}</span>
                  </div>
                </section>

                <section className="journal-note-detail-card journal-note-detail-card--memory">
                  <span className="journal-note-detail-label">相关历史问题</span>
                  {relatedHistory.length > 0 ? (
                    <ul className="journal-note-memory-list">
                      {relatedHistory.slice(0, 4).map(note => (
                        <li key={note.id}>
                          <strong>{note.question}</strong>
                          <span>{note.created_at ? formatDateTime(note.created_at) : '时间未知'}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="journal-note-memory-empty">当前主题还没有更多历史追问。</p>
                  )}
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
