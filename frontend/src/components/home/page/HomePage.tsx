import ChapterModal from '../../books/dialogs/ChapterModal'
import PlanModal from '../../books/dialogs/PlanModal'
import { MyBookCard, StudyGuidancePanel, TodoTaskRow } from './HomePageSections'
import { PageReady, PageSkeleton } from '../../ui'
import { useHomePage } from '../../../composables/home/page/useHomePage'

export default function HomePage() {
  const {
    selectedBook,
    showChapterModal,
    selectedBookProgress,
    containerRef,
    skeletonCount,
    isInitialLoading,
    bookCards,
    taskList,
    studyGuidance,
    handleSelectBook,
    handleRemoveBook,
    handleSelectChapter,
    handleStartStudy,
    runDailyPlanAction,
    navigateToBooks,
    closeChapterModal,
    closePlanModal,
  } = useHomePage()

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
                  onClick={navigateToBooks}
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
          progress={selectedBookProgress ?? null}
          onClose={closeChapterModal}
          onSelectChapter={handleSelectChapter}
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
    </div>
  )
}
