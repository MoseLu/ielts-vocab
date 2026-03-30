import { useState, useEffect, useCallback } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { apiFetch } from '../lib'
import { safeParse } from '../lib/validation'
import {
  NotesListResponseSchema,
  SummariesListResponseSchema,
  GenerateSummaryResponseSchema,
  ExportResponseSchema,
  type LearningNote,
  type DailySummary,
} from '../lib/schemas'

// ── helpers ───────────────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatDate(iso: string): string {
  return iso ? iso.slice(0, 10) : ''
}

function formatDateTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ── Safe Markdown renderer (marked + DOMPurify) ───────────────────────────────

function renderMarkdown(md: string): string {
  const raw = marked.parse(md, { async: false }) as string
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: ['h1','h2','h3','h4','p','strong','em','ul','ol','li','hr','br','code','pre','blockquote'],
    ALLOWED_ATTR: [],
  })
}

// ── ExpandableText ────────────────────────────────────────────────────────────

function ExpandableText({ text, maxLen = 200 }: { text: string; maxLen?: number }) {
  const [expanded, setExpanded] = useState(false)
  if (text.length <= maxLen) return <span>{text}</span>
  return (
    <span>
      {expanded ? text : text.slice(0, maxLen) + '…'}
      <button
        className="journal-expand-btn"
        onClick={() => setExpanded(e => !e)}
      >
        {expanded ? ' 收起' : ' 展开'}
      </button>
    </span>
  )
}

// ── SummaryModal ──────────────────────────────────────────────────────────────

interface SummaryModalProps {
  summary: DailySummary
  onClose: () => void
}

