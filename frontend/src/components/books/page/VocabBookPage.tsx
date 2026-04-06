import type { Book, BookProgress } from '../../../types'
import PlanModal from '../dialogs/PlanModal'
import ChapterModal from '../dialogs/ChapterModal'
import { PageSkeleton } from '../../ui'
import { Page, PageContent, PageHeader, PageScroll } from '../../layout'
import { useVocabBookPage } from '../../../composables/books/page/useVocabBookPage'

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
  const {
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
    selectedBookProgress,
    setActiveStudyType,
    setActiveCategory,
    setActiveLevel,
    handleSelectBook,
    handleSelectChapter,
    handleStartStudy,
    closeChapterModal,
    fallbackToPlanModal,
    closePlanModal,
  } = useVocabBookPage()

  return (
    <Page className="vocab-book-page">
      <PageHeader className="vb-page-header">
        <div className="vb-filters">
          <div className="vb-filter-left">
            <div className="vb-filter-row vb-filter-row--compact">
              {STUDY_TYPES.map(type => (
                <button
                  key={String(type.key)}
                  className={`vb-filter-btn vb-filter-btn--compact${activeStudyType === type.key ? ' active' : ''}`}
                  onClick={() => setActiveStudyType(type.key)}
                >
                  {type.label}
                </button>
              ))}
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              {SKILL_TYPES.map(type => (
                <button
                  key={String(type.key)}
                  className={`vb-filter-btn vb-filter-btn--compact${activeCategory === type.key ? ' active' : ''}`}
                  onClick={() => setActiveCategory(type.key)}
                >
                  {type.label}
                </button>
              ))}
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              {LEVEL_TYPES.map(type => (
                <button
                  key={String(type.key)}
                  className={`vb-filter-btn vb-filter-btn--compact${activeLevel === type.key ? ' active' : ''}`}
                  onClick={() => setActiveLevel(type.key)}
                >
                  {type.label}
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
          progress={selectedBookProgress}
          onClose={closeChapterModal}
          onSelectChapter={handleSelectChapter}
          onFallback={fallbackToPlanModal}
        />
      )}
      {selectedBook && !showChapterModal && (
        <PlanModal
          book={selectedBook}
          progress={selectedBookProgress}
          onClose={closePlanModal}
          onStart={handleStartStudy}
        />
      )}
    </Page>
  )
}

export default VocabBookPage
