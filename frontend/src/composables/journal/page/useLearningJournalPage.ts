import { startTransition, useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../../../lib'
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
} from '../../../lib/schemas'
import { safeParse } from '../../../lib/validation'
import { isActiveSummaryJob, today } from './journalPageUtils'

export type JournalTab = 'summaries' | 'notes'

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function useLearningJournalPage() {
  const [tab, setTab] = useState<JournalTab>('summaries')
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
    setSummaries(previous => {
      const index = previous.findIndex(item => item.date === summary.date)
      if (index >= 0) {
        const updated = [...previous]
        updated[index] = summary
        return updated
      }

      return [summary, ...previous]
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
      setSummaryError(getErrorMessage(error, '加载总结失败，请重试'))
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
      setNotesError(getErrorMessage(error, '加载问答记录失败，请重试'))
    } finally {
      setNotesLoading(false)
    }
  }, [endDate, startDate])

  useEffect(() => {
    if (tab === 'summaries') {
      void fetchSummaries()
      return
    }

    setCursorStack([null])
    void fetchNotes(null)
  }, [fetchNotes, fetchSummaries, tab])

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

  const activeSummaryJob = isActiveSummaryJob(summaryJob) ? summaryJob : null

  useEffect(() => {
    if (!activeSummaryJob) return

    let cancelled = false
    let timer: number | null = null

    const stopPolling = () => {
      if (timer != null) {
        window.clearTimeout(timer)
      }
    }

    const pollJob = async () => {
      try {
        const data = await apiFetch<unknown>(
          `/api/notes/summaries/generate-jobs/${activeSummaryJob.job_id}`,
        )
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
        setSummaryError(getErrorMessage(error, '生成进度获取失败，请重试'))
        setSummaryJob(null)
        setGeneratingDate('')
      }
    }

    void pollJob()

    return () => {
      cancelled = true
      stopPolling()
    }
  }, [activeSummaryJob?.job_id, activeSummaryJob?.status, applyCompletedSummary])

  const generateSummary = useCallback(async (date: string) => {
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
      setSummaryError(getErrorMessage(error, '生成失败，请重试'))
      setGeneratingDate('')
    }
  }, [applyCompletedSummary])

  const exportMarkdown = useCallback(async (type: 'summaries' | 'notes') => {
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

      downloadMarkdown(parsed.data.content, parsed.data.filename)
    } catch (error) {
      window.alert(getErrorMessage(error, '导出失败，请重试'))
    } finally {
      setExporting(false)
    }
  }, [endDate, startDate])

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
        const data = await apiFetch<unknown>(
          `/api/ai/learner-profile?date=${encodeURIComponent(targetDate)}`,
        )
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

  const handleTabChange = useCallback((nextTab: JournalTab) => {
    if (nextTab === tab) return

    if (nextTab === 'summaries' && summaries.length === 0) {
      setSummaryLoading(true)
    }

    if (nextTab === 'notes' && notes.length === 0) {
      setNotesLoading(true)
    }

    startTransition(() => {
      setTab(nextTab)
    })
  }, [notes.length, summaries.length, tab])

  const resetNoteDateFilters = useCallback(() => {
    setStartDate('')
    setEndDate(today())
  }, [])

  const goToPreviousNotesPage = useCallback(() => {
    const previous = cursorStack.length > 1 ? cursorStack.slice(0, -1) : [null]
    const beforeId = previous[previous.length - 1] ?? null
    setCursorStack(previous)
    void fetchNotes(beforeId)
  }, [cursorStack, fetchNotes])

  const goToNextNotesPage = useCallback(() => {
    const lastId = notes[notes.length - 1]?.id ?? null
    if (lastId == null) return

    setCursorStack(stack => [...stack, lastId])
    void fetchNotes(lastId)
  }, [fetchNotes, notes])

  const summaryTargetDate = today()
  const summaryProgress =
    activeSummaryJob && activeSummaryJob.date === generatingDate ? activeSummaryJob : null
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
  const exportLabel = exporting ? '导出中...' : '导出 Markdown'
  const progressText = summaryProgress ? `${summaryProgress.progress}%` : ''
  const generateLoadingText = progressText ? `生成中... ${progressText}` : '生成中...'

  return {
    tab,
    startDate,
    endDate,
    notes,
    notesLoading,
    notesError,
    notesTotal,
    memoryTopics,
    cursorStack,
    hasMore,
    exporting,
    selectedSummary,
    selectedNote,
    summaryLoading,
    summaryError,
    summaryProfile,
    summaryProfileLoading,
    generatingDate,
    summaryTargetDate,
    summaryProgress,
    isInitialSummaryLoading,
    isInitialNotesLoading,
    exportLabel,
    generateLoadingText,
    setStartDate,
    setEndDate,
    handleTabChange,
    resetNoteDateFilters,
    generateSummary,
    exportSummaries: () => void exportMarkdown('summaries'),
    exportNotes: () => void exportMarkdown('notes'),
    setSelectedNoteId,
    goToPreviousNotesPage,
    goToNextNotesPage,
  }
}
