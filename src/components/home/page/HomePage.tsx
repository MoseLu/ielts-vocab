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
  QuickActionButton,
  TodaySummaryItem,
  TodoTaskRow,
} from './HomePageSections'
import {
  buildStudyBookCards,
  formatDurationSeconds,
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
  const { learnerProfile, loading: learningStatsLoading } = useLearningStats(7, 'all', 'all')
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
  const taskList = dailyPlan?.tasks ?? []
  const taskMap = useMemo(() => {
    return taskList.reduce<Record<string, DailyPlanTask>>((acc, task) => {
      acc[task.id] = task
      return acc
    }, {})
  }, [taskList])

  const focusBookCard = useMemo(() => {
    const focusBookId = dailyPlan?.focus_book?.book_id
    if (focusBookId) {
      const matched = bookCards.find(card => card.book.id === focusBookId)
      if (matched) return matched
    }

    return bookCards.find(card => !card.isComplete) ?? bookCards[0] ?? null
  }, [bookCards, dailyPlan])

  const todayContent = dailyPlan?.today_content ?? {
    date: learnerProfile?.summary.date ?? '',
    studied_words: learnerProfile?.summary.today_words ?? 0,
    duration_seconds: learnerProfile?.summary.today_duration_seconds ?? 0,
    sessions: learnerProfile?.summary.today_sessions ?? 0,
    latest_activity_title: null,
    latest_activity_at: null,
  }

  const handleSelectBook = (book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(Boolean(book.is_paid || book.practice_mode === 'match'))
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

  const startWeakModePractice = () => {
    const weakestMode = learnerProfile?.summary.weakest_mode
    if (!weakestMode) {
      navigate('/stats')
      return
    }

    requestPracticeMode(weakestMode)
    openBookFromAction(dailyPlan?.focus_book?.book_id ?? focusBookCard?.book.id ?? null)
  }

  const focusTask = taskMap['focus-book']
  const reviewTask = taskMap['due-review']
  const errorTask = taskMap['error-review']
  const weakestModeLabel = learnerProfile?.summary.weakest_mode_label ?? '先看画像'
  const focusBookText = dailyPlan?.focus_book?.title ?? focusBookCard?.book.title ?? '未设置'

  return (
    <div className="study-center-page">
      <div className="page-content" ref={containerRef}>
        <PageReady
          ready={!isInitialLoading}
          fallback={<PageSkeleton variant="books" itemCount={skeletonCount} bookMinWidth={260} />}
        >
          <div className="study-center-shell">
            <section className="study-todo-panel">
              <div className="study-todo-head">
                <div>
                  <div className="study-todo-eyebrow">今日待办</div>
                  <h1 className="study-todo-title">今天先处理这 3 件事</h1>
                  <p className="study-todo-caption">系统会根据今天的真实学习数据自动勾选，你不用手动处理。</p>
                </div>
              </div>

              <div className="study-todo-summary">
                <TodaySummaryItem label="今天已学" value={`${todayContent.studied_words} 词`} />
                <TodaySummaryItem label="学习时长" value={formatDurationSeconds(todayContent.duration_seconds)} />
                <TodaySummaryItem label="主线词书" value={focusBookText} />
                <TodaySummaryItem
                  label="最近学习"
                  value={todayContent.latest_activity_title ?? '今天还没有新的学习记录'}
                />
              </div>

              <div className="study-todo-list">
                {taskList.length > 0 ? taskList.map(task => (
                  <TodoTaskRow
                    key={task.id}
                    task={task}
                    onAction={runDailyPlanAction}
                  />
                )) : (
                  <div className="study-todo-empty">
                    今日待办正在同步，先从词书开始也可以。
                  </div>
                )}
              </div>
            </section>

            <section className="study-quick-actions-panel">
              <div className="study-section-head study-section-head--compact">
                <div>
                  <h2>快捷入口</h2>
                  <p>不改待办逻辑，只把常用路径收成一排。</p>
                </div>
              </div>
              <div className="study-quick-actions">
                <QuickActionButton
                  label="背新词"
                  value={focusTask?.kind === 'add-book'
                    ? '先选词书'
                    : focusBookCard
                      ? (focusBookCard.isComplete ? '主线已清空' : `剩余 ${focusBookCard.remainingWords} 词`)
                      : '先选词书'}
                  onClick={() => runDailyPlanAction(focusTask?.action)}
                />
                <QuickActionButton
                  label="去复习"
                  value={reviewTask?.badge ?? '同步中'}
                  onClick={() => runDailyPlanAction(reviewTask?.action)}
                />
                <QuickActionButton
                  label="清错词"
                  value={errorTask?.badge ?? '同步中'}
                  onClick={() => runDailyPlanAction(errorTask?.action)}
                />
                <QuickActionButton
                  label="练弱项"
                  value={weakestModeLabel}
                  onClick={startWeakModePractice}
                />
              </div>
            </section>

            <section className="study-guide-panel">
              <div className="study-section-head">
                <div>
                  <h2>你的词书</h2>
                  <p>词书区直接放回首页上方，方便你马上进入今天的内容。</p>
                </div>
                <button
                  type="button"
                  className="study-section-link"
                  onClick={() => navigate('/books')}
                >
                  管理词书
                </button>
              </div>

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
