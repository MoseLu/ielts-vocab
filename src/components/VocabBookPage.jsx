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

// Study type filter rows (visual grouping)
const STUDY_TYPES = [
  { key: null, label: '全部' },
  { key: 'ielts', label: '雅思' },
  { key: 'toefl', label: '托福' },
  { key: 'gre', label: 'GRE' },
  { key: 'other', label: '其他' },
]

const SKILL_TYPES = [
  { key: null, label: '全部' },
  { key: 'listening', label: '听力' },
  { key: 'reading', label: '阅读' },
  { key: 'writing', label: '写作' },
  { key: 'speaking', label: '口语' },
  { key: 'comprehensive', label: '综合' },
]

const LEVEL_TYPES = [
  { key: null, label: '全部' },
  { key: 'beginner', label: '初级' },
  { key: 'intermediate', label: '中级' },
  { key: 'advanced', label: '高级' },
]

function VocabBookCard({ book, progress, onSelect }) {
  const currentIndex = progress?.current_index || 0
  const progressPercent = progress
    ? Math.round((currentIndex / book.word_count) * 100)
    : 0

  return (
    <div
      className="vb-card"
      onClick={() => onSelect(book)}
    >
      {book.is_paid && <span className="vb-card-badge">付费</span>}
      <h3 className="vb-card-title">{book.title}</h3>
      <div className="vb-card-meta">
        <span className="vb-card-count">{book.word_count} 词</span>
        {book.description && (
          <span className="vb-card-desc">{book.description}</span>
        )}
      </div>
      {progress && currentIndex > 0 && (
        <div className="vb-card-progress">
          <div className="vb-card-progress-bar">
            <div className="vb-card-progress-fill" style={{ width: `${progressPercent}%` }} />
          </div>
          <span className="vb-card-progress-text">{currentIndex}/{book.word_count}</span>
        </div>
      )}
    </div>
  )
}

function VocabBookPage() {
  const navigate = useNavigate()
  const [activeStudyType, setActiveStudyType] = useState(null)
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

  const filteredBooks = searchQuery.trim()
    ? books.filter(book =>
        book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (book.description || '').toLowerCase().includes(searchQuery.toLowerCase())
      )
    : books

  return (
    <div className="vocab-book-page">
      {/* Filter Header */}
      <div className="vb-filters">
        <div className="vb-filter-left">
          {/* Row 1: Study type */}
          <div className="vb-filter-row">
            {STUDY_TYPES.map(t => (
              <button
                key={String(t.key)}
                className={`vb-filter-btn${activeStudyType === t.key ? ' active' : ''}`}
                onClick={() => setActiveStudyType(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Row 2: Skill/Category */}
          <div className="vb-filter-row">
            {SKILL_TYPES.map(t => (
              <button
                key={String(t.key)}
                className={`vb-filter-btn${activeCategory === t.key ? ' active' : ''}`}
                onClick={() => setActiveCategory(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Row 3: Level */}
          <div className="vb-filter-row">
            {LEVEL_TYPES.map(t => (
              <button
                key={String(t.key)}
                className={`vb-filter-btn${activeLevel === t.key ? ' active' : ''}`}
                onClick={() => setActiveLevel(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="vb-search">
          <input
            type="text"
            placeholder="搜索词书"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="vb-search-input"
          />
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="vb-search-icon">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>
      </div>

      {/* Book Grid */}
      <div className="vb-main">
        {loading ? (
          <div className="vocab-book-loading">
            <div className="loading-spinner" />
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
          <div className="vb-grid">
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
