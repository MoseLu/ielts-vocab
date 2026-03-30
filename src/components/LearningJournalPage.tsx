import { useCallback, useEffect, useMemo, useState } from 'react'
import refreshIcon from '../assets/icons/refresh.svg'
import {
  DailySummaryDocument,
  JournalWorkspace,
  QaHistoryDocument,
} from './journal'
import { MicroLoading, PageSkeleton } from './ui'
import { apiFetch } from '../lib'
import {
  ExportResponseSchema,
  LearnerProfileSchema,
  NotesListResponseSchema,
  SummariesListResponseSchema,
  SummaryGenerationJobSchema,
  type DailySummary,
  type LearnerProfile,
  type LearningNote,
  type NoteMemoryTopic,
  type SummaryGenerationJob,
} from '../lib/schemas'
import { safeParse } from '../lib/validation'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatDateTime(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
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

function isActiveSummaryJob(job: SummaryGenerationJob | null): job is SummaryGenerationJob {
  return Boolean(job && (job.status === 'queued' || job.status === 'running'))
}

export default function LearningJournalPage() {
  const [tab, setTab] = useState<'summaries' | 'notes'>('summaries')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState(today())

  const [summaries, setSummaries] = useState<DailySummary[]>([])
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [summaryError, setSummaryError] = useState('')
  const [generatingDate, setGeneratingDate] = useState('')
  const [selectedSummaryId, setSelectedSummaryId] = useState<number | null>(null)
  const [summaryJob, setSummaryJob] = useState<SummaryGenerationJob | null>(null)
  const [summaryProfile, setSummaryProfile] = useState<LearnerProfile | null>(null)
  const [summaryProfileLoading, setSummaryProfileLoading] = useState(false)

  const [notes, setNotes] = useState<LearningNote[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')
  const [notesTotal, setNotesTotal] = useState(0)
  const [memoryTopics, setMemoryTopics] = useState<NoteMemoryTopic[]>([])
  const [cursorStack, setCursorStack] = useState<(number | null)[]>([null])
  const [hasMore, setHasMore] = useState(false)
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null)
  const [exporting, setExporting] = useState(false)

  const notesPerPage = 20

  const applyCompletedSummary = useCallback((summary: DailySummary) => {
    setSelectedSummaryId(summary.id)
    setSummaryError('')
    setSummaries(prev => {
      const index = prev.findIndex(item => item.date === summary.date)
      if (index >= 0) {
        const updated = [...prev]
        updated[index] = summary
        return updated
      }
      return [summary, ...prev]
    })
  }, [])

  const fetchSummaries = useCallback(async () => {
    setSummaryLoading(true)
    setSummaryError('')

    try {
      const data = await apiFetch<unknown>('/api/notes/summaries')
      const parsed = safeParse(SummariesListResponseSchema, data)

      if (!parsed.success) {
        setSummaryError('总结列表数据格式错误，请重试')
        return
      }

      setSummaries(parsed.data.summaries)
    } catch (error) {
      setSummaryError(error instanceof Error ? error.message : '加载总结失败，请重试')
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

      if (!parsed.success) {
        setNotesError('问答记录数据格式错误，请重试')
        return
      }

      setNotes(parsed.data.notes)
      setMemoryTopics(parsed.data.memory_topics || [])
      setNotesTotal(parsed.data.total)
      setHasMore(parsed.data.has_more)
    } catch (error) {
      setNotesError(error instanceof Error ? error.message : '加载问答记录失败，请重试')
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

  useEffect(() => {
    if (!isActiveSummaryJob(summaryJob)) return

    let cancelled = false
    let timer: number | null = null

    const stopPolling = () => {
      if (timer != null) {
        window.clearTimeout(timer)
      }
    }

    const pollJob = async () => {
      try {
        const data = await apiFetch<unknown>(`/api/notes/summaries/generate-jobs/${summaryJob.job_id}`)
        const parsed = safeParse(SummaryGenerationJobSchema, data)

        if (!parsed.success) {
          throw new Error('生成进度数据格式错误，请重试')
        }

        if (cancelled) return

        const nextJob = parsed.data
        if (nextJob.status === 'completed') {
          if (nextJob.summary) {
            applyCompletedSummary(nextJob.summary)
          }
          setSummaryJob(null)
          setGeneratingDate('')
          return
        }

        if (nextJob.status === 'failed') {
          setSummaryError(nextJob.error || nextJob.message || '生成失败，请重试')
          setSummaryJob(null)
          setGeneratingDate('')
          return
        }

        setSummaryJob(nextJob)
        timer = window.setTimeout(pollJob, 1000)
      } catch (error) {
        if (cancelled) return
        setSummaryError(error instanceof Error ? error.message : '生成进度获取失败，请重试')
        setSummaryJob(null)
        setGeneratingDate('')
      }
    }

    void pollJob()

    return () => {
      cancelled = true
      stopPolling()
    }
  }, [applyCompletedSummary, summaryJob?.job_id, summaryJob?.status])

  const generateSummary = async (date: string) => {
    setGeneratingDate(date)
    setSummaryError('')
    setSummaryJob(null)

    try {
      const data = await apiFetch<unknown>('/api/notes/summaries/generate-jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date }),
      })
      const parsed = safeParse(SummaryGenerationJobSchema, data)

      if (!parsed.success) {
        setSummaryError('生成任务启动失败，请重试')
        setGeneratingDate('')
        return
      }

      if (parsed.data.status === 'completed') {
        if (parsed.data.summary) {
          applyCompletedSummary(parsed.data.summary)
        }
        setGeneratingDate('')
        return
      }

      if (parsed.data.status === 'failed') {
        setSummaryError(parsed.data.error || parsed.data.message || '生成失败，请重试')
        setGeneratingDate('')
        return
      }

      setSummaryJob(parsed.data)
    } catch (error) {
      setSummaryError(error instanceof Error ? error.message : '生成失败，请重试')
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

      const data = await apiFetch<unknown>(`/api/notes/export?${params}`)
      const parsed = safeParse(ExportResponseSchema, data)

      if (!parsed.success) {
        window.alert('导出结果格式错误，请重试')
        return
      }

      const { content, filename } = parsed.data
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '导出失败，请重试')
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

  useEffect(() => {
    if (tab !== 'summaries') return

    const targetDate = selectedSummary?.date
    if (!targetDate) {
      setSummaryProfile(null)
      setSummaryProfileLoading(false)
      return
    }

    let cancelled = false
    setSummaryProfileLoading(true)

    void (async () => {
      try {
        const data = await apiFetch<unknown>(`/api/ai/learner-profile?date=${encodeURIComponent(targetDate)}`)
        const parsed = safeParse(LearnerProfileSchema, data)

        if (!parsed.success) {
          if (!cancelled) setSummaryProfile(null)
          return
        }

        if (!cancelled) {
          setSummaryProfile(parsed.data)
        }
      } catch {
        if (!cancelled) {
          setSummaryProfile(null)
        }
      } finally {
        if (!cancelled) {
          setSummaryProfileLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [selectedSummary?.date, tab])

  const summaryTargetDate = today()
  const activeSummaryJob = isActiveSummaryJob(summaryJob) ? summaryJob : null
  const summaryProgress = activeSummaryJob && activeSummaryJob.date === generatingDate ? activeSummaryJob : null
  const isInitialSummaryLoading =
    tab === 'summaries' &&
    summaryLoading &&
    !summaryError &&
    summaries.length === 0
  const isInitialNotesLoading =
    tab === 'notes' &&
    notesLoading &&
    !notesError &&
    notes.length === 0

  const handleTabChange = (nextTab: 'summaries' | 'notes') => {
    if (nextTab === tab) return
    if (nextTab === 'summaries' && summaries.length === 0) {
      setSummaryLoading(true)
    }
    if (nextTab === 'notes' && notes.length === 0) {
      setNotesLoading(true)
    }
    setTab(nextTab)
  }

  const exportLabel = exporting ? '导出中...' : '导出 Markdown'
  const progressText = summaryProgress ? `${summaryProgress.progress}%` : ''
  const generateLoadingText = progressText ? `生成中... ${progressText}` : '生成中...'

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
          onChange={event => setStartDate(event.target.value)}
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
          onChange={event => setEndDate(event.target.value)}
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
          title={exportLabel}
          aria-label={exportLabel}
        >
          {exporting ? (
            <MicroLoading text="导出中..." />
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M12 3v11" />
              <path d="M8 10l4 4 4-4" />
              <path d="M5 19h14" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )

  const summaryActions = (
    <div className="journal-summary-actions">
      <div className="journal-summary-actions__buttons">
        {selectedSummary ? (
          <button
            className="journal-regen-btn"
            disabled={generatingDate === selectedSummary.date}
            onClick={() => generateSummary(selectedSummary.date)}
          >
            {generatingDate === selectedSummary.date ? <MicroLoading text={generateLoadingText} /> : '重新生成'}
          </button>
        ) : (
          <button
            className="journal-generate-btn"
            disabled={generatingDate === summaryTargetDate}
            onClick={() => generateSummary(summaryTargetDate)}
          >
            {generatingDate === summaryTargetDate ? <MicroLoading text={generateLoadingText} /> : '生成今日总结'}
          </button>
        )}
        <div className="journal-export-group">
          <button
            className="journal-export-btn"
            disabled={exporting}
            onClick={() => handleExport('summaries')}
            title={exportLabel}
            aria-label={exportLabel}
          >
            {exporting ? (
              <MicroLoading text="导出中..." />
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M12 3v11" />
                <path d="M8 10l4 4 4-4" />
                <path d="M5 19h14" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {summaryProgress ? (
        <div className="journal-summary-progress" role="status" aria-live="polite">
          <div className="journal-summary-progress__head">
            <span>{summaryProgress.message}</span>
            <strong>{summaryProgress.progress}%</strong>
          </div>
          <div className="journal-summary-progress__track" aria-hidden="true">
            <span
              className="journal-summary-progress__fill"
              style={{ width: `${summaryProgress.progress}%` }}
            />
          </div>
        </div>
      ) : null}
    </div>
  )

  if (isInitialSummaryLoading || isInitialNotesLoading) {
    return <PageSkeleton variant="journal" itemCount={4} />
  }

  return (
    <JournalWorkspace
      activeTab={tab}
      onTabChange={handleTabChange}
      actions={tab === 'notes' ? notesActions : summaryActions}
    >
      {tab === 'summaries' ? (
        <DailySummaryDocument
          summary={selectedSummary}
          learnerProfile={summaryProfile}
          learnerProfileLoading={summaryProfileLoading}
          summaryLoading={summaryLoading}
          summaryError={summaryError}
          summaryProgress={summaryProgress}
          formatDateTime={formatDateTime}
        />
      ) : (
        <QaHistoryDocument
          notes={notes}
          memoryTopics={memoryTopics}
          notesLoading={notesLoading}
          notesError={notesError}
          notesTotal={notesTotal}
          selectedNote={selectedNote}
          cursorStack={cursorStack}
          hasMore={hasMore}
          onSelectNote={setSelectedNoteId}
          onPreviousPage={() => {
            const previous = [...cursorStack]
            previous.pop()
            const beforeId = previous[previous.length - 1] ?? null
            setCursorStack(previous)
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
