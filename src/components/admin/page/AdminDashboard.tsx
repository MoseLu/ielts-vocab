import { useAdminDashboard } from '../../../composables/admin/dashboard/useAdminDashboard'
import { AdminDashboardModal } from '../dashboard/AdminDashboardModal'
import { AdminDashboardView } from '../dashboard/AdminDashboardView'

export default function AdminDashboard() {
  const {
    tab,
    overview,
    users,
    total,
    page,
    pages,
    search,
    sort,
    order,
    selectedUser,
    isFullscreen,
    detailTab,
    detailDateFrom,
    detailDateTo,
    detailMode,
    ttsBooks,
    ttsBooksLoading,
    loading,
    overviewLoading,
    error,
    setTab,
    setSearch,
    setIsFullscreen,
    setDetailTab,
    setDetailDateFrom,
    setDetailDateTo,
    setDetailMode,
    fetchUserDetail,
    handleGenerate,
    handleSearchSubmit,
    handleSearchClear,
    handleSort,
    handlePageChange,
    handleSelectUser,
    closeDetail,
    dismissError,
  } = useAdminDashboard()

  return (
    <>
      <AdminDashboardView
        tab={tab}
        overview={overview}
        overviewLoading={overviewLoading}
        users={users}
        total={total}
        page={page}
        pages={pages}
        search={search}
        sort={sort}
        order={order}
        ttsBooks={ttsBooks}
        ttsBooksLoading={ttsBooksLoading}
        loading={loading}
        error={error}
        onDismissError={dismissError}
        onTabChange={setTab}
        onSearchSubmit={handleSearchSubmit}
        onSearchClear={handleSearchClear}
        onSearchChange={setSearch}
        onSort={handleSort}
        onPageChange={handlePageChange}
        onSelectUser={handleSelectUser}
        onGenerateTtsBook={handleGenerate}
      />

      {selectedUser && (
        <AdminDashboardModal
          selectedUser={selectedUser}
          isFullscreen={isFullscreen}
          detailTab={detailTab}
          detailDateFrom={detailDateFrom}
          detailDateTo={detailDateTo}
          detailMode={detailMode}
          onClose={closeDetail}
          onToggleFullscreen={() => setIsFullscreen(flag => !flag)}
          onSetDetailTab={setDetailTab}
          onSetDetailDateFrom={setDetailDateFrom}
          onSetDetailDateTo={setDetailDateTo}
          onSetDetailMode={setDetailMode}
          onFetchUserDetail={fetchUserDetail}
        />
      )}
    </>
  )
}
