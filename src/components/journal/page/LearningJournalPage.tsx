import { useLearningJournalPage } from '../../../composables/journal/page/useLearningJournalPage'
import {
  formatDateTime,
  toPlainTextSnippet,
} from '../../../composables/journal/page/journalPageUtils'
import DailySummaryDocument from '../documents/DailySummaryDocument'
import QaHistoryDocument from '../documents/QaHistoryDocument'
import JournalWorkspace from '../layout/JournalWorkspace'
import { JournalNotesActions, JournalSummaryActions } from './JournalPageActions'
import { PageSkeleton } from '../../ui'
import { Page } from '../../layout'

export default function LearningJournalPage() {
  const {
    tab,
    startDate,
    endDate,
    notes,
    notesLoading,
    notesError,
    notesTotal,
    memoryTopics,
    cursorStack,
    hasMore,
    exporting,
    selectedSummary,
    selectedNote,
    summaryLoading,
    summaryError,
    summaryProfile,
    summaryProfileLoading,
    generatingDate,
    summaryTargetDate,
    summaryProgress,
    isInitialSummaryLoading,
    isInitialNotesLoading,
    exportLabel,
    generateLoadingText,
    setStartDate,
    setEndDate,
    handleTabChange,
    resetNoteDateFilters,
    generateSummary,
    exportSummaries,
    exportNotes,
    setSelectedNoteId,
    goToPreviousNotesPage,
    goToNextNotesPage,
  } = useLearningJournalPage()

  if (isInitialSummaryLoading || isInitialNotesLoading) {
    return (
      <Page className="journal-page">
        <PageSkeleton
          variant="journal"
          itemCount={4}
          className="journal-page-skeleton"
        />
      </Page>
    )
  }

  return (
    <JournalWorkspace
      activeTab={tab}
      onTabChange={handleTabChange}
      actions={tab === 'notes' ? (
        <JournalNotesActions
          startDate={startDate}
          endDate={endDate}
          exporting={exporting}
          exportLabel={exportLabel}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onResetDates={resetNoteDateFilters}
          onExport={exportNotes}
        />
      ) : (
        <JournalSummaryActions
          selectedSummaryDate={selectedSummary?.date ?? null}
          summaryTargetDate={summaryTargetDate}
          generatingDate={generatingDate}
          exporting={exporting}
          exportLabel={exportLabel}
          generateLoadingText={generateLoadingText}
          summaryProgress={summaryProgress}
          onGenerate={generateSummary}
          onExport={exportSummaries}
        />
      )}
    >
      {tab === 'summaries' ? (
        <DailySummaryDocument
          summary={selectedSummary}
          learnerProfile={summaryProfile}
          learnerProfileLoading={summaryProfileLoading}
          summaryLoading={summaryLoading}
          summaryError={summaryError}
          summaryProgress={summaryProgress}
          formatDateTime={formatDateTime}
        />
      ) : (
        <QaHistoryDocument
          notes={notes}
          memoryTopics={memoryTopics}
          notesLoading={notesLoading}
          notesError={notesError}
          notesTotal={notesTotal}
          selectedNote={selectedNote}
          cursorStack={cursorStack}
          hasMore={hasMore}
          onSelectNote={setSelectedNoteId}
          onPreviousPage={goToPreviousNotesPage}
          onNextPage={goToNextNotesPage}
          formatDateTime={formatDateTime}
          toPlainTextSnippet={toPlainTextSnippet}
        />
      )}
    </JournalWorkspace>
  )
}
