import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVocabBooks, useAllBookProgress, useMyBooks, useWrongWords } from '../features/vocabulary/hooks'
import PlanModal from './PlanModal'
import ChapterModal from './ChapterModal'
import type { Chapter } from './ChapterModal'

// Type definitions
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
  const { progressMap } = useAllBookProgress()
  const { myBookIds, myBooks: myBooksRaw, resolveMyBooks, addBook, removeBook } = useMyBooks()
  const { words: wrongWords } = useWrongWords()
  const myBooks: Book[] = myBooksRaw as Book[]

  // Resolve full book objects once books are loaded
  useEffect(() => {
    if (!booksLoading && books.length > 0) {
      resolveMyBooks(books as Book[])
    }
  }, [books, booksLoading, resolveMyBooks])

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

  // Calculate total stats
  const totalLearned = Object.values(progressMap).reduce(
    (sum: number, p) => sum + ((p as BookProgress)?.current_index || 0),
    0
  )
  const totalWords = myBooks.reduce(
    (sum: number, b: Book) => sum + (b.word_count || 0),
    0
  )

  // Find last active book
  const lastActiveBook = myBooks.reduce((last: Book | null, book: Book) => {
    const progress = progressMap[book.id]
    if (progress?.current_index > 0) {
      if (!last || ((progressMap[last.id] as BookProgress)?.current_index || 0) < progress.current_index) {
        return book
      }
    }
    return last
  }, null)

  // Calculate overall progress
  const overallPercent = totalWords > 0
    ? Math.round((totalLearned / totalWords) * 100)
    : 0

  // SVG progress ring params
  const RING_R = 26
  const RING_CIRC = 2 * Math.PI * RING_R
  const ringOffset = RING_CIRC - (overallPercent / 100) * RING_CIRC

  return (
    <div className="study-center-page">
      <div className="page-content">
      {/* Welcome banner */}
      <div className="study-banner">
        <div className="study-banner-left">
          <div className="study-banner-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            学习中心
          </div>
          <div className="study-banner-text">
            <h2>{wrongWords.length > 0 ? `还有 ${wrongWords.length} 个错词待复习` : totalLearned > 0 ? '继续加油，保持学习节奏' : '选择一个词书开始学习'}</h2>
            <p>{totalLearned > 0 ? `已累计学习 ${totalLearned.toLocaleString()} 个单词` : '30天掌握 3000 个 IELTS 核心词汇'}</p>
          </div>
        </div>
        {totalWords > 0 && (
          <div className="study-progress-ring-wrap">
            <svg viewBox="0 0 64 64">
              <circle className="study-progress-ring-bg" cx="32" cy="32" r={RING_R}/>
              <circle
                className="study-progress-ring-fill"
                cx="32" cy="32" r={RING_R}
                strokeDasharray={RING_CIRC}
                strokeDashoffset={ringOffset}
              />
            </svg>
            <div className="study-progress-ring-label">
              <span className="study-progress-ring-pct">{overallPercent}%</span>
              <span className="study-progress-ring-sub">总进度</span>
            </div>
          </div>
        )}
      </div>

      <div className="study-center-grid">

        {/* My book cards */}
        {myBooks.map((book: Book) => {
          const progress = progressMap[book.id] as BookProgress | undefined
          const currentIndex = progress?.current_index || 0
          const progressPercent = Math.round((currentIndex / book.word_count) * 100)

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
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                  </svg>
                </div>
                <div className="study-book-header">
                  <h3 className="study-book-title">{book.title}</h3>
                  {book.is_paid && <span className="study-book-badge">付费</span>}
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
                {progressPercent === 100 && <span className="study-book-status-complete">全部完成</span>}
              </div>
            </div>
          )
        })}

        {/* Quick start card */}
        {lastActiveBook && (
          <div
            className="study-book-card study-book-card-cta"
            onClick={() => handleSelectBook(lastActiveBook)}
          >
            <div className="study-cta-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" stroke="none"/>
              </svg>
            </div>
            <div>
              <div className="study-cta-title">继续学习</div>
              <div className="study-cta-subtitle">{lastActiveBook.title}</div>
            </div>
          </div>
        )}

        {/* Wrong words review card */}
        <div
          className="study-book-card study-book-card-review"
          onClick={() => navigate('/errors')}
        >
          <div className="study-review-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
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
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </div>

        {/* Add new book card */}
        <div
          className="study-add-card"
          onClick={() => navigate('/')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>添加词书</span>
        </div>
      </div>
      </div>

      {/* Chapter Modal for paid books */}
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

      {/* Plan Modal for non-paid books */}
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
