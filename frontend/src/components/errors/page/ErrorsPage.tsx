import {
  type WrongWordDimension,
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  WRONG_WORD_DIMENSION_TITLES,
  WRONG_WORD_SCOPE_LABELS,
} from '../../../features/vocabulary/wrongWordsStore'
import type { WrongWordSearchMode } from '../../../features/vocabulary/wrongWordsFilters'
import { Page, PageContent, PageHeader } from '../../layout'
import { EmptyState, PageSkeleton, SegmentedControl, UnderlineTabs } from '../../ui'
import { useErrorsPage, type WrongCountRange } from '../../../composables/errors/page/useErrorsPage'
import { ErrorsFAQCard } from './ErrorsFAQCard'
import { ErrorsCustomBookExportModal } from './ErrorsCustomBookExportModal'
import { ErrorsDatePicker } from './ErrorsDatePicker'
import { ErrorsFilterSelect } from './ErrorsFilterSelect'
import { ErrorsSearchWordItem } from './ErrorsSearchWordItem'
import { ErrorsWordItem } from './ErrorsWordItem'
import { downloadWrongWordsCsvExport } from './errorsWordExport'

const WRONG_COUNT_RANGE_OPTIONS: Array<{ value: WrongCountRange; label: string }> = [
  { value: 'all', label: '全部' },
  { value: '0-5', label: '0~5 次' },
  { value: '6-10', label: '6~10 次' },
  { value: '11-20', label: '11~20 次' },
  { value: '20+', label: '20 次以上' },
]

const SEARCH_MODE_OPTIONS: Array<{ value: WrongWordSearchMode; label: string }> = [
  { value: 'prefix', label: '词头' },
  { value: 'contains', label: '词中' },
  { value: 'suffix', label: '词尾' },
]

