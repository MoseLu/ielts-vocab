import { useMemo, useState, type MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useAllBookProgress,
  useLearningStats,
  useMyBooks,
  useVocabBooks,
} from '../../../features/vocabulary/hooks'
import { buildWrongWordsPracticeQuery } from '../../../features/vocabulary/wrongWordsFilters'
import { useResponsivePageSkeletonCount } from '../../../hooks/useResponsiveSkeletonCount'
import { buildBookPracticePath } from '../../../lib'
import type { Book, BookProgress } from '../../../types'
import type { Chapter } from '../../books/dialogs/ChapterModal'
import ChapterModal from '../../books/dialogs/ChapterModal'
import PlanModal from '../../books/dialogs/PlanModal'
import {
  MyBookCard,
  StudyGuidancePanel,
  TodoTaskRow,
} from './HomePageSections'
import {
  buildStudyGuidanceSection,
  buildTaskGuidanceSteps,
  buildStudyBookCards,
  type DailyPlanAction,
  type DailyPlanTask,
  type StudyPlan,
} from './homePageModels'
import { PageReady, PageSkeleton } from '../../ui'

function requestPracticeMode(mode?: string | null) {
  if (!mode) return

  window.dispatchEvent(new CustomEvent('practice-mode-request', {
    detail: { mode },
  }))
}


export default function HomePage() {
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
    return taskList.reduce<Record<string, DailyPlanTask>>((acc, task) => {
      acc[task.id] = task
      return acc
    }, {})
  }, [taskList])

  const handleSelectBook = (book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(Boolean(book.is_paid || book.practice_mode === 'match' || book.is_auto_favorites))
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

  const handleRemoveBook = (bookId: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    removeBook(bookId)
  }

  const openBookFromAction = (bookId?: string | null) => {
    const targetBook = books.find(book => book.id === bookId)
      ?? focusBookCard?.book
      ?? null

    if (!targetBook) {
      navigate('/books')
      return
    }

    handleSelectBook(targetBook as Book)
  }

  const runDailyPlanAction = (action?: DailyPlanAction | null) => {
    if (!action) return

    switch (action.kind) {
      case 'add-book':
        navigate('/books')
        return
      case 'due-review':
        requestPracticeMode(action.mode ?? 'quickmemory')
        navigate('/practice?review=due')
        return
      case 'error-review': {
        requestPracticeMode(action.mode)
        const query = buildWrongWordsPracticeQuery({
          scope: 'pending',
          dimFilter: action.dimension ?? 'all',
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
  }

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

  return (
    <div className="study-center-page">
      <div className="page-content" ref={containerRef}>
        <PageReady
          ready={!isInitialLoading}
          fallback={<PageSkeleton variant="books" itemCount={skeletonCount} bookMinWidth={260} />}
        >
          <div className="study-center-shell">
            <section className="study-guide-panel">
              <div className="study-center-grid">
                {bookCards.map(card => (
                  <MyBookCard
                    key={card.book.id}
                    card={card}
                    onSelect={handleSelectBook}
                    onRemove={handleRemoveBook}
                  />
                ))}

                <button
                  type="button"
                  className="study-add-card"
                  onClick={() => navigate('/books')}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  <span>{bookCards.length > 0 ? '添加或切换词书' : '添加第一本词书'}</span>
                </button>
              </div>
            </section>

            <section className="study-guidance-panel">
              <StudyGuidancePanel guidance={studyGuidance} />
            </section>

            <section className="study-todo-panel">
              {taskList.length > 0 ? (
                <ol className="study-todo-list" aria-label="今日待办列表">
                  {taskList.map(task => (
                    <TodoTaskRow
                      key={task.id}
                      task={task}
                      onAction={runDailyPlanAction}
                    />
                  ))}
                </ol>
              ) : (
                <div className="study-todo-empty">
                  待办还在同步，先从词书开始。
                </div>
              )}
            </section>
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
