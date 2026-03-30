import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAllBookProgress, useMyBooks, useVocabBooks, useWrongWords } from '../features/vocabulary/hooks'
import { useResponsivePageSkeletonCount } from '../hooks/useResponsiveSkeletonCount'
import type { Chapter } from './ChapterModal'
import ChapterModal from './ChapterModal'
import PlanModal from './PlanModal'
import { PageReady, PageSkeleton } from './ui'

interface Book {
  id: string
  title: string
  word_count: number
  is_paid?: boolean
  description?: string
}

interface BookProgress {
  current_index: number
}

interface StudyPlan {
  bookId: string
  dailyCount: number
  totalDays: number
  startIndex: number
}

export default function HomePage() {
  const navigate = useNavigate()
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [showChapterModal, setShowChapterModal] = useState(false)

  const { books, loading: booksLoading } = useVocabBooks()
  const { progressMap, loading: progressLoading } = useAllBookProgress()
  const { myBookIds, loading: myBooksLoading, addBook, removeBook } = useMyBooks()
  const { words: wrongWords } = useWrongWords()
  const { containerRef, count: skeletonCount } = useResponsivePageSkeletonCount({
    minColumnWidth: 260,
    gap: 10,
  })

  const myBooks = useMemo(
    () => (books as Book[]).filter(book => myBookIds.has(book.id)),
    [books, myBookIds],
  )

  const isInitialLoading = booksLoading || progressLoading || myBooksLoading

  const handleSelectBook = (book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(!!book.is_paid)
  }

  const handleStartStudy = (plan: StudyPlan | null) => {
    if (plan) {
      localStorage.setItem('study_plan', JSON.stringify(plan))
    }
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    navigate(`/practice?book=${selectedBook?.id}`)
  }

  const handleSelectChapter = (chapter: Chapter, startIndex: number) => {
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    localStorage.setItem('selected_chapter', JSON.stringify({ id: chapter.id, title: chapter.title }))
    localStorage.setItem('chapter_start_index', String(startIndex))
    navigate(`/practice?book=${selectedBook?.id}&chapter=${chapter.id}`)
  }

  const handleRemoveBook = (bookId: string, e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation()
    removeBook(bookId)
  }

  return (
    <div className="study-center-page">
      <div className="page-content" ref={containerRef}>
        <PageReady
          ready={!isInitialLoading}
          fallback={<PageSkeleton variant="books" itemCount={skeletonCount} bookMinWidth={260} />}
        >
          <div className="study-center-grid">
            {myBooks.map((book: Book) => {
              const progress = progressMap[book.id] as BookProgress | undefined
              const currentIndex = progress?.current_index || 0
              const progressPercent = Math.min(100, Math.round((currentIndex / book.word_count) * 100))
              const isActive = currentIndex > 0 && progressPercent < 100
              const isComplete = progressPercent === 100

              return (
                <div
                  key={book.id}
                  className="study-book-card study-book-card-main"
                  onClick={() => handleSelectBook(book)}
                >
                  <button
                    className="study-book-remove"
                    onClick={(e) => handleRemoveBook(book.id, e)}
                    title="移除"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                  <div className="study-book-icon-row">
                    <div className="study-book-icon study-book-icon--accent">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                      </svg>
                    </div>
                    <div className="study-book-header">
                      <h3 className="study-book-title">{book.title}</h3>
                      {book.is_paid && <span className="study-book-badge">付费</span>}
                      {isActive && <span className="study-book-state study-book-state--active">进行中</span>}
                      {isComplete && <span className="study-book-state study-book-state--complete">已完成</span>}
                    </div>
                  </div>
                  <div className="study-book-progress-text">
                    {currentIndex} / {book.word_count} 词
                  </div>
                  <div className="study-book-progress-bar">
                    <progress
                      className="study-book-progress-fill"
                      max="100"
                      value={progressPercent}
                    />
                  </div>
                  <div className="study-book-stats">
                    <span>{progressPercent}% 完成</span>
                    {isComplete && <span className="study-book-status-complete">全部完成</span>}
                  </div>
                </div>
              )
            })}

            <div
              className="study-book-card study-book-card-review"
              onClick={() => navigate('/errors')}
            >
              <div className="study-review-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div className="study-review-info">
                <div className="study-review-title">错词本</div>
                <div className={`study-review-count ${wrongWords.length > 0 ? 'has-errors' : ''}`}>
                  {wrongWords.length > 0 ? `${wrongWords.length} 个待复习` : '暂无错词'}
                </div>
              </div>
              <div className="study-review-arrow">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </div>
            </div>

            <div
              className="study-add-card"
              onClick={() => navigate('/books')}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span>添加词书</span>
            </div>
          </div>
        </PageReady>
      </div>

      {selectedBook && showChapterModal && (
        <ChapterModal
          key={`chapter-${selectedBook.id}-${showChapterModal}`}
          book={selectedBook}
          progress={progressMap[selectedBook.id]}
          onClose={() => {
            setSelectedBook(null)
            setShowChapterModal(false)
          }}
          onSelectChapter={handleSelectChapter}
        />
      )}

      {selectedBook && !showChapterModal && (
        <PlanModal
          book={selectedBook}
          progress={progressMap[selectedBook.id]}
          onClose={() => setSelectedBook(null)}
          onStart={handleStartStudy}
        />
      )}
    </div>
  )
}
