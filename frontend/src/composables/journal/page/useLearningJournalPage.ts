import { startTransition, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../../../lib'
import {
  JournalEntryListResponseSchema,
  JournalTodayResponseSchema,
  JournalUpsertResponseSchema,
  JournalPolishResponseSchema,
  type JournalEntry,
} from '../../../lib/schemas'
import { safeParse } from '../../../lib/validation'
import { today } from './journalPageUtils'

export type JournalTab = 'today' | 'history'

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

export function useLearningJournalPage() {
  const [tab, setTab] = useState<JournalTab>('today')

  // ── Today state ──
  const [todayEntry, setTodayEntry] = useState<JournalEntry | null>(null)
  const [todayLoading, setTodayLoading] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [polishing, setPolishing] = useState(false)
  const [polishedPreview, setPolishedPreview] = useState<string | null>(null)
  const [todayDraftContent, setTodayDraftContent] = useState('')

  // ── History state ──
  const [historyEntries, setHistoryEntries] = useState<JournalEntry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [historyHasMore, setHistoryHasMore] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState(today())

  // ── Export state ──
  const [exporting, setExporting] = useState(false)

  const isInitialTodayLoading = tab === 'today' && todayLoading && !todayEntry

  // ── Fetch today's entry ──
  const fetchToday = useCallback(async () => {
    setTodayLoading(true)
    try {
      const data = await apiFetch<unknown>('/api/notes/journal/today')
      const parsed = safeParse(JournalTodayResponseSchema, data)
      if (parsed.success) {
        setTodayEntry(parsed.data.entry)
        setTodayDraftContent(parsed.data.entry?.content ?? '')
      }
    } catch {
      // Silently handle — entry is null
    } finally {
      setTodayLoading(false)
    }
  }, [])

  // ── Save today's entry ──
  const saveJournalEntry = useCallback(async (content: string) => {
    if (!content.trim()) return
    try {
      const data = await apiFetch<unknown>('/api/notes/journal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      const parsed = safeParse(JournalUpsertResponseSchema, data)
      if (parsed.success) {
        setTodayEntry(parsed.data.entry)
        setTodayDraftContent(parsed.data.entry.content)
      }
    } catch {
      // Silently handle save error
    }
  }, [])

  // ── Polish content ──
  const polishContent = useCallback(async (contentOverride?: string) => {
    const overrideContent = typeof contentOverride === 'string' ? contentOverride : undefined
    const content = ((overrideContent ?? todayDraftContent) || todayEntry?.content || '').trim()
    if (!content) {
      window.alert('请先写一点内容再润色')
      return
    }
    setPolishing(true)
    setPolishedPreview(null)

    try {
      const data = await apiFetch<unknown>('/api/notes/journal/polish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      const parsed = safeParse(JournalPolishResponseSchema, data)
      if (parsed.success && parsed.data.polished) {
        setPolishedPreview(parsed.data.polished)
      } else {
        window.alert('AI 润色失败，请重试')
      }
    } catch (error) {
      window.alert(getErrorMessage(error, 'AI 润色失败，请重试'))
    } finally {
      setPolishing(false)
    }
  }, [todayDraftContent, todayEntry?.content])

  const acceptPolish = useCallback(() => {
    if (!polishedPreview) return
    setTodayEntry((prev: JournalEntry | null) => prev ? { ...prev, content: polishedPreview } : null)
    saveJournalEntry(polishedPreview)
    setPolishedPreview(null)
  }, [polishedPreview, saveJournalEntry])

  const rejectPolish = useCallback(() => {
    setPolishedPreview(null)
  }, [])

  // ── History ──
  const fetchHistory = useCallback(async (beforeId: number | null = null) => {
    setHistoryLoading(true)
    setHistoryError('')

    try {
      const params = new URLSearchParams({ per_page: '10' })
      if (beforeId != null) params.set('before_id', String(beforeId))
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)

      const data = await apiFetch<unknown>(`/api/notes/journal?${params}`)
      const parsed = safeParse(JournalEntryListResponseSchema, data)

      if (!parsed.success) {
        setHistoryError('数据格式错误，请重试')
        return
      }

      if (beforeId != null) {
        setHistoryEntries(prev => [...prev, ...parsed.data.entries])
      } else {
        setHistoryEntries(parsed.data.entries)
      }
      setHistoryHasMore(parsed.data.has_more)
    } catch (error) {
      setHistoryError(getErrorMessage(error, '加载失败，请重试'))
    } finally {
      setHistoryLoading(false)
    }
  }, [startDate, endDate])

  const loadMoreHistory = useCallback(() => {
    const lastEntry = historyEntries[historyEntries.length - 1]
    if (lastEntry) {
      void fetchHistory(lastEntry.id)
    }
  }, [fetchHistory, historyEntries])

  const selectEntry = useCallback((entry: JournalEntry) => {
    setSelectedEntry(entry)
  }, [])

  const backToList = useCallback(() => {
    setSelectedEntry(null)
  }, [])

  const resetDateFilters = useCallback(() => {
    setStartDate('')
    setEndDate(today())
  }, [])

  // ── Tab switching ──
  const handleTabChange = useCallback((nextTab: JournalTab) => {
    if (nextTab === tab) return
    startTransition(() => {
      setTab(nextTab)
    })
  }, [tab])

  // ── Initial load ──
  useEffect(() => {
    void fetchToday()
  }, [fetchToday])

  useEffect(() => {
    if (tab === 'history' && historyEntries.length === 0) {
      void fetchHistory(null)
    }
  }, [fetchHistory, historyEntries.length, tab])

  // Reload history when filters change
  useEffect(() => {
    if (tab === 'history') {
      void fetchHistory(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate])

  // ── Export ──
  const exportNotes = useCallback(async () => {
    setExporting(true)
    try {
      const params = new URLSearchParams({ format: 'md', type: 'notes' })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)

      const data = await apiFetch<unknown>(`/api/notes/export?${params}`)
      const blob = new Blob([JSON.stringify(data)], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `notes-export-${today()}.md`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      window.alert('导出失败，请重试')
    } finally {
      setExporting(false)
    }
  }, [startDate, endDate])

  const exportLabel = exporting ? '导出中...' : '导出 Markdown'

  return {
    tab,
    startDate,
    endDate,
    todayEntry,
    todayLoading,
    editMode,
    polishing,
    polishedPreview,
    historyEntries,
    historyLoading,
    historyError,
    historyHasMore,
    selectedEntry,
    exporting,
    exportLabel,
    isInitialTodayLoading,
    setStartDate,
    setEndDate,
    setEditMode,
    setTodayEntry,
    handleTabChange,
    resetDateFilters,
    fetchToday,
    saveJournalEntry,
    setTodayDraftContent,
    polishContent,
    acceptPolish,
    rejectPolish,
    fetchHistory,
    loadMoreHistory,
    selectEntry,
    backToList,
    exportNotes,
  }
}
