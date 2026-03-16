import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVocabBooks, useAllBookProgress } from '../hooks/useVocabBooks'
import PlanModal from './PlanModal'

function HomePage({ user }) {
  const navigate = useNavigate()
  const [myBooks, setMyBooks] = useState([])
  const [selectedBook, setSelectedBook] = useState(null)

  const { books, loading: booksLoading } = useVocabBooks()
  const { progressMap, loading: progressLoading } = useAllBookProgress()

  const wrongWords = JSON.parse(localStorage.getItem('wrong_words') || '[]')

  // Load user's selected books
  useEffect(() => {
    const savedBooks = localStorage.getItem('my_books')
    if (savedBooks) {
      try {
        setMyBooks(JSON.parse(savedBooks))
      } catch (e) {
        setMyBooks([])
      }
    }
  }, [])

  // Sync with available books
  useEffect(() => {
    if (!booksLoading && books.length > 0 && myBooks.length > 0) {
      const bookIds = new Set(books.map(b => b.id))
      const validBooks = myBooks.filter(b => bookIds.has(b.id))
      if (validBooks.length !== myBooks.length) {
        setMyBooks(validBooks)
        localStorage.setItem('my_books', JSON.stringify(validBooks))
      }
    }
  }, [books, booksLoading, myBooks])

  const handleSelectBook = (book) => {
    setSelectedBook(book)
  }

  const handleStartStudy = (plan) => {
    if (plan) {
      localStorage.setItem('study_plan', JSON.stringify(plan))
    }
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    navigate(`/practice?book=${selectedBook.id}`)
  }

  const handleRemoveBook = (bookId, e) => {
    e.stopPropagation()
    const newBooks = myBooks.filter(b => b.id !== bookId)
    setMyBooks(newBooks)
    localStorage.setItem('my_books', JSON.stringify(newBooks))
  }

  // Calculate total stats
  const totalLearned = Object.values(progressMap).reduce((sum, p) => sum + (p?.current_index || 0), 0)
  const totalWords = myBooks.reduce((sum, b) => sum + (b.word_count || 0), 0)

  // Find last active book
  const lastActiveBook = myBooks.reduce((last, book) => {
    const progress = progressMap[book.id]
    if (progress?.current_index > 0) {
      if (!last || (progressMap[last.id]?.current_index || 0) < progress.current_index) {
        return book
      }
    }
    return last
  }, null)

  return (
    <div className="study-center-page">
      <div className="study-center-grid">

        {/* My book cards */}
        {myBooks.map(book => {
          const progress = progressMap[book.id]
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
              <div className="study-book-header">
                <h3 className="study-book-title">{book.title}</h3>
              </div>
              <div className="study-book-progress-text">
                {currentIndex} / {book.word_count}
              </div>
              <div className="study-book-progress-bar">
                <div
                  className="study-book-progress-fill"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="study-book-stats">
                <span>{progressPercent}% 完成</span>
              </div>
            </div>
          )
        })}

        {/* Quick start card - only show if has active book */}
        {lastActiveBook && (
          <div
            className="study-book-card study-book-card-cta"
            onClick={() => handleSelectBook(lastActiveBook)}
          >
            <div className="study-cta-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" />
              </svg>
            </div>
            <div className="study-cta-text">
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
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="9" y1="13" x2="15" y2="13" />
              <line x1="9" y1="17" x2="15" y2="17" />
            </svg>
          </div>
          <div className="study-review-info">
            <div className="study-review-title">错词本</div>
            <div className="study-review-count">
              {wrongWords.length > 0 ? `${wrongWords.length} 个待复习` : '暂无错词'}
            </div>
          </div>
        </div>

        {/* Stats card */}
        <div className="study-book-card study-book-card-stats">
          <div className="study-stats-row">
            <div className="study-stat-item">
              <span className="study-stat-num">{myBooks.length}</span>
              <span className="study-stat-label">词书数</span>
            </div>
            <div className="study-stat-item">
              <span className="study-stat-num">{totalLearned.toLocaleString()}</span>
              <span className="study-stat-label">已学词数</span>
            </div>
            <div className="study-stat-item">
              <span className="study-stat-num">{wrongWords.length}</span>
              <span className="study-stat-label">错词数</span>
            </div>
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

      {/* Plan Modal */}
      {selectedBook && (
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

export default HomePage