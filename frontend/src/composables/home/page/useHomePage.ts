import { useCallback, useMemo, useState, type MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHomeTodos } from '../../../features/home/hooks/useHomeTodos'
import {
  useAllBookProgress,
  useLearningStats,
  useMyBooks,
  useVocabBooks,
} from '../../../features/vocabulary/hooks'
import { useResponsivePageSkeletonCount } from '../../../hooks/useResponsiveSkeletonCount'
import { buildBookStudyEntryPath, type BookEntryMode } from '../../../lib'
import type { Book, BookProgress } from '../../../types'
import type { Chapter } from '../../../components/books/dialogs/ChapterModal'
import {
  buildStudyBookCards,
  buildStudyGuidanceSection,
  buildTaskGuidanceSteps,
  type DailyPlanTask,
  type StudyPlan,
} from '../../../components/home/page/homePageModels'

export function useHomePage() {
  const navigate = useNavigate()
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [showChapterModal, setShowChapterModal] = useState(false)

  const { books, loading: booksLoading } = useVocabBooks()
  const { progressMap, loading: progressLoading } = useAllBookProgress()
  const { myBookIds, loading: myBooksLoading, addBook, removeBook } = useMyBooks()
  const { learnerProfile, alltime, loading: learningStatsLoading } = useLearningStats(7, 'all', 'all')
  const {
    primaryItems,
    overflowItems,
    loading: homeTodosLoading,
    error: homeTodosError,
  } = useHomeTodos()
  const { containerRef, count: skeletonCount } = useResponsivePageSkeletonCount({
    minColumnWidth: 260,
    gap: 10,
  })

  const isInitialLoading = booksLoading || progressLoading || myBooksLoading || learningStatsLoading || homeTodosLoading

  const bookCards = useMemo(() => (
    buildStudyBookCards(
      books as Book[],
      myBookIds,
      progressMap as Record<string, BookProgress | undefined>,
    )
  ), [books, myBookIds, progressMap])

  const focusBookCard = useMemo(() => {
    return bookCards.find(card => !card.isComplete) ?? bookCards[0] ?? null
  }, [bookCards])

  const decorateTask = useCallback((task: DailyPlanTask) => ({
    ...task,
    steps: task.steps?.length
      ? task.steps
      : buildTaskGuidanceSteps(task, { focusBookTitle: focusBookCard?.book.title ?? null }),
  }), [focusBookCard])

  const primaryTaskList = useMemo(() => (
    primaryItems.map(task => decorateTask(task as DailyPlanTask))
  ), [decorateTask, primaryItems])

  const overflowTaskList = useMemo(() => (
    overflowItems.map(task => decorateTask(task as DailyPlanTask))
  ), [decorateTask, overflowItems])

  const taskList = useMemo(() => (
    [...primaryTaskList, ...overflowTaskList]
  ), [overflowTaskList, primaryTaskList])

  const taskMap = useMemo(() => {
    return taskList.reduce<Record<string, DailyPlanTask>>((result, task) => {
      result[task.id] = task
      return result
    }, {})
  }, [taskList])

  const handleSelectBook = useCallback((book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(Boolean(
      book.is_paid
      || book.practice_mode === 'match'
      || book.is_auto_favorites
      || book.is_custom_book
    ))
  }, [addBook, myBookIds])

  const closeChapterModal = useCallback(() => {
    setSelectedBook(null)
    setShowChapterModal(false)
  }, [])

  const closePlanModal = useCallback(() => {
    setSelectedBook(null)
  }, [])

  const handleStartStudy = useCallback((plan: StudyPlan | null, entryMode: BookEntryMode = 'practice') => {
    if (plan) {
      localStorage.setItem('study_plan', JSON.stringify(plan))
    }
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    if (!selectedBook) return
    navigate(buildBookStudyEntryPath(selectedBook, entryMode))
  }, [navigate, selectedBook])

  const handleSelectChapter = useCallback((
    chapter: Chapter,
    startIndex: number,
    entryMode: BookEntryMode = 'practice',
  ) => {
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    localStorage.setItem('selected_chapter', JSON.stringify({ id: chapter.id, title: chapter.title }))
    localStorage.setItem('chapter_start_index', String(startIndex))
    if (!selectedBook) return
    navigate(buildBookStudyEntryPath(selectedBook, entryMode, chapter.id))
  }, [navigate, selectedBook])

  const handleRemoveBook = useCallback((bookId: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    removeBook(bookId)
  }, [removeBook])

  const reviewTask = taskMap['due-review']
  const errorTask = taskMap['error-review']
  const studyGuidance = useMemo(() => buildStudyGuidanceSection({
    learnerProfile,
    alltime,
    reviewTask,
    errorTask,
    focusBookTitle: focusBookCard?.book.title ?? null,
    focusBookRemainingWords: focusBookCard?.remainingWords ?? null,
  }), [alltime, errorTask, focusBookCard, learnerProfile, reviewTask])

  return {
    selectedBook,
    showChapterModal,
    selectedBookProgress: selectedBook ? progressMap[selectedBook.id] : undefined,
    containerRef,
    skeletonCount,
    isInitialLoading,
    bookCards,
    taskList,
    todoError: homeTodosError,
    studyGuidance,
    handleSelectBook,
    handleRemoveBook,
    handleSelectChapter,
    handleStartStudy,
    navigateToBooks: () => navigate('/books/create'),
    closeChapterModal,
    closePlanModal,
  }
}
