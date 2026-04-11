import { useCallback, useMemo, useState, type MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useAllBookProgress,
  useLearningStats,
  useMyBooks,
  useVocabBooks,
} from '../../../features/vocabulary/hooks'
import { buildWrongWordsPracticeQuery, type WrongWordDimensionFilter } from '../../../features/vocabulary/wrongWordsFilters'
import { useResponsivePageSkeletonCount } from '../../../hooks/useResponsiveSkeletonCount'
import { buildBookPracticePath } from '../../../lib'
import { requestPracticeMode } from '../../practice/page/practiceModeEvents'
import type { Book, BookProgress } from '../../../types'
import type { Chapter } from '../../../components/books/dialogs/ChapterModal'
import {
  buildStudyBookCards,
  buildStudyGuidanceSection,
  buildTaskGuidanceSteps,
  type DailyPlanAction,
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
  const { containerRef, count: skeletonCount } = useResponsivePageSkeletonCount({
    minColumnWidth: 260,
    gap: 10,
  })

  const isInitialLoading = booksLoading || progressLoading || myBooksLoading || learningStatsLoading

  const bookCards = useMemo(() => (
    buildStudyBookCards(
      books as Book[],
      myBookIds,
      progressMap as Record<string, BookProgress | undefined>,
    )
  ), [books, myBookIds, progressMap])

  const dailyPlan = learnerProfile?.daily_plan
  const rawTaskList = dailyPlan?.tasks ?? []

  const focusBookCard = useMemo(() => {
    const focusBookId = dailyPlan?.focus_book?.book_id
    if (focusBookId) {
      const matched = bookCards.find(card => card.book.id === focusBookId)
      if (matched) return matched
    }

    return bookCards.find(card => !card.isComplete) ?? bookCards[0] ?? null
  }, [bookCards, dailyPlan])

  const taskList = useMemo(() => {
    const focusBookTitle = dailyPlan?.focus_book?.title ?? focusBookCard?.book.title ?? null
    return rawTaskList.map(task => ({
      ...task,
      steps: buildTaskGuidanceSteps(task, { focusBookTitle }),
    }))
  }, [dailyPlan, focusBookCard, rawTaskList])

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
    setShowChapterModal(Boolean(book.is_paid || book.practice_mode === 'match' || book.is_auto_favorites))
  }, [addBook, myBookIds])

  const closeChapterModal = useCallback(() => {
    setSelectedBook(null)
    setShowChapterModal(false)
  }, [])

  const closePlanModal = useCallback(() => {
    setSelectedBook(null)
  }, [])

  const handleStartStudy = useCallback((plan: StudyPlan | null) => {
    if (plan) {
      localStorage.setItem('study_plan', JSON.stringify(plan))
    }
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    if (!selectedBook) return
    navigate(buildBookPracticePath(selectedBook))
  }, [navigate, selectedBook])

  const handleSelectChapter = useCallback((chapter: Chapter, startIndex: number) => {
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    localStorage.setItem('selected_chapter', JSON.stringify({ id: chapter.id, title: chapter.title }))
    localStorage.setItem('chapter_start_index', String(startIndex))
    if (!selectedBook) return
    navigate(buildBookPracticePath(selectedBook, chapter.id))
  }, [navigate, selectedBook])

  const handleRemoveBook = useCallback((bookId: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    removeBook(bookId)
  }, [removeBook])

  const openBookFromAction = useCallback((bookId?: string | null) => {
    const targetBook = books.find(book => book.id === bookId)
      ?? focusBookCard?.book
      ?? null

    if (!targetBook) {
      navigate('/books')
      return
    }

    handleSelectBook(targetBook as Book)
  }, [books, focusBookCard, handleSelectBook, navigate])

  const runDailyPlanAction = useCallback((action?: DailyPlanAction | null) => {
    if (!action) return

    switch (action.kind) {
      case 'add-book':
        navigate('/books/create')
        return
      case 'due-review':
        requestPracticeMode(action.mode ?? 'quickmemory')
        navigate('/practice?review=due')
        return
      case 'error-review': {
        requestPracticeMode(action.mode)
        const dimFilter: WrongWordDimensionFilter = (
          action.dimension === 'recognition'
          || action.dimension === 'listening'
          || action.dimension === 'meaning'
          || action.dimension === 'dictation'
        ) ? action.dimension : 'all'
        const query = buildWrongWordsPracticeQuery({
          scope: 'pending',
          dimFilter,
        })
        navigate(query ? `/practice?mode=errors&${query}` : '/practice?mode=errors')
        return
      }
      case 'continue-book':
        openBookFromAction(action.book_id)
        return
      default:
        return
    }
  }, [navigate, openBookFromAction])

  const reviewTask = taskMap['due-review']
  const errorTask = taskMap['error-review']
  const studyGuidance = useMemo(() => buildStudyGuidanceSection({
    learnerProfile,
    alltime,
    reviewTask,
    errorTask,
    focusBookTitle: dailyPlan?.focus_book?.title ?? focusBookCard?.book.title ?? null,
    focusBookRemainingWords:
      dailyPlan?.focus_book?.remaining_words
      ?? focusBookCard?.remainingWords
      ?? null,
  }), [alltime, dailyPlan, errorTask, focusBookCard, learnerProfile, reviewTask])

  return {
    selectedBook,
    showChapterModal,
    selectedBookProgress: selectedBook ? progressMap[selectedBook.id] : undefined,
    containerRef,
    skeletonCount,
    isInitialLoading,
    bookCards,
    taskList,
    studyGuidance,
    handleSelectBook,
    handleRemoveBook,
    handleSelectChapter,
    handleStartStudy,
    runDailyPlanAction,
    navigateToBooks: () => navigate('/books/create'),
    closeChapterModal,
    closePlanModal,
  }
}