function SummaryModal({ summary, onClose }: SummaryModalProps) {
  return (
    <div className="journal-modal-overlay" onClick={onClose}>
      <div className="journal-modal" onClick={e => e.stopPropagation()}>
        <div className="journal-modal-header">
          <h2>{summary.date} 学习总结</h2>
          <button className="journal-modal-close" onClick={onClose}>✕</button>
        </div>
        <div
          className="journal-modal-body markdown-content"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(summary.content) }}
        />
        <div className="journal-modal-footer">
          <span className="journal-meta">生成于 {formatDateTime(summary.generated_at)}</span>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function LearningJournalPage() {
  const [tab, setTab] = useState<'summaries' | 'notes'>('summaries')

  // date filter
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState(today())

  // summaries state
  const [summaries, setSummaries] = useState<DailySummary[]>([])
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState('')
  const [generatingDate, setGeneratingDate] = useState('')
  const [selectedSummary, setSelectedSummary] = useState<DailySummary | null>(null)

  // notes state — cursor-based pagination
  const [notes, setNotes] = useState<LearningNote[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')
  const [notesTotal, setNotesTotal] = useState(0)
  const [cursorStack, setCursorStack] = useState<(number | null)[]>([null]) // stack of before_id values
  const [hasMore, setHasMore] = useState(false)
  const NOTES_PER_PAGE = 20

  // export state
  const [exporting, setExporting] = useState(false)

  // ── fetch summaries ──────────────────────────────────────────────────────────
  const fetchSummaries = useCallback(async () => {
    setSummaryLoading(true)
    setSummaryError('')
    try {
      const params = new URLSearchParams()
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      const data = await apiFetch<unknown>(`/api/notes/summaries?${params}`)
      const parsed = safeParse(SummariesListResponseSchema, data)
      if (parsed.success) {
        setSummaries(parsed.data.summaries)
      } else {
        setSummaryError('数据格式错误')
      }
    } catch {
      setSummaryError('加载失败，请重试')
    } finally {
      setSummaryLoading(false)
    }
  }, [startDate, endDate])

  // ── fetch notes (cursor-based) ────────────────────────────────────────────────
  const fetchNotes = useCallback(async (beforeId: number | null = null) => {
    setNotesLoading(true)
    setNotesError('')
    try {
      const params = new URLSearchParams({ per_page: String(NOTES_PER_PAGE) })
      if (beforeId != null) params.set('before_id', String(beforeId))
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      const data = await apiFetch<unknown>(`/api/notes?${params}`)
      const parsed = safeParse(NotesListResponseSchema, data)
      if (parsed.success) {
        setNotes(parsed.data.notes)
        setNotesTotal(parsed.data.total)
        setHasMore(parsed.data.has_more)
      } else {
        setNotesError('数据格式错误')
      }
    } catch {
      setNotesError('加载失败，请重试')
    } finally {
      setNotesLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => {
    setCursorStack([null])
    if (tab === 'summaries') fetchSummaries()
    else fetchNotes(null)
  }, [tab, fetchSummaries, fetchNotes])

  // ── generate summary ─────────────────────────────────────────────────────────
  const generateSummary = async (date: string) => {
    setGeneratingDate(date)
    try {
      const res = await apiFetch('/api/notes/summaries/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date }),
      })
      const data = await res.json()
      if (!res.ok) {
        alert(data.error || '生成失败')
        return
      }
      const parsed = safeParse(GenerateSummaryResponseSchema, data)
      if (parsed.success) {
        setSummaries(prev => {
          const idx = prev.findIndex(s => s.date === date)
          if (idx >= 0) {
            const updated = [...prev]
            updated[idx] = parsed.data.summary
            return updated
          }
          return [parsed.data.summary, ...prev]
        })
      }
    } catch {
      alert('生成失败，请重试')
    } finally {
      setGeneratingDate('')
    }
  }

  // ── export ───────────────────────────────────────────────────────────────────
  const handleExport = async (fmt: 'md' | 'txt', type: 'all' | 'summaries' | 'notes') => {
    setExporting(true)
    try {
      const params = new URLSearchParams({ format: fmt, type })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      const res = await apiFetch(`/api/notes/export?${params}`)
      const data = await res.json()
      const parsed = safeParse(ExportResponseSchema, data)
      if (!parsed.success) { alert('导出失败'); return }
      const { content, filename } = parsed.data
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('导出失败，请重试')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="journal-page">
      <div className="page-content">
      <div className="journal-header">
        <h1 className="journal-title">学习日志</h1>
        <p className="journal-subtitle">查看每日学习总结和 AI 问答记录</p>
      </div>

      {/* Date Filter */}
      <div className="journal-filter-bar">
        <div className="journal-filter-group">
          <label className="journal-filter-label">开始日期</label>
          <input
            type="date"
            className="journal-date-input"
            value={startDate}
            max={endDate || today()}
            onChange={e => setStartDate(e.target.value)}
          />
        </div>
        <div className="journal-filter-group">
          <label className="journal-filter-label">结束日期</label>
          <input
            type="date"
            className="journal-date-input"
            value={endDate}
            max={today()}
            onChange={e => setEndDate(e.target.value)}
          />
        </div>
        <button
          className="journal-filter-reset"
          onClick={() => { setStartDate(''); setEndDate(today()) }}
        >
          重置
        </button>

        <div className="journal-export-group">
          <span className="journal-filter-label">导出</span>
          <button
            className="journal-export-btn"
            disabled={exporting}
            onClick={() => handleExport('md', 'all')}
            title="导出 Markdown"
          >
            .md
          </button>
          <button
            className="journal-export-btn"
            disabled={exporting}
            onClick={() => handleExport('txt', 'all')}
            title="导出纯文本"
          >
            .txt
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="journal-tabs">
        <button
          className={`journal-tab ${tab === 'summaries' ? 'active' : ''}`}
          onClick={() => setTab('summaries')}
        >
          每日总结
        </button>
        <button
          className={`journal-tab ${tab === 'notes' ? 'active' : ''}`}
          onClick={() => setTab('notes')}
        >
          AI 问答记录
        </button>
      </div>

      {/* ── Summaries Tab ── */}
      {tab === 'summaries' && (
        <div className="journal-section">
          <div className="journal-section-actions">
            <button
              className="journal-generate-btn"
              disabled={!!generatingDate}
              onClick={() => generateSummary(today())}
            >
              {generatingDate === today() ? '生成中…' : '生成今日总结'}
            </button>
          </div>

          {summaryLoading && <div className="journal-loading">加载中…</div>}
          {summaryError && <div className="journal-error">{summaryError}</div>}

          {!summaryLoading && summaries.length === 0 && !summaryError && (
            <div className="journal-empty">
              <p>暂无总结记录。</p>
              <p>点击「生成今日总结」让 AI 根据当日学习数据生成摘要。</p>
            </div>
          )}

          <div className="journal-summary-list">
            {summaries.map(s => (
              <div key={s.id} className="journal-summary-card">
                <div className="journal-summary-card-header">
                  <span className="journal-summary-date">{s.date}</span>
                  <div className="journal-summary-card-actions">
                    <button
                      className="journal-view-btn"
                      onClick={() => setSelectedSummary(s)}
                    >
                      查看
                    </button>
                    <button
                      className="journal-regen-btn"
                      disabled={generatingDate === s.date}
                      onClick={() => generateSummary(s.date)}
                    >
                      {generatingDate === s.date ? '生成中…' : '重新生成'}
                    </button>
                  </div>
                </div>
                <div className="journal-summary-preview">
                  <ExpandableText text={s.content} maxLen={180} />
                </div>
                <div className="journal-summary-meta">
                  更新于 {formatDateTime(s.generated_at)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Notes Tab ── */}
      {tab === 'notes' && (
        <div className="journal-section">
          {notesLoading && <div className="journal-loading">加载中…</div>}
          {notesError && <div className="journal-error">{notesError}</div>}

          {!notesLoading && notes.length === 0 && !notesError && (
            <div className="journal-empty">
              <p>暂无问答记录。</p>
              <p>在学习单词时向 AI 助手提问，对话会自动保存在这里。</p>
            </div>
          )}

          {notes.length > 0 && (
            <>
              <div className="journal-notes-count">
                共 {notesTotal} 条记录
              </div>
              <div className="journal-notes-table">
                <div className="journal-notes-header">
                  <div className="journal-notes-col col-time">时间</div>
                  <div className="journal-notes-col col-word">单词</div>
                  <div className="journal-notes-col col-question">问题</div>
                  <div className="journal-notes-col col-answer">AI 回答</div>
                </div>
                {notes.map(n => (
                  <NoteRow key={n.id} note={n} />
                ))}
              </div>

              {/* Cursor pagination */}
              {(cursorStack.length > 1 || hasMore) && (
                <div className="journal-pagination">
                  <button
                    className="journal-page-btn"
                    disabled={cursorStack.length <= 1}
                    onClick={() => {
                      const prev = [...cursorStack]
                      prev.pop()           // remove current
                      const beforeId = prev[prev.length - 1] ?? null
                      setCursorStack(prev)
                      fetchNotes(beforeId)
                    }}
                  >
                    上一页
                  </button>
                  <span className="journal-page-info">第 {cursorStack.length} 页</span>
                  <button
                    className="journal-page-btn"
                    disabled={!hasMore}
                    onClick={() => {
                      const lastId = notes[notes.length - 1]?.id ?? null
                      setCursorStack(s => [...s, lastId])
                      fetchNotes(lastId)
                    }}
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Summary detail modal */}
      {selectedSummary && (
        <SummaryModal
          summary={selectedSummary}
          onClose={() => setSelectedSummary(null)}
        />
      )}
      </div>
    </div>
  )
}

// ── NoteRow (expandable answer) ───────────────────────────────────────────────

function NoteRow({ note }: { note: LearningNote }) {
  const [expanded, setExpanded] = useState(false)
  const ANSWER_PREVIEW = 120

  return (
    <div className="journal-notes-row">
      <div className="journal-notes-col col-time">
        {formatDate(note.created_at)}
        <span className="journal-note-time-sub">
          {note.created_at ? new Date(note.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
        </span>
      </div>
      <div className="journal-notes-col col-word">
        {note.word_context ? (
          <span className="journal-word-badge">{note.word_context}</span>
        ) : (
          <span className="journal-word-none">—</span>
        )}
      </div>
      <div className="journal-notes-col col-question">
        <ExpandableText text={note.question} maxLen={100} />
      </div>
      <div className="journal-notes-col col-answer">
        {expanded ? (
          <>
            <div
              className="journal-answer-full markdown-content"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(note.answer) }}
            />
            <button className="journal-expand-btn" onClick={() => setExpanded(false)}>
              收起
            </button>
          </>
        ) : (
          <>
            {note.answer.length > ANSWER_PREVIEW
              ? note.answer.slice(0, ANSWER_PREVIEW) + '…'
              : note.answer}
            {note.answer.length > ANSWER_PREVIEW && (
              <button className="journal-expand-btn" onClick={() => setExpanded(true)}>
                展开
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
