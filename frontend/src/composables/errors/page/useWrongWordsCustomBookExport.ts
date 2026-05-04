import { useCallback, useMemo, useState } from 'react'
import type { NavigateFunction } from 'react-router-dom'
import type { WrongWordSearchMode } from '../../../features/vocabulary/wrongWordsFilters'
import type { WrongWordRecord } from '../../../features/vocabulary/wrongWordsStore'
import { apiFetch } from '../../../lib'
import { readAppSettingsFromStorage } from '../../../lib/appSettings'

const EXPORT_CHAPTER_ID = 'wrong-word-export'

interface CustomBookSummary {
  id: string
  title?: string
  word_count?: number
}

interface CreatedChapter {
  id?: string | number
  title?: string
}

interface AppendCustomBookChaptersResponse {
  bookId?: string
  created_chapters?: CreatedChapter[]
  rejected_words?: unknown[]
}

interface UseWrongWordsCustomBookExportOptions {
  words: WrongWordRecord[]
  appliedSearch: string
  searchMode: WrongWordSearchMode | null
  navigate: NavigateFunction
}

interface WrongWordsCustomBookExportPayload {
  chapters: Array<{ id: string; title: string }>
  words: Array<{
    chapterId: string
    word: string
    phonetic: string
    pos: string
    definition: string
  }>
}

export function buildWrongWordsCustomBookChapterTitle(
  appliedSearch: string,
  searchMode: WrongWordSearchMode | null,
): string {
  const search = appliedSearch.trim()
  if (!search) return '错词本精选'
  if (searchMode === 'prefix') return `以 ${search} 开头`
  if (searchMode === 'suffix') return `以 ${search} 结尾`
  if (searchMode === 'contains') return `中间包含 ${search}`
  return `包含 ${search}`
}

function stringifyWordField(value: string | null | undefined): string {
  return String(value ?? '').trim()
}

export function readWrongWordsExportChunkSize(): number | null {
  const settings = readAppSettingsFromStorage()
  if (settings.reviewLimitCustomized !== true) return null
  if (settings.reviewLimit === 'unlimited') return null

  const limit = Number.parseInt(String(settings.reviewLimit), 10)
  return Number.isFinite(limit) && limit > 0 ? limit : null
}

export function countWrongWordsExportChapters(wordCount: number, chunkSize: number | null): number {
  if (wordCount <= 0) return 0
  if (!chunkSize) return 1
  return Math.max(1, Math.ceil(wordCount / chunkSize))
}

export function buildWrongWordsCustomBookExportPayload(
  words: WrongWordRecord[],
  chapterTitle: string,
  chunkSize: number | null,
): WrongWordsCustomBookExportPayload {
  const chapterCount = countWrongWordsExportChapters(words.length, chunkSize)
  const safeChunkSize = chunkSize && chapterCount > 1 ? chunkSize : Math.max(1, words.length)
  const chapters = Array.from({ length: chapterCount }, (_, index) => ({
    id: chapterCount > 1 ? `${EXPORT_CHAPTER_ID}-${index + 1}` : EXPORT_CHAPTER_ID,
    title: chapterCount > 1 ? `${chapterTitle}（${index + 1}/${chapterCount}）` : chapterTitle,
  }))
  const payloadWords = words.flatMap((word, index) => {
    const chapter = chapters[Math.floor(index / safeChunkSize)]
    if (!chapter) return []
    return [{
      chapterId: chapter.id,
      word: stringifyWordField(word.word),
      phonetic: stringifyWordField(word.phonetic),
      pos: stringifyWordField(word.pos),
      definition: stringifyWordField(word.definition),
    }]
  })

  return { chapters, words: payloadWords }
}

export function useWrongWordsCustomBookExport({
  words,
  appliedSearch,
  searchMode,
  navigate,
}: UseWrongWordsCustomBookExportOptions) {
  const [isOpen, setIsOpen] = useState(false)
  const [phase, setPhase] = useState<'select' | 'success'>('select')
  const [books, setBooks] = useState<CustomBookSummary[]>([])
  const [selectedBookId, setSelectedBookId] = useState('')
  const [loadingBooks, setLoadingBooks] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [savedTarget, setSavedTarget] = useState<{
    bookId: string
    chapterId: string
    chapterCount: number
    rejectedCount: number
  } | null>(null)
  const chapterTitle = useMemo(
    () => buildWrongWordsCustomBookChapterTitle(appliedSearch, searchMode),
    [appliedSearch, searchMode],
  )
  const chunkSize = useMemo(readWrongWordsExportChunkSize, [isOpen, words.length])
  const chapterCount = useMemo(
    () => countWrongWordsExportChapters(words.length, chunkSize),
    [chunkSize, words.length],
  )

  const loadBooks = useCallback(async () => {
    setLoadingBooks(true)
    setError('')
    try {
      const response = await apiFetch<{ books?: CustomBookSummary[] }>('/api/books/custom-books')
      const nextBooks = Array.isArray(response.books) ? response.books : []
      setBooks(nextBooks)
      setSelectedBookId(current => current || nextBooks[0]?.id || '')
    } catch (nextError) {
      setBooks([])
      setSelectedBookId('')
      setError(nextError instanceof Error ? nextError.message : '自定义词书加载失败')
    } finally {
      setLoadingBooks(false)
    }
  }, [])

  const open = useCallback(() => {
    setIsOpen(true)
    setPhase('select')
    setSavedTarget(null)
    setError('')
    void loadBooks()
  }, [loadBooks])

  const close = useCallback(() => {
    setIsOpen(false)
    setPhase('select')
    setSaving(false)
    setError('')
  }, [])

  const save = useCallback(async () => {
    if (!selectedBookId || words.length === 0) return

    setSaving(true)
    setError('')
    try {
      const exportPayload = buildWrongWordsCustomBookExportPayload(words, chapterTitle, chunkSize)
      const response = await apiFetch<AppendCustomBookChaptersResponse>(
        `/api/books/custom-books/${encodeURIComponent(selectedBookId)}/chapters`,
        {
          method: 'POST',
          body: JSON.stringify({
            chapters: exportPayload.chapters,
            words: exportPayload.words,
          }),
        },
      )
      const createdChapter = response.created_chapters?.[0]
      const chapterId = String(createdChapter?.id ?? '')
      if (!chapterId) throw new Error('保存结果缺少章节 ID')
      setSavedTarget({
        bookId: response.bookId || selectedBookId,
        chapterId,
        chapterCount: exportPayload.chapters.length,
        rejectedCount: Array.isArray(response.rejected_words) ? response.rejected_words.length : 0,
      })
      setPhase('success')
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '保存到自定义词书失败')
    } finally {
      setSaving(false)
    }
  }, [chapterTitle, chunkSize, selectedBookId, words])

  const openQuickMemory = useCallback(() => {
    if (!savedTarget) return
    const params = new URLSearchParams({
      book: savedTarget.bookId,
      chapter: savedTarget.chapterId,
      mode: 'quickmemory',
      restart: '1',
    })
    close()
    navigate(`/practice?${params.toString()}`)
  }, [close, navigate, savedTarget])

  return {
    isOpen,
    phase,
    books,
    selectedBookId,
    loadingBooks,
    saving,
    error,
    chapterTitle,
    chapterCount,
    chunkSize,
    wordCount: words.length,
    savedTarget,
    setSelectedBookId,
    open,
    close,
    save,
    openQuickMemory,
  }
}
