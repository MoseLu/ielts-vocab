import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVocabBooks, useAllBookProgress, useMyBooks } from '../../../features/vocabulary/hooks'
import { useResponsivePageSkeletonCount } from '../../../hooks/useResponsiveSkeletonCount'
import { buildBookPracticePath } from '../../../lib'
import type { Book, BookProgress } from '../../../types'
import PlanModal from '../dialogs/PlanModal'
import ChapterModal, { Chapter } from '../dialogs/ChapterModal'
import { PageSkeleton } from '../../ui'
import { Page, PageContent, PageHeader, PageScroll } from '../../layout'

interface StudyPlan {
  bookId: string | number
  dailyCount: number
  totalDays: number
  startIndex: number
}

interface FilterOption {
  key: string | null
  label: string
}

interface VocabBookCardProps {
  book: Book
  progress?: BookProgress
  onSelect: (book: Book) => void
  isInMyBooks: boolean
}

const CONFUSABLE_BOOK_ID = 'ielts_confusable_match'

function isConfusableBook(book: Pick<Book, 'id'>): boolean {
  return String(book.id) === CONFUSABLE_BOOK_ID
}

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
  { key: 'confusable', label: '辨析' },
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
    ? Math.min(100, Math.round((currentIndex / book.word_count) * 100))
    : 0
  const isConfusable = isConfusableBook(book)
  const countValue = isConfusable ? book.group_count ?? 0 : book.word_count
  const countUnit = isConfusable ? '组' : '词'
  const progressText = isConfusable ? `${progressPercent}%` : `${currentIndex}/${book.word_count}`

  return (
    <div className="vb-card" onClick={() => onSelect(book)}>
      {book.is_paid && <span className="vb-card-badge">已购</span>}
      <h3 className="vb-card-title">{book.title}</h3>
      <div className="vb-card-meta">
        <span className="vb-card-count">{countValue} {countUnit}</span>
        {book.description && <span className="vb-card-desc">{book.description}</span>}
      </div>
      {progress && (
        <div className="vb-card-progress">
          <div
            className="vb-card-progress-bar"
            role="progressbar"
            aria-label={`${book.title} 学习进度`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercent}
          >
            <div
              className="vb-card-progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="vb-card-progress-text">{progressText}</span>
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

  const handleSelectBook = (book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(true)
  }

  const handleStartStudy = (plan: StudyPlan | null) => {
    if (plan) {
      localStorage.setItem('study_plan', JSON.stringify(plan))
    }
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    if (!selectedBook) return
    navigate(buildBookPracticePath(selectedBook))
  }

  const handleSelectChapter = (chapter: Chapter, startIndex: number) => {
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    localStorage.setItem('selected_chapter', JSON.stringify({ id: chapter.id, title: chapter.title }))
    localStorage.setItem('chapter_start_index', String(startIndex))
    if (!selectedBook) return
    navigate(buildBookPracticePath(selectedBook, chapter.id))
  }

  const filteredBooks = books.filter(book => {
    if (activeStudyType && book.study_type !== activeStudyType) return false
    if (activeCategory && book.category !== activeCategory) return false
    if (activeLevel && book.level !== activeLevel) return false
    return true
  })

  return (
    <Page className="vocab-book-page">
      <PageHeader className="vb-page-header">
        <div className="vb-filters">
          <div className="vb-filter-left">
            <div className="vb-filter-row vb-filter-row--compact">
              {STUDY_TYPES.map(t => (
                <button
                  key={String(t.key)}
                  className={`vb-filter-btn vb-filter-btn--compact${activeStudyType === t.key ? ' active' : ''}`}
                  onClick={() => setActiveStudyType(t.key)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              {SKILL_TYPES.map(t => (
                <button
                  key={String(t.key)}
                  className={`vb-filter-btn vb-filter-btn--compact${activeCategory === t.key ? ' active' : ''}`}
                  onClick={() => setActiveCategory(t.key)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              {LEVEL_TYPES.map(t => (
                <button
                  key={String(t.key)}
                  className={`vb-filter-btn vb-filter-btn--compact${activeLevel === t.key ? ' active' : ''}`}
                  onClick={() => setActiveLevel(t.key)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </PageHeader>

      <PageContent className="vb-page-body">
        <PageScroll className="vb-main">
          <div ref={containerRef}>
            {isInitialLoading ? (
              <PageSkeleton variant="books" itemCount={skeletonCount} bookMinWidth={220} />
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
                    isInMyBooks={myBookIds.has(book.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </PageScroll>
      </PageContent>

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
          onFallback={() => setShowChapterModal(false)}
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
    </Page>
  )
}

export default VocabBookPage