export default function ErrorsPage() {
  const {
    activeTab,
    scope,
    dimFilter,
    startDate,
    endDate,
    wrongCountRange,
    searchText,
    searchMode,
    appliedSearch,
    words,
    historyWords,
    pendingWords,
    scopeWords,
    dimCounts,
    filteredWords,
    selectedWordKeySet,
    selectedWordCount,
    actionSelectedWords,
    actionSelectedWordCount,
    allFilteredSelected,
    allPaginatedSelected,
    hasActiveFilters,
    canResetFilters,
    canApplySearchMode,
    loading,
    searchLoading,
    page,
    totalPages,
    pageStartIndex,
    pageEndIndex,
    paginatedWords,
    setActiveTab,
    setScope,
    setDimFilter,
    setStartDate,
    setEndDate,
    setWrongCountRange,
    setSearchText,
    setPage,
    applySearch,
    applySearchMode,
    applyTodayDateRange,
    applyRecentDaysDateRange,
    toggleWordSelection,
    selectFilteredWords,
    selectPaginatedWords,
    clearSelectedWords,
    resetFilters,
    startSelectedPractice,
    customBookExport,
    goToPlan,
  } = useErrorsPage()
  const isSearchMode = Boolean(appliedSearch)
  const searchStatusLabel = !isSearchMode
    ? ''
    : searchMode === 'prefix'
      ? `词头匹配“${appliedSearch}”`
      : searchMode === 'contains'
        ? `词中匹配“${appliedSearch}”`
      : searchMode === 'suffix'
        ? `词尾匹配“${appliedSearch}”`
        : `搜索“${appliedSearch}”`
  const dimFilterOptions: Array<{
    value: 'all' | WrongWordDimension
    label: string
    disabled?: boolean
    title?: string
  }> = [
    { value: 'all', label: `全部模式（${scopeWords.length}）` },
    ...WRONG_WORD_DIMENSIONS.map(dimension => {
      const count = dimCounts[dimension]
      return {
        value: dimension,
        label: `${WRONG_WORD_DIMENSION_LABELS[dimension]}（${count}）`,
        disabled: count === 0,
        title: WRONG_WORD_DIMENSION_TITLES[dimension],
      }
    }),
  ]
  const menuActionLabel = (label: string, inMenu: boolean) => (inMenu ? `更多操作：${label}` : undefined)
  const renderSecondaryActionButtons = (inMenu = false) => (
    <>
      <button
        className="errors-clear-btn"
        aria-label={menuActionLabel('全选结果', inMenu)}
        disabled={filteredWords.length === 0 || allFilteredSelected}
        onClick={selectFilteredWords}
      >
        全选结果
      </button>
      <button
        className="errors-clear-btn"
        aria-label={menuActionLabel('全选当前页', inMenu)}
        disabled={paginatedWords.length === 0 || allPaginatedSelected}
        onClick={selectPaginatedWords}
      >
        全选当前页
      </button>
      <button
        className="errors-clear-btn"
        aria-label={menuActionLabel('导出已勾选 CSV', inMenu)}
        disabled={actionSelectedWords.length === 0}
        onClick={() => downloadWrongWordsCsvExport(actionSelectedWords)}
      >
        导出已勾选 CSV
      </button>
      <button
        className="errors-clear-btn"
        aria-label={menuActionLabel('保存到自定义词书', inMenu)}
        disabled={actionSelectedWordCount === 0}
        onClick={customBookExport.open}
      >
        保存到自定义词书
      </button>
      <button
        className="errors-clear-btn"
        aria-label={menuActionLabel('清空选择', inMenu)}
        disabled={selectedWordCount === 0}
        onClick={clearSelectedWords}
      >
        清空选择
      </button>
    </>
  )
  const toolbar = (
    <div className="errors-toolbar">
      <UnderlineTabs
        className="errors-tabs"
        ariaLabel="错词本导航"
        value={activeTab}
        onChange={setActiveTab}
        options={[
          { value: 'words', label: '错词', badge: words.length > 0 ? words.length : undefined },
          { value: 'real', label: '真题' },
        ]}
      />

      {activeTab === 'words' && scopeWords.length > 0 && (
        <div className="errors-actions">
          <button
            className="errors-practice-btn"
            disabled={actionSelectedWordCount === 0}
            onClick={startSelectedPractice}
          >
            开始复习（{actionSelectedWordCount}词）
          </button>
          <div className="errors-secondary-actions">{renderSecondaryActionButtons()}</div>
          <details className="errors-actions-menu">
            <summary className="errors-actions-menu-trigger">更多操作</summary>
            <div className="errors-actions-menu-list">
              {renderSecondaryActionButtons(true)}
            </div>
          </details>
        </div>
      )}
    </div>
  )

  return (
    <Page className="errors-page">
      <PageHeader className="errors-page-toolbar">{toolbar}</PageHeader>
      <PageContent className="errors-page-body">
        {activeTab === 'real' ? (
          <EmptyState
            page
            className="errors-empty"
            icon={(
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M9 9h6M9 13h6M9 17h4" />
              </svg>
            )}
            title="真题错题功能"
            description="敬请期待"
          />
        ) : loading && words.length === 0 ? (
          <PageSkeleton variant="books" itemCount={4} />
        ) : words.length === 0 ? (
          <EmptyState
            page
            className="errors-empty"
            icon={(
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="9" y1="13" x2="15" y2="13" />
                <line x1="9" y1="17" x2="15" y2="17" />
              </svg>
            )}
            title="暂无错词"
            description='答错后的单词会进入累计错词；相关问题类型没清掉前，也会继续留在待清错词里。'
            action={<button className="errors-go-practice" onClick={goToPlan}>去练习 →</button>}
          />
        ) : (
          <div className="errors-content-scroll">
            {!isSearchMode && <ErrorsFAQCard />}

            <div className="errors-scope-row">
              <SegmentedControl
                className="errors-dim-filter"
                ariaLabel="错词集合筛选"
                value={scope}
                onChange={value => setScope(value as 'pending' | 'history')}
                options={[
                  { value: 'pending', label: WRONG_WORD_SCOPE_LABELS.pending, badge: pendingWords.length > 0 ? pendingWords.length : undefined },
                  { value: 'history', label: WRONG_WORD_SCOPE_LABELS.history, badge: historyWords.length > 0 ? historyWords.length : undefined },
                ]}
              />

              {filteredWords.length > 0 && (
                <div className="errors-scope-tools">
                  <span className="errors-summary-pill">
                    {pageStartIndex}-{pageEndIndex}/{filteredWords.length}
                  </span>
                  {totalPages > 1 && (
                    <div className="errors-inline-pagination" role="navigation" aria-label="错词分页">
                      <button
                        type="button"
                        className="errors-clear-btn"
                        disabled={page <= 1}
                        onClick={() => setPage(page - 1)}
                      >
                        上一页
                      </button>
                      <span className="errors-inline-pagination-status">
                        {page}/{totalPages}
                      </span>
                      <button
                        type="button"
                        className="errors-clear-btn"
                        disabled={page >= totalPages}
                        onClick={() => setPage(page + 1)}
                      >
                        下一页
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="errors-filter-panel">
              <div className="errors-filter-panel-main">
                <div className="errors-filter-field errors-mode-filter-field">
                  <span className="errors-filter-label">问题类型</span>
                  <ErrorsFilterSelect
                    ariaLabel="错词模式筛选"
                    value={dimFilter}
                    options={dimFilterOptions}
                    className="errors-mode-filter-select"
                    onChange={setDimFilter}
                  />
                </div>

                <div className="errors-filter-field">
                  <span className="errors-filter-label">起始日期</span>
                  <ErrorsDatePicker
                    ariaLabel="起始日期"
                    value={startDate}
                    onChange={setStartDate}
                  />
                </div>

                <div className="errors-filter-field">
                  <span className="errors-filter-label">结束日期</span>
                  <ErrorsDatePicker
                    ariaLabel="结束日期"
                    value={endDate}
                    onChange={setEndDate}
                  />
                </div>

                <div className="errors-filter-field errors-filter-field--compact">
                  <span className="errors-filter-label">{scope === 'pending' ? '待清错次' : '累计错次'}</span>
                  <ErrorsFilterSelect
                    ariaLabel="错次区间"
                    value={wrongCountRange}
                    options={WRONG_COUNT_RANGE_OPTIONS}
                    onChange={setWrongCountRange}
                  />
                </div>
              </div>

              <div className="errors-filter-panel-actions">
                <div className="errors-filter-shortcuts" role="group" aria-label="日期快捷筛选">
                  <button
                    type="button"
                    className="errors-filter-chip"
                    onClick={applyTodayDateRange}
                  >
                    只看今天新错词
                  </button>
                  <button
                    type="button"
                    className="errors-filter-chip"
                    onClick={() => applyRecentDaysDateRange(7)}
                  >
                    最近 7 天
                  </button>
                </div>

                <button
                  type="button"
                  className="errors-filter-chip errors-filter-reset"
                  disabled={!canResetFilters}
                  onClick={resetFilters}
                >
                  重置筛选
                </button>
              </div>
            </div>

            <div className="errors-dim-filter-row">
              <div className="errors-dim-filter-shell">
                <div className="errors-dim-filter-tools">
                  <form
                    className="errors-search-form"
                    onSubmit={event => {
                      event.preventDefault()
                      void applySearch()
                    }}
                  >
                    <div className="errors-search-input-wrap">
                      <input
                        aria-label="搜索错词"
                        className="errors-filter-input errors-search-input"
                        type="search"
                        value={searchText}
                        placeholder="搜索单词"
                        onChange={event => setSearchText(event.target.value)}
                      />
                      <button
                        type="submit"
                        className="errors-search-submit"
                        aria-label="执行搜索"
                        disabled={searchLoading}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                          <circle cx="11" cy="11" r="6.5" />
                          <path d="M16 16l4.5 4.5" strokeLinecap="round" />
                        </svg>
                      </button>
                    </div>
                  </form>

                  <div className="errors-search-mode-group" role="group" aria-label="搜索匹配方式">
                    {SEARCH_MODE_OPTIONS.map(option => {
                      const active = searchMode === option.value

                      return (
                        <button
                          key={option.value}
                          type="button"
                          className={`errors-search-mode-option${active ? ' is-active' : ''}${!canApplySearchMode ? ' is-disabled' : ''}`}
                          aria-pressed={active}
                          disabled={!canApplySearchMode}
                          onClick={() => applySearchMode(option.value)}
                        >
                          <span className="errors-search-mode-marker" aria-hidden="true" />
                          <span className="errors-search-mode-text">{option.label}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>

            {filteredWords.length === 0 ? (
              <EmptyState
                page
                className="errors-empty"
                title={hasActiveFilters ? '暂无匹配错词' : `${WRONG_WORD_SCOPE_LABELS[scope]}为空`}
                description={hasActiveFilters ? '调整搜索词、日期、错次或问题类型后再试' : (scope === 'pending' ? '当前没有待继续攻克的错词' : '继续练习，累计错词会自动增加')}
              />
            ) : (
              <>
                {isSearchMode && (
                  <div className="errors-search-status">
                    {searchStatusLabel} · {filteredWords.length} 个结果
                  </div>
                )}

                <div className={isSearchMode ? 'errors-search-results' : 'errors-list'}>
                  {paginatedWords.map(word => (
                    isSearchMode ? (
                      <ErrorsSearchWordItem
                        key={word.word}
                        word={word}
                        selectedWordKeySet={selectedWordKeySet}
                        toggleWordSelection={toggleWordSelection}
                      />
                    ) : (
                      <ErrorsWordItem
                        key={word.word}
                        word={word}
                        scope={scope}
                        dimFilter={dimFilter}
                        selectedWordKeySet={selectedWordKeySet}
                        toggleWordSelection={toggleWordSelection}
                      />
                    )
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </PageContent>
      <ErrorsCustomBookExportModal exportState={customBookExport} />
    </Page>
  )
}
