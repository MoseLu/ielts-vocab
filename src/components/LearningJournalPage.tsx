import { useCallback, useEffect, useMemo, useState } from 'react'
import refreshIcon from '../assets/icons/refresh.svg'
import {
  DailySummaryDocument,
  JournalWorkspace,
  QaHistoryDocument,
} from './journal'
import { apiFetch } from '../lib'
import {
  ExportResponseSchema,
  GenerateSummaryResponseSchema,
  NotesListResponseSchema,
  SummariesListResponseSchema,
  type DailySummary,
  type LearningNote,
} from '../lib/schemas'
import { renderJournalMarkdown } from '../lib/journalMarkdown'
import { safeParse } from '../lib/validation'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatDateTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function toPlainTextSnippet(text: string, maxLen = 120): string {
  const plain = text
    .replace(/\r\n/g, '\n')
    .replace(/[`#>*_|-]+/g, ' ')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()

  if (plain.length <= maxLen) return plain
  return `${plain.slice(0, maxLen).trim()}...`
}

export default function LearningJournalPage() {
  const [tab, setTab] = useState<'summaries' | 'notes'>('summaries')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState(today())

  const [summaries, setSummaries] = useState<DailySummary[]>([])
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState('')
  const [generatingDate, setGeneratingDate] = useState('')
  const [selectedSummaryId, setSelectedSummaryId] = useState<number | null>(null)

  const [notes, setNotes] = useState<LearningNote[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')
  const [notesTotal, setNotesTotal] = useState(0)
  const [cursorStack, setCursorStack] = useState<(number | null)[]>([null])
  const [hasMore, setHasMore] = useState(false)
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null)
  const [exporting, setExporting] = useState(false)

  const notesPerPage = 20

  const fetchSummaries = useCallback(async () => {
    setSummaryLoading(true)
    setSummaryError('')
    try {
      const data = await apiFetch<unknown>('/api/notes/summaries')
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
  }, [])

  const fetchNotes = useCallback(async (beforeId: number | null = null) => {
    setNotesLoading(true)
    setNotesError('')
    try {
      const params = new URLSearchParams({ per_page: String(notesPerPage) })
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
  }, [endDate, startDate])

  useEffect(() => {
    if (tab === 'summaries') {
      fetchSummaries()
      return
    }

    setCursorStack([null])
    fetchNotes(null)
  }, [tab, fetchNotes, fetchSummaries])

  useEffect(() => {
    if (!summaries.length) {
      setSelectedSummaryId(null)
      return
    }
    if (!summaries.some(summary => summary.id === selectedSummaryId)) {
      setSelectedSummaryId(summaries[0].id)
    }
  }, [selectedSummaryId, summaries])

  useEffect(() => {
    if (!notes.length) {
      setSelectedNoteId(null)
      return
    }
    if (!notes.some(note => note.id === selectedNoteId)) {
      setSelectedNoteId(notes[0].id)
    }
  }, [notes, selectedNoteId])

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
        setSelectedSummaryId(parsed.data.summary.id)
        setSummaries(prev => {
          const idx = prev.findIndex(summary => summary.date === date)
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

  const handleExport = async (type: 'all' | 'summaries' | 'notes') => {
    setExporting(true)
    try {
      const params = new URLSearchParams({ format: 'md', type })
      if (type === 'notes') {
        if (startDate) params.set('start_date', startDate)
        if (endDate) params.set('end_date', endDate)
      }
      const res = await apiFetch(`/api/notes/export?${params}`)
      const data = await res.json()
      const parsed = safeParse(ExportResponseSchema, data)
      if (!parsed.success) {
        alert('导出失败')
        return
      }
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

  const selectedSummary = useMemo(
    () => summaries.find(summary => summary.id === selectedSummaryId) ?? null,
    [selectedSummaryId, summaries],
  )
  const selectedNote = useMemo(
    () => notes.find(note => note.id === selectedNoteId) ?? null,
    [notes, selectedNoteId],
  )
  const summaryTargetDate = today()

  const notesActions = (
    <div className="journal-filter-bar">
      <div className="journal-filter-group">
        <label className="journal-filter-label" htmlFor="journal-start-date">开始日期</label>
        <input
          id="journal-start-date"
          type="date"
          className="journal-date-input"
          value={startDate}
          max={endDate || today()}
          onChange={e => setStartDate(e.target.value)}
        />
      </div>
      <div className="journal-filter-group">
        <label className="journal-filter-label" htmlFor="journal-end-date">结束日期</label>
        <input
          id="journal-end-date"
          type="date"
          className="journal-date-input"
          value={endDate}
          max={today()}
          onChange={e => setEndDate(e.target.value)}
        />
      </div>
      <button
        className="journal-filter-reset"
        title="重置日期筛选"
        aria-label="重置日期筛选"
        onClick={() => {
          setStartDate('')
          setEndDate(today())
        }}
      >
        <img src={refreshIcon} alt="" aria-hidden="true" />
      </button>
      <div className="journal-export-group">
        <button
          className="journal-export-btn"
          disabled={exporting}
          onClick={() => handleExport('notes')}
          title="导出 Markdown"
          aria-label="导出 Markdown"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M12 3v11" />
            <path d="M8 10l4 4 4-4" />
            <path d="M5 19h14" />
          </svg>
        </button>
      </div>
    </div>
  )

  const summaryActions = (
    <div className="journal-summary-actions">
      {selectedSummary ? (
        <button
          className="journal-regen-btn"
          disabled={generatingDate === selectedSummary.date}
          onClick={() => generateSummary(selectedSummary.date)}
        >
          {generatingDate === selectedSummary.date ? '生成中...' : '重新生成'}
        </button>
      ) : (
        <button
          className="journal-generate-btn"
          disabled={generatingDate === summaryTargetDate}
          onClick={() => generateSummary(summaryTargetDate)}
        >
          {generatingDate === summaryTargetDate ? '生成中...' : '生成今日总结'}
        </button>
      )}
      <div className="journal-export-group">
      <button
        className="journal-export-btn"
        disabled={exporting}
        onClick={() => handleExport('summaries')}
        title="导出 Markdown"
        aria-label="导出 Markdown"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <path d="M12 3v11" />
          <path d="M8 10l4 4 4-4" />
          <path d="M5 19h14" />
        </svg>
      </button>
      </div>
    </div>
  )

  return (
    <JournalWorkspace
      activeTab={tab}
      onTabChange={setTab}
      actions={tab === 'notes' ? notesActions : summaryActions}
    >
      {tab === 'summaries' ? (
        <DailySummaryDocument
          summary={selectedSummary}
          summaryLoading={summaryLoading}
          summaryError={summaryError}
          formatDateTime={formatDateTime}
        />
      ) : (
        <QaHistoryDocument
          notes={notes}
          notesLoading={notesLoading}
          notesError={notesError}
          notesTotal={notesTotal}
          selectedNote={selectedNote}
          cursorStack={cursorStack}
          hasMore={hasMore}
          onSelectNote={setSelectedNoteId}
          onPreviousPage={() => {
            const prev = [...cursorStack]
            prev.pop()
            const beforeId = prev[prev.length - 1] ?? null
            setCursorStack(prev)
            fetchNotes(beforeId)
          }}
          onNextPage={() => {
            const lastId = notes[notes.length - 1]?.id ?? null
            setCursorStack(stack => [...stack, lastId])
            fetchNotes(lastId)
          }}
          formatDateTime={formatDateTime}
          toPlainTextSnippet={toPlainTextSnippet}
        />
      )}
    </JournalWorkspace>
  )
}
