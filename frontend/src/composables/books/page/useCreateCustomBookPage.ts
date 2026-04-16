import { useCallback, useEffect, useState, type ChangeEvent, type DragEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../../../contexts'
import { apiFetch } from '../../../lib'
import {
  DEFAULT_CHAPTER_WORD_TARGET,
  buildCustomBookPayload,
  countDraftWords,
  createChapterDraft,
  updateChapterContent,
  type CustomBookChapterDraft,
} from '../../../components/books/create/customBookDraft'
import { parseCustomBookCsv } from '../../../components/books/create/customBookCsv'

type ImportMode = 'manual' | 'csv'

interface CustomBookChapterSummary {
  id: string
  title: string
}

interface CreateCustomBookResponse {
  bookId?: string
  created_count?: number
  book?: {
    id?: string
    incomplete_word_count?: number
  }
}

interface ExistingCustomBookResponse {
  id: string
  title?: string
  word_count?: number
  education_stage?: string | null
  exam_type?: string | null
  ielts_skill?: string | null
  share_enabled?: boolean
  chapter_word_target?: number
  chapters?: CustomBookChapterSummary[]
}

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items]
  const [removed] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, removed)
  return next
}

export function useCreateCustomBookPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const appendBookId = searchParams.get('bookId')?.trim() ?? ''
  const isAppendMode = appendBookId.length > 0
  const { showToast } = useToast()
  const [title, setTitle] = useState(isAppendMode ? '' : '我的自定义词书')
  const [educationStage, setEducationStage] = useState('abroad')
  const [examType, setExamType] = useState('ielts')
  const [ieltsSkill, setIeltsSkill] = useState('listening')
  const [chapterWordTarget, setChapterWordTarget] = useState(DEFAULT_CHAPTER_WORD_TARGET)
  const [shareEnabled, setShareEnabled] = useState(false)
  const [importMode, setImportMode] = useState<ImportMode>('manual')
  const [chapters, setChapters] = useState<CustomBookChapterDraft[]>(() => (
    isAppendMode ? [] : [createChapterDraft(1, { content: '' })]
  ))
  const [chapterIndexBase, setChapterIndexBase] = useState(0)
  const [existingChapterCount, setExistingChapterCount] = useState(0)
  const [existingWordCount, setExistingWordCount] = useState(0)
  const [reorderMode, setReorderMode] = useState(false)
  const [draggedChapterId, setDraggedChapterId] = useState<string | null>(null)
  const [csvSummary, setCsvSummary] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isLoadingExistingBook, setIsLoadingExistingBook] = useState(isAppendMode)
  const [hasLoadedExistingBook, setHasLoadedExistingBook] = useState(!isAppendMode)

  const totalWords = countDraftWords(chapters)

  useEffect(() => {
    if (!isAppendMode) return

    let isCancelled = false
    setIsLoadingExistingBook(true)
    setHasLoadedExistingBook(false)
    setFormError(null)

    void apiFetch<ExistingCustomBookResponse>(`/api/books/custom-books/${appendBookId}`)
      .then(book => {
        if (isCancelled) return
        const loadedChapterCount = book.chapters?.length ?? 0
        setTitle(book.title?.trim() || '我的自定义词书')
        setEducationStage(book.education_stage || 'abroad')
        setExamType(book.exam_type || 'ielts')
        setIeltsSkill(book.ielts_skill || 'listening')
        setChapterWordTarget(Math.max(1, Number(book.chapter_word_target) || DEFAULT_CHAPTER_WORD_TARGET))
        setShareEnabled(Boolean(book.share_enabled))
        setChapterIndexBase(loadedChapterCount)
        setExistingChapterCount(loadedChapterCount)
        setExistingWordCount(Math.max(0, Number(book.word_count) || 0))
        setChapters([createChapterDraft(loadedChapterCount + 1, { content: '' })])
        setHasLoadedExistingBook(true)
      })
      .catch(error => {
        if (isCancelled) return
        setFormError(error instanceof Error ? error.message : '词书加载失败')
      })
      .finally(() => {
        if (!isCancelled) setIsLoadingExistingBook(false)
      })

    return () => {
      isCancelled = true
    }
  }, [appendBookId, isAppendMode])

  const addChapter = useCallback(() => {
    setChapters(current => [...current, createChapterDraft(chapterIndexBase + current.length + 1)])
  }, [chapterIndexBase])

  const removeChapter = useCallback((chapterId: string) => {
    setChapters(current => (
      current.length <= 1 ? current : current.filter(chapter => chapter.id !== chapterId)
    ))
  }, [])

  const updateChapterTitle = useCallback((chapterId: string, nextTitle: string) => {
    setChapters(current => current.map(chapter => (
      chapter.id === chapterId ? { ...chapter, title: nextTitle } : chapter
    )))
  }, [])

  const updateChapterBody = useCallback((chapterId: string, content: string) => {
    setChapters(current => current.map(chapter => (
      chapter.id === chapterId ? updateChapterContent(chapter, content) : chapter
    )))
  }, [])

  const moveChapter = useCallback((chapterId: string, direction: -1 | 1) => {
    setChapters(current => {
      const index = current.findIndex(chapter => chapter.id === chapterId)
      const nextIndex = index + direction
      if (index < 0 || nextIndex < 0 || nextIndex >= current.length) return current
      return moveItem(current, index, nextIndex)
    })
  }, [])

  const handleDragStart = useCallback((chapterId: string, event: DragEvent<HTMLElement>) => {
    setDraggedChapterId(chapterId)
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', chapterId)
  }, [])

  const handleDragOver = useCallback((event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const handleDrop = useCallback((targetChapterId: string, event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    const sourceChapterId = draggedChapterId ?? event.dataTransfer.getData('text/plain')
    setDraggedChapterId(null)
    if (!sourceChapterId || sourceChapterId === targetChapterId) return

    setChapters(current => {
      const sourceIndex = current.findIndex(chapter => chapter.id === sourceChapterId)
      const targetIndex = current.findIndex(chapter => chapter.id === targetChapterId)
      if (sourceIndex < 0 || targetIndex < 0) return current
      return moveItem(current, sourceIndex, targetIndex)
    })
  }, [draggedChapterId])

  const handleCsvFile = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const parsedChapters = parseCustomBookCsv(text, chapterWordTarget, chapterIndexBase)
      if (parsedChapters.length === 0) {
        setFormError('没有从 CSV 中识别到单词')
        return
      }
      setChapters(parsedChapters)
      setImportMode('csv')
      setCsvSummary(`已导入 ${parsedChapters.length} 个章节，共 ${countDraftWords(parsedChapters)} 个词条`)
      setFormError(null)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'CSV 解析失败')
    } finally {
      event.target.value = ''
    }
  }, [chapterIndexBase, chapterWordTarget])

  const saveBook = useCallback(async () => {
    if (isAppendMode && !hasLoadedExistingBook) {
      setFormError('当前词书尚未加载完成，暂时不能追加章节')
      return
    }
    if (!title.trim()) {
      setFormError('请输入词书名称')
      return
    }
    if (totalWords <= 0) {
      setFormError('至少需要输入 1 个单词')
      return
    }

    setIsSaving(true)
    setFormError(null)
    try {
      const payload = buildCustomBookPayload({
        title,
        educationStage,
        examType,
        ieltsSkill,
        shareEnabled,
        chapterWordTarget,
        chapters,
      })
      const endpoint = isAppendMode
        ? `/api/books/custom-books/${appendBookId}/chapters`
        : '/api/books/custom-books'
      const created = await apiFetch<CreateCustomBookResponse>(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const bookId = created.bookId ?? created.book?.id
      if (!bookId) throw new Error('保存结果缺少词书 ID')

      if (!isAppendMode) {
        await apiFetch('/api/books/my', {
          method: 'POST',
          body: JSON.stringify({ book_id: bookId }),
        })
      }

      const incompleteCount = created.book?.incomplete_word_count ?? 0
      const createdCount = Math.max(1, created.created_count ?? chapters.filter(chapter => chapter.entries.length > 0).length)
      const successMessage = isAppendMode
        ? (
            incompleteCount > 0
              ? `已新增 ${createdCount} 个章节，词书中仍有 ${incompleteCount} 个词条待补全`
              : `已新增 ${createdCount} 个章节`
          )
        : (
            incompleteCount > 0
              ? `词书已创建，${incompleteCount} 个词条待补全`
              : '词书已创建'
          )
      showToast(successMessage, 'success')
      navigate(isAppendMode ? '/books' : '/plan')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : '词书保存失败')
    } finally {
      setIsSaving(false)
    }
  }, [
    appendBookId,
    chapterWordTarget,
    chapters,
    educationStage,
    examType,
    hasLoadedExistingBook,
    ieltsSkill,
    isAppendMode,
    navigate,
    shareEnabled,
    showToast,
    title,
    totalWords,
  ])

  return {
    title,
    educationStage,
    examType,
    ieltsSkill,
    chapterWordTarget,
    shareEnabled,
    importMode,
    chapters,
    chapterIndexBase,
    existingChapterCount,
    existingWordCount,
    reorderMode,
    draggedChapterId,
    csvSummary,
    formError,
    isAppendMode,
    isSaving,
    isLoadingExistingBook,
    totalWords,
    setTitle,
    setEducationStage,
    setExamType,
    setIeltsSkill,
    setChapterWordTarget,
    setShareEnabled,
    setImportMode,
    setReorderMode,
    addChapter,
    removeChapter,
    updateChapterTitle,
    updateChapterBody,
    moveChapter,
    handleDragStart,
    handleDragOver,
    handleDrop,
    handleCsvFile,
    saveBook,
    cancel: () => navigate(isAppendMode ? '/books' : '/plan'),
  }
}
