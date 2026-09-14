import { useLearningJournalPage } from '../../../composables/journal/page/useLearningJournalPage'
import {
  formatDateTime,
} from '../../../composables/journal/page/journalPageUtils'
import TodayNotesDocument from '../documents/TodayNotesDocument'
import HistoryNotesDocument from '../documents/HistoryNotesDocument'
import JournalWorkspace from '../layout/JournalWorkspace'
import { JournalNotesActions, TodayNotesActions } from './JournalPageActions'
import { PageSkeleton } from '../../ui'
import { Page } from '../../layout'

export default function LearningJournalPage() {
  const {
    tab,
    startDate,
    endDate,
    todayEntry,
    editMode,
    polishing,
    polishedPreview,
    historyEntries,
    historyLoading,
    historyError,
    historyHasMore,
    selectedEntry,
    exporting,
    exportLabel,
    isInitialTodayLoading,
    setStartDate,
    setEndDate,
    setEditMode,
    handleTabChange,
    resetDateFilters,
    saveJournalEntry,
    setTodayDraftContent,
    polishContent,
    acceptPolish,
    rejectPolish,
    loadMoreHistory,
    selectEntry,
    backToList,
    exportNotes,
  } = useLearningJournalPage()

  if (isInitialTodayLoading) {
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
      actions={tab === 'history' ? (
        <JournalNotesActions
          startDate={startDate}
          endDate={endDate}
          exporting={exporting}
          exportLabel={exportLabel}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onResetDates={resetDateFilters}
          onExport={exportNotes}
        />
      ) : (
        <TodayNotesActions
          editMode={editMode}
          polishing={polishing}
          onToggleEdit={() => setEditMode(!editMode)}
          onPolish={polishContent}
        />
      )}
    >
      {tab === 'today' ? (
        <TodayNotesDocument
          entry={todayEntry}
          editMode={editMode}
          polishing={polishing}
          polishedPreview={polishedPreview}
          onSave={saveJournalEntry}
          onDraftChange={setTodayDraftContent}
          onPolish={polishContent}
          onAcceptPolish={acceptPolish}
          onRejectPolish={rejectPolish}
          formatDateTime={formatDateTime}
        />
      ) : (
        <HistoryNotesDocument
          entries={historyEntries}
          loading={historyLoading}
          error={historyError}
          hasMore={historyHasMore}
          selectedEntry={selectedEntry}
          onSelectEntry={selectEntry}
          onLoadMore={loadMoreHistory}
          onBack={backToList}
          formatDateTime={formatDateTime}
        />
      )}
    </JournalWorkspace>
  )
}
