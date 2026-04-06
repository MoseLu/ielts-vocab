import { ConfusableMatchBoard } from './confusable/ConfusableMatchBoard'
import { ConfusableMatchHeader } from './confusable/ConfusableMatchHeader'
import {
  ConfusableMatchCompletedState,
  ConfusableMatchErrorState,
  ConfusableMatchLoadingState,
  ConfusableMatchWarningOverlay,
} from './confusable/ConfusableMatchStatus'
import ConfusableCustomGroupsModal from './ConfusableCustomGroupsModal'
import WordListPanel from './WordListPanel'
import { useConfusableMatchPage } from '../../composables/practice/confusable/useConfusableMatchPage'

export default function ConfusableMatchPage() {
  const {
    bookId,
    chapterId,
    supportsCustomGroups,
    loading,
    error,
    isCompleted,
    completedGroup,
    currentChapterTitle,
    correctCount,
    wrongCount,
    currentChapter,
    bookChapters,
    showWordList,
    showCustomModal,
    boardGroups,
    queuedGroups,
    selectedCard,
    activeLine,
    errorCardIds,
    successCardIds,
    answeredGroupCount,
    totalGroups,
    completedBoardGroup,
    errorComparison,
    groupBoardRefs,
    cardRefs,
    warningVisible,
    warningText,
    vocabulary,
    wordListQueue,
    wordListCurrentIndex,
    wordListStatuses,
    setShowWordList,
    setShowCustomModal,
    handleReplay,
    handleCardClick,
    handleCustomCreated,
    handleCustomUpdated,
    buildChapterPath,
    navigatePath,
    navigateToBooks,
    navigateToPlan,
  } = useConfusableMatchPage()

  if (loading) {
    return <ConfusableMatchLoadingState />
  }

  if (error || !bookId) {
    return <ConfusableMatchErrorState error={error ?? '缺少词书参数'} onBack={navigateToBooks} />
  }

  if (isCompleted && !completedGroup) {
    return (
      <ConfusableMatchCompletedState
        chapterTitle={currentChapterTitle}
        correctCount={correctCount}
        wrongCount={wrongCount}
        onReplay={handleReplay}
        onBack={navigateToBooks}
      />
    )
  }

  return (
    <div className="practice-session-layout confusable-shell">
      <div className="confusable-stage">
        <ConfusableMatchHeader
          chapterId={chapterId}
          currentChapterTitle={currentChapterTitle}
          bookChapters={bookChapters}
          canEditCurrentChapter={Boolean(currentChapter?.is_custom)}
          showWordList={showWordList}
          onEditCurrentChapter={() => setShowCustomModal(true)}
          onWordListToggle={() => setShowWordList(value => !value)}
          onExitHome={navigateToPlan}
          onNavigate={navigatePath}
          buildChapterPath={buildChapterPath}
        />
        <ConfusableMatchBoard
          boardGroups={boardGroups}
          queuedGroups={queuedGroups}
          selectedCard={selectedCard}
          activeLine={activeLine}
          errorCardIds={errorCardIds}
          successCardIds={successCardIds}
          answeredGroupCount={answeredGroupCount}
          totalGroups={totalGroups}
          completedGroup={completedBoardGroup}
          errorComparison={errorComparison}
          groupBoardRefs={groupBoardRefs}
          cardRefs={cardRefs}
          onCardClick={handleCardClick}
        />
      </div>
      {warningVisible && <ConfusableMatchWarningOverlay warningText={warningText} />}
      {showWordList && (
        <WordListPanel
          show={showWordList}
          vocabulary={vocabulary}
          queue={wordListQueue}
          queueIndex={wordListCurrentIndex}
          wordStatuses={wordListStatuses}
          onClose={() => setShowWordList(false)}
        />
      )}
      {supportsCustomGroups && (
        <ConfusableCustomGroupsModal
          isOpen={showCustomModal}
          onClose={() => setShowCustomModal(false)}
          editChapter={currentChapter?.is_custom ? currentChapter : null}
          initialWords={currentChapter?.is_custom ? vocabulary.map(word => word.word) : undefined}
          onCreated={handleCustomCreated}
          onUpdated={handleCustomUpdated}
        />
      )}
    </div>
  )
}
