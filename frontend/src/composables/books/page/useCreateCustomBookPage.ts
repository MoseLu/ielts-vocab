import { useCallback, useState, type ChangeEvent, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
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

interface CreateCustomBookResponse {
  bookId?: string
  book?: {
    id?: string
    incomplete_word_count?: number
  }
}

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items]
  const [removed] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, removed)
  return next
}

export function useCreateCustomBookPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [title, setTitle] = useState('我的自定义词书')
  const [educationStage, setEducationStage] = useState('abroad')
  const [examType, setExamType] = useState('ielts')
  const [ieltsSkill, setIeltsSkill] = useState('listening')
  const [chapterWordTarget, setChapterWordTarget] = useState(DEFAULT_CHAPTER_WORD_TARGET)
  const [shareEnabled, setShareEnabled] = useState(false)
  const [importMode, setImportMode] = useState<ImportMode>('manual')
  const [chapters, setChapters] = useState<CustomBookChapterDraft[]>([
    createChapterDraft(1, { content: '' }),
  ])
  const [reorderMode, setReorderMode] = useState(false)
  const [draggedChapterId, setDraggedChapterId] = useState<string | null>(null)
  const [csvSummary, setCsvSummary] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const totalWords = countDraftWords(chapters)

  const addChapter = useCallback(() => {
    setChapters(current => [...current, createChapterDraft(current.length + 1)])
  }, [])

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
      const parsedChapters = parseCustomBookCsv(text, chapterWordTarget)
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
  }, [chapterWordTarget])

  const saveBook = useCallback(async () => {
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
      const created = await apiFetch<CreateCustomBookResponse>('/api/books/custom-books', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const bookId = created.bookId ?? created.book?.id
      if (!bookId) throw new Error('创建结果缺少词书 ID')

      await apiFetch('/api/books/my', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId }),
      })

      const incompleteCount = created.book?.incomplete_word_count ?? 0
      showToast(
        incompleteCount > 0
          ? `词书已创建，${incompleteCount} 个词条待补全`
          : '词书已创建',
        'success',
      )
      navigate('/books')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : '词书保存失败')
    } finally {
      setIsSaving(false)
    }
  }, [
    chapterWordTarget,
    chapters,
    educationStage,
    examType,
    ieltsSkill,
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
    reorderMode,
    draggedChapterId,
    csvSummary,
    formError,
    isSaving,
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
    cancel: () => navigate('/books'),
  }
}
