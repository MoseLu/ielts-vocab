import {
  type WrongWordDimension,
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  WRONG_WORD_DIMENSION_TITLES,
  WRONG_WORD_PENDING_REVIEW_TARGET,
  WRONG_WORD_SCOPE_LABELS,
  getWrongWordActiveCount,
  getWrongWordDimensionHistoryWrong,
  isWrongWordPendingInDimension,
} from '../../../features/vocabulary/wrongWordsStore'
import { formatWrongWordOccurrenceDate } from '../../../features/vocabulary/wrongWordsFilters'
import {
  describeWrongWordDimension,
  normalizeWrongWordKey,
} from './errorsPageHelpers'
import { Page, PageContent, PageHeader } from '../../layout'
import { EmptyState, SegmentedControl, UnderlineTabs } from '../../ui'
import { useErrorsPage, type WrongCountRange } from '../../../composables/errors/page/useErrorsPage'

const WRONG_COUNT_RANGE_OPTIONS: Array<{ value: WrongCountRange; label: string }> = [
  { value: 'all', label: '全部' },
  { value: '0-5', label: '0~5 次' },
  { value: '6-10', label: '6~10 次' },
  { value: '11-20', label: '11~20 次' },
  { value: '20+', label: '20 次以上' },
]

export default function ErrorsPage() {
  const {
    activeTab,
    scope,
    dimFilter,
    startDate,
    endDate,
    wrongCountRange,
    words,
    historyWords,
    pendingWords,
    scopeWords,
    dimStats,
    dimCounts,
    filteredWords,
    selectedWordKeySet,
    selectedWordCount,
    selectedFilteredWordCount,
    selectedOutsideFilterCount,
    allFilteredSelected,
    hasActiveFilters,
    setActiveTab,
    setScope,
    setDimFilter,
    setStartDate,
    setEndDate,
    setWrongCountRange,
    toggleWordSelection,
    selectFilteredWords,
    clearSelectedWords,
    resetFilters,
    startSelectedPractice,
    goToPlan,
  } = useErrorsPage()

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
            disabled={selectedWordCount === 0}
            onClick={startSelectedPractice}
          >
            复习已选（{selectedWordCount}词）
          </button>
          <button
            className="errors-clear-btn"
            disabled={filteredWords.length === 0 || allFilteredSelected}
            onClick={selectFilteredWords}
          >
            勾选当前筛选
          </button>
          <button
            className="errors-clear-btn"
            disabled={selectedWordCount === 0}
            onClick={clearSelectedWords}
          >
            清空勾选
          </button>
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
            <div className="errors-review-rule">
              一个词只要答错过，就会进入“累计错词”。如果某一类问题还没连续答对 {WRONG_WORD_PENDING_REVIEW_TARGET} 次，它也会继续留在“待清错词”里，方便你按问题类型集中清理。
            </div>

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

            <div className="errors-filter-panel">
              <label className="errors-filter-field">
                <span className="errors-filter-label">起始日期</span>
                <input
                  aria-label="起始日期"
                  className="errors-filter-input"
                  type="date"
                  value={startDate}
                  onChange={event => setStartDate(event.target.value)}
                />
              </label>

              <label className="errors-filter-field">
                <span className="errors-filter-label">结束日期</span>
                <input
                  aria-label="结束日期"
                  className="errors-filter-input"
                  type="date"
                  value={endDate}
                  onChange={event => setEndDate(event.target.value)}
                />
              </label>

              <label className="errors-filter-field errors-filter-field--compact">
                <span className="errors-filter-label">{scope === 'pending' ? '待清错次' : '累计错次'}</span>
                <select
                  aria-label="错次区间"
                  className="errors-filter-select"
                  value={wrongCountRange}
                  onChange={event => setWrongCountRange(event.target.value as WrongCountRange)}
                >
                  {WRONG_COUNT_RANGE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="button"
                className="errors-filter-reset"
                disabled={!hasActiveFilters}
                onClick={resetFilters}
              >
                重置筛选
              </button>
            </div>

            {hasActiveFilters && (
              <div className="errors-filter-summary">
                当前筛选命中 {filteredWords.length} 个{scope === 'pending' ? '待清错词' : '累计错词'}
              </div>
            )}

            <div className="errors-selection-summary">
              错词不会被删除；勾选后只加入复习。已勾选 {selectedWordCount} 词，当前筛选中 {selectedFilteredWordCount} 词
              {selectedOutsideFilterCount > 0 ? `，另外 ${selectedOutsideFilterCount} 词来自其他筛选` : ''}
              。
            </div>

            {scopeWords.length > 0 && (
              <div className="errors-dim-summary" role="note">
                一个词可能同时属于多类问题，所以这里的标签数量会重复计算。当前 {scopeWords.length} 个{WRONG_WORD_SCOPE_LABELS[scope]}对应了 {dimStats.hitCount} 个问题标签
                {dimStats.overlappingWordCount > 0
                  ? `，其中 ${dimStats.overlappingWordCount} 个词同时落在多个问题类型里`
                  : ''}
                ，这些数字不是互斥拆分。
              </div>
            )}

            <div className="errors-dim-filter-row">
              <SegmentedControl
                className="errors-dim-filter"
                ariaLabel="错词维度筛选"
                value={dimFilter}
                onChange={value => setDimFilter(value as 'all' | WrongWordDimension)}
                options={[
                  { value: 'all', label: '全部', badge: scopeWords.length },
                  ...WRONG_WORD_DIMENSIONS.map(dimension => ({
                    value: dimension,
                    label: WRONG_WORD_DIMENSION_LABELS[dimension],
                    badge: dimCounts[dimension] > 0 ? dimCounts[dimension] : undefined,
                    disabled: dimCounts[dimension] === 0,
                    title: WRONG_WORD_DIMENSION_TITLES[dimension],
                  })),
                ]}
              />
              <div className="errors-select-heading">加入复习</div>
            </div>

            {filteredWords.length === 0 ? (
              <EmptyState
                page
                className="errors-empty"
                title={hasActiveFilters ? '当前筛选暂无错词' : `${WRONG_WORD_SCOPE_LABELS[scope]}为空`}
                description={hasActiveFilters ? '调整日期、错次或问题类型后再试' : (scope === 'pending' ? '当前没有待继续攻克的错词' : '继续练习，累计错词会自动增加')}
              />
            ) : (
              <div className="errors-list">
                {filteredWords.map(word => {
                  const collectedOn = formatWrongWordOccurrenceDate(word)
                  const historyDims = WRONG_WORD_DIMENSIONS.filter(dimension => getWrongWordDimensionHistoryWrong(word, dimension) > 0)
                  const pendingDimensionCount = WRONG_WORD_DIMENSIONS.filter(dimension => isWrongWordPendingInDimension(word, dimension)).length
                  const wordKey = normalizeWrongWordKey(word.word)
                  const checked = selectedWordKeySet.has(wordKey)

                  return (
                    <div key={word.word} className="errors-item">
                      <div className="errors-item-main">
                        <div className="errors-item-word-row">
                          <span className="errors-item-word">{word.word}</span>
                          <span className="errors-item-total-count">
                            {scope === 'pending'
                              ? `待清错次×${getWrongWordActiveCount(word, 'pending')}`
                              : `累计错次×${getWrongWordActiveCount(word, 'history')}`}
                          </span>
                        </div>
                        {(word.phonetic || collectedOn) && (
                          <div className="errors-item-meta">
                            {word.phonetic && <div className="errors-item-phonetic">{word.phonetic}</div>}
                            {collectedOn && <span className="errors-item-date">收录于 {collectedOn}</span>}
                          </div>
                        )}
                        <div className="errors-item-definition">
                          {word.pos && <span className="word-pos-tag">{word.pos}</span>}
                          {word.definition}
                        </div>
                        <div className="errors-item-dims">
                          <span className="errors-dim-badge errors-dim-progress">
                            出现过 {historyDims.length} 类问题
                          </span>
                          <span className={`errors-dim-badge ${pendingDimensionCount > 0 ? 'errors-dim-progress' : 'errors-dim-ok'}`}>
                            待清 {pendingDimensionCount} 类问题
                          </span>
                          {historyDims.map(dimension => {
                            const dimensionCopy = describeWrongWordDimension(word, dimension)
                            const highlighted = dimFilter === dimension

                            return (
                              <span
                                key={dimension}
                                title={dimensionCopy.title}
                                className={`errors-dim-badge ${dimensionCopy.pending ? 'errors-dim-progress' : 'errors-dim-ok'}${highlighted ? ' errors-dim-highlight' : ''}`}
                              >
                                {dimensionCopy.label}
                                <span className="errors-dim-wrong"> {dimensionCopy.detail}</span>
                                <span className="errors-dim-correct"> {dimensionCopy.status}</span>
                              </span>
                            )
                          })}
                        </div>
                      </div>
                      <label className={`errors-item-select${checked ? ' errors-item-select--checked' : ''}`}>
                        <input
                          className="errors-item-checkbox"
                          type="checkbox"
                          aria-label={`选择 ${word.word}`}
                          checked={checked}
                          onChange={() => toggleWordSelection(word.word)}
                        />
                      </label>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </PageContent>
    </Page>
  )
}
