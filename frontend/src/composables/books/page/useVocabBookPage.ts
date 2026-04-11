import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useAllBookProgress,
  useMyBooks,
  useVocabBooks,
} from '../../../features/vocabulary/hooks'
import { useResponsivePageSkeletonCount } from '../../../hooks/useResponsiveSkeletonCount'
import { buildBookPracticePath } from '../../../lib'
import type { Book } from '../../../types'
import type { Chapter } from '../../../components/books/dialogs/ChapterModal'

interface StudyPlan {
  bookId: string | number
  dailyCount: number
  totalDays: number
  startIndex: number
}

export function useVocabBookPage() {
  const navigate = useNavigate()
  const [activeStudyType, setActiveStudyType] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [activeLevel, setActiveLevel] = useState<string | null>(null)
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [showChapterModal, setShowChapterModal] = useState(false)

  const { books, loading, error } = useVocabBooks()
  const { progressMap, loading: progressLoading } = useAllBookProgress()
  const { myBookIds, loading: myBooksLoading, addBook } = useMyBooks()
  const { containerRef, count: skeletonCount } = useResponsivePageSkeletonCount({
    minColumnWidth: 220,
    gap: 10,
  })

  const isInitialLoading = loading || progressLoading || myBooksLoading

  const handleSelectBook = useCallback((book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(true)
  }, [addBook, myBookIds])

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

  const filteredBooks = useMemo(() => {
    return books.filter(book => {
      if (activeStudyType && book.study_type !== activeStudyType) return false
      if (activeCategory && book.category !== activeCategory) return false
      if (activeLevel && book.level !== activeLevel) return false
      return true
    })
  }, [activeCategory, activeLevel, activeStudyType, books])

  const closeChapterModal = useCallback(() => {
    setSelectedBook(null)
    setShowChapterModal(false)
  }, [])

  const fallbackToPlanModal = useCallback(() => {
    setShowChapterModal(false)
  }, [])

  const closePlanModal = useCallback(() => {
    setSelectedBook(null)
  }, [])

  return {
    activeStudyType,
    activeCategory,
    activeLevel,
    selectedBook,
    showChapterModal,
    filteredBooks,
    progressMap,
    myBookIds,
    error,
    isInitialLoading,
    containerRef,
    skeletonCount,
    selectedBookProgress: selectedBook ? progressMap[selectedBook.id] : undefined,
    setActiveStudyType,
    setActiveCategory,
    setActiveLevel,
    handleSelectBook,
    handleSelectChapter,
    handleStartStudy,
    closeChapterModal,
    fallbackToPlanModal,
    closePlanModal,
  }
}
