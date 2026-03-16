import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVocabBooks, useAllBookProgress } from '../hooks/useVocabBooks'

const CATEGORY_LABELS = {
  listening: '听力',
  reading: '阅读',
  writing: '写作',
  speaking: '口语',
  academic: '学术',
  comprehensive: '综合',
  phrases: '短语'
}

const LEVEL_LABELS = {
  beginner: '初级',
  intermediate: '中级',
  advanced: '高级'
}

const ICONS = {
  headphones: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
      <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
    </svg>
  ),
  'book-open': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
    </svg>
  ),
  edit: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
    </svg>
  ),
  mic: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
      <line x1="12" y1="19" x2="12" y2="23"></line>
      <line x1="8" y1="23" x2="16" y2="23"></line>
    </svg>
  ),
  'graduation-cap': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
      <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"></path>
    </svg>
  ),
  library: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
    </svg>
  ),
  link: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
    </svg>
  ),
  star: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
    </svg>
  )
}

function VocabBookCard({ book, progress, onSelect }) {
  const progressPercent = progress
    ? Math.round((progress.current_index / book.word_count) * 100)
    : 0

  return (
    <div
      className="vocab-book-card"
      onClick={() => onSelect(book)}
      style={{ '--book-color': book.color }}
    >
      <div className="vocab-book-icon">
        {ICONS[book.icon] || ICONS.library}
      </div>
      <div className="vocab-book-content">
        <h3 className="vocab-book-title">{book.title}</h3>
        <p className="vocab-book-desc">{book.description}</p>
        <div className="vocab-book-meta">
          <span className="vocab-book-count">{book.word_count} 词</span>
          <span className="vocab-book-level">{LEVEL_LABELS[book.level]}</span>
        </div>
        {progress && progress.current_index > 0 && (
          <div className="vocab-book-progress">
            <div className="vocab-book-progress-bar">
              <div
                className="vocab-book-progress-fill"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
            <span className="vocab-book-progress-text">{progressPercent}%</span>
          </div>
        )}
      </div>
      <div className="vocab-book-arrow">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </div>
    </div>
  )
}

function VocabBookPage() {
  const navigate = useNavigate()
  const [activeCategory, setActiveCategory] = useState(null)
  const [activeLevel, setActiveLevel] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  const { books, loading, error } = useVocabBooks({
    category: activeCategory,
    level: activeLevel
  })
  const { progressMap } = useAllBookProgress()

  const handleSelectBook = (book) => {
    localStorage.setItem('selected_book', JSON.stringify(book))
    navigate(`/practice?book=${book.id}`)
  }

  // Filter books by search query
  const filteredBooks = searchQuery.trim()
    ? books.filter(book =>
        book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        book.description.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : books

  const categories = ['listening', 'reading', 'writing', 'speaking', 'academic', 'comprehensive']
  const levels = ['beginner', 'intermediate', 'advanced']

  return (
    <div className="vocab-book-page">
      {/* Filter Header */}
      <div className="vocab-book-filters">
        <div className="filter-header-row">
          <div className="filter-sections">
            <div className="filter-row">
              <span className="filter-label">技能维度</span>
              <div className="filter-buttons">
                <button
                  className={`filter-btn ${!activeCategory ? 'active' : ''}`}
                  onClick={() => setActiveCategory(null)}
                >
                  全部
                </button>
                {categories.map(cat => (
                  <button
                    key={cat}
                    className={`filter-btn ${activeCategory === cat ? 'active' : ''}`}
                    onClick={() => setActiveCategory(cat)}
                  >
                    {CATEGORY_LABELS[cat]}
                  </button>
                ))}
              </div>
            </div>
            <div className="filter-row">
              <span className="filter-label">难度等级</span>
              <div className="filter-buttons">
                <button
                  className={`filter-btn ${!activeLevel ? 'active' : ''}`}
                  onClick={() => setActiveLevel(null)}
                >
                  全部
                </button>
                {levels.map(level => (
                  <button
                    key={level}
                    className={`filter-btn ${activeLevel === level ? 'active' : ''}`}
                    onClick={() => setActiveLevel(level)}
                  >
                    {LEVEL_LABELS[level]}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Search Bar - Right Side */}
          <div className="vocab-search-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="M21 21l-4.35-4.35"></path>
            </svg>
            <input
              type="text"
              placeholder="搜索词书"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="vocab-search-input"
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="vocab-book-main">
        {loading ? (
          <div className="vocab-book-loading">
            <div className="loading-spinner"></div>
            <span>加载中...</span>
          </div>
        ) : error ? (
          <div className="vocab-book-error">
            <p>加载失败: {error}</p>
          </div>
        ) : filteredBooks.length === 0 ? (
          <div className="vocab-book-empty">
            <p>没有找到符合条件的词书</p>
          </div>
        ) : (
          <div className="vocab-book-grid">
            {filteredBooks.map(book => (
              <VocabBookCard
                key={book.id}
                book={book}
                progress={progressMap[book.id]}
                onSelect={handleSelectBook}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default VocabBookPage