import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVocabBooks, useAllBookProgress } from '../features/vocabulary/hooks'
import type { Book, BookProgress } from '../types'
import PlanModal from './PlanModal'
import ChapterModal, { Chapter } from './ChapterModal'

// Data types — compatible with ChapterModal / PlanModal

interface StudyPlan {
  bookId: string | number
  dailyCount: number
  totalDays: number
  startIndex: number
}

// Filter row type
interface FilterOption {
  key: string | null
  label: string
}

// VocabBookCard props
interface VocabBookCardProps {
  book: Book
  progress?: BookProgress
  onSelect: (book: Book) => void
  isInMyBooks: boolean
}

const CATEGORY_LABELS: Record<string, string> = {
  listening: '听力',
  reading: '阅读',
  writing: '写作',
  speaking: '口语',
  academic: '学术',
  comprehensive: '综合',
  phrases: '短语'
}

const LEVEL_LABELS: Record<string, string> = {
  beginner: '初级',
  intermediate: '中级',
  advanced: '高级'
}

// Study type filter rows (visual grouping)
const STUDY_TYPES: FilterOption[] = [
  { key: null, label: '全部' },
  { key: 'ielts', label: '雅思' },
  { key: 'toefl', label: '托福' },
  { key: 'gre', label: 'GRE' },
  { key: 'other', label: '其他' },
]

const SKILL_TYPES: FilterOption[] = [
  { key: null, label: '全部' },
  { key: 'listening', label: '听力' },
  { key: 'reading', label: '阅读' },
  { key: 'writing', label: '写作' },
  { key: 'speaking', label: '口语' },
  { key: 'comprehensive', label: '综合' },
]

const LEVEL_TYPES: FilterOption[] = [
  { key: null, label: '全部' },
  { key: 'beginner', label: '初级' },
  { key: 'intermediate', label: '中级' },
  { key: 'advanced', label: '高级' },
]

function VocabBookCard({ book, progress, onSelect, isInMyBooks }: VocabBookCardProps) {
  const currentIndex = progress?.current_index || 0
  const progressPercent = progress
    ? Math.round((currentIndex / book.word_count) * 100)
    : 0

  return (
    <div
      className="vb-card"
      onClick={() => onSelect(book)}
    >
      {book.is_paid && <span className="vb-card-badge">已购</span>}
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
      {isInMyBooks && (
        <div className="vb-card-added">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          已添加
        </div>
      )}
    </div>
  )
}

function VocabBookPage() {
  const navigate = useNavigate()
  const [activeStudyType, setActiveStudyType] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [activeLevel, setActiveLevel] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [myBooks, setMyBooks] = useState<Book[]>([])
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [showChapterModal, setShowChapterModal] = useState(false)

  const { books, loading, error } = useVocabBooks({
    category: activeCategory ?? undefined,
    level: activeLevel ?? undefined,
    studyType: activeStudyType ?? undefined,
  })
  const { progressMap } = useAllBookProgress()

  // Load my books
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

  const handleSelectBook = (book: Book) => {
    // Add to my books if not already added
    if (!myBooks.find(b => b.id === book.id)) {
      const newBooks = [...myBooks, book]
      setMyBooks(newBooks)
      localStorage.setItem('my_books', JSON.stringify(newBooks))
    }

    // Books with chapters show ChapterModal; books without chapters show PlanModal
    setSelectedBook(book)
    setShowChapterModal(book.has_chapters !== false)
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
                isInMyBooks={myBooks.some(b => b.id === book.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {selectedBook && showChapterModal && (
        <ChapterModal
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

export default VocabBookPage
