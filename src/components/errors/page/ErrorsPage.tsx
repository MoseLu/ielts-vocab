import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords } from '../../../features/vocabulary/hooks'
import {
  buildWrongWordsPracticeQuery,
  filterWrongWords,
  formatWrongWordOccurrenceDate,
} from '../../../features/vocabulary/wrongWordsFilters'
import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  WRONG_WORD_PENDING_REVIEW_TARGET,
  getWrongWordActiveCount,
  getWrongWordDimensionHistoryWrong,
  getWrongWordDimensionProgress,
  hasWrongWordHistory,
  hasWrongWordPending,
  isWrongWordPendingInDimension,
} from '../../../features/vocabulary/wrongWordsStore'
import { Page, PageContent, PageHeader } from '../../layout'
import { EmptyState, SegmentedControl, UnderlineTabs } from '../../ui'

type ActiveTab = 'words' | 'real'
type DimFilter = 'all' | WrongWordDimension
type WrongCountRange = 'all' | '0-5' | '6-10' | '11-20' | '20+'

const DIM_SHORT_LABEL: Record<WrongWordDimension, string> = {
  recognition: '认识',
  meaning: '会想',
  listening: '听得到',
  dictation: '会拼写',
}

const SCOPE_LABELS: Record<WrongWordCollectionScope, string> = {
  pending: '未过错词',
  history: '历史错词',
}

const WRONG_COUNT_RANGE_OPTIONS: { value: WrongCountRange; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: '0-5', label: '0~5 次' },
  { value: '6-10', label: '6~10 次' },
  { value: '11-20', label: '11~20 次' },
  { value: '20+', label: '20 次以上' },
]

function getWrongCountBounds(range: WrongCountRange): { minWrongCount?: number; maxWrongCount?: number } {
  switch (range) {
    case '0-5':
      return { maxWrongCount: 5 }
    case '6-10':
      return { minWrongCount: 6, maxWrongCount: 10 }
    case '11-20':
      return { minWrongCount: 11, maxWrongCount: 20 }
    case '20+':
      return { minWrongCount: 21 }
    default:
      return {}
  }
}

function requestPracticeMode(dimFilter: DimFilter) {
  const requestedMode = dimFilter === 'recognition'
    ? 'quickmemory'
    : dimFilter === 'listening'
      ? 'listening'
      : dimFilter === 'dictation'
        ? 'dictation'
        : dimFilter === 'meaning'
          ? 'meaning'
          : null

  if (!requestedMode) return
  window.dispatchEvent(new CustomEvent('practice-mode-request', {
    detail: { mode: requestedMode },
  }))
}

export default function ErrorsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('words')
  const [scope, setScope] = useState<WrongWordCollectionScope>('pending')
  const [dimFilter, setDimFilter] = useState<DimFilter>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [wrongCountRange, setWrongCountRange] = useState<WrongCountRange>('all')
  const { words, removeWord, clearAll } = useWrongWords()
  const { minWrongCount, maxWrongCount } = getWrongCountBounds(wrongCountRange)

  const historyWords = useMemo(() => words.filter(word => hasWrongWordHistory(word)), [words])
  const pendingWords = useMemo(() => words.filter(word => hasWrongWordPending(word)), [words])
  const scopeWords = scope === 'pending' ? pendingWords : historyWords

  const dimCounts = useMemo(() => {
    return WRONG_WORD_DIMENSIONS.reduce((result, dimension) => {
      result[dimension] = scopeWords.filter(word => {
        if (scope === 'history') {
          return getWrongWordDimensionHistoryWrong(word, dimension) > 0
        }
        return isWrongWordPendingInDimension(word, dimension)
      }).length
      return result
    }, {} as Record<WrongWordDimension, number>)
  }, [scope, scopeWords])

  const filteredWords = useMemo(() => {
    return [...filterWrongWords(words, {
      scope,
      dimFilter,
      startDate,
      endDate,
      minWrongCount,
      maxWrongCount,
    })].sort((a, b) => {
      if (dimFilter !== 'all') {
        const aDimCount = scope === 'history'
          ? getWrongWordDimensionHistoryWrong(a, dimFilter)
          : (isWrongWordPendingInDimension(a, dimFilter) ? getWrongWordDimensionHistoryWrong(a, dimFilter) : 0)
        const bDimCount = scope === 'history'
          ? getWrongWordDimensionHistoryWrong(b, dimFilter)
          : (isWrongWordPendingInDimension(b, dimFilter) ? getWrongWordDimensionHistoryWrong(b, dimFilter) : 0)
        if (bDimCount !== aDimCount) return bDimCount - aDimCount
      }

      return getWrongWordActiveCount(b, scope) - getWrongWordActiveCount(a, scope)
    })
  }, [dimFilter, endDate, maxWrongCount, minWrongCount, scope, startDate, words])

  const hasActiveFilters = dimFilter !== 'all' || Boolean(startDate) || Boolean(endDate) || wrongCountRange !== 'all'
  const practiceQuery = buildWrongWordsPracticeQuery({
    scope,
    dimFilter,
    startDate,
    endDate,
    minWrongCount,
    maxWrongCount,
  })

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
            disabled={filteredWords.length === 0}
            onClick={() => {
              requestPracticeMode(dimFilter)
              navigate(practiceQuery ? `/practice?mode=errors&${practiceQuery}` : '/practice?mode=errors')
            }}
          >
            复习（{filteredWords.length}词）
          </button>
          {scope === 'pending' && pendingWords.length > 0 && (
            <button className="errors-clear-btn" onClick={clearAll}>
              清空未过
            </button>
          )}
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
            description='答错后的单词会同时进入历史错词和未过错词，后续通过才会从未过错词移出'
            action={<button className="errors-go-practice" onClick={() => navigate('/plan')}>去练习 →</button>}
          />
        ) : (
          <div className="errors-content-scroll">
            <div className="errors-review-rule">
              历史错词只增不减；未过错词会按维度定向移除。当前规则是同一维度连续答对 {WRONG_WORD_PENDING_REVIEW_TARGET} 次后，从未过错词移出，但仍保留在历史错词里。
            </div>

            <SegmentedControl
              className="errors-dim-filter"
              ariaLabel="错词集合筛选"
              value={scope}
              onChange={value => setScope(value as WrongWordCollectionScope)}
              options={[
                { value: 'pending', label: SCOPE_LABELS.pending, badge: pendingWords.length > 0 ? pendingWords.length : undefined },
                { value: 'history', label: SCOPE_LABELS.history, badge: historyWords.length > 0 ? historyWords.length : undefined },
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
                <span className="errors-filter-label">{scope === 'pending' ? '未过权重' : '历史错次'}</span>
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
                onClick={() => {
                  setDimFilter('all')
                  setStartDate('')
                  setEndDate('')
                  setWrongCountRange('all')
                }}
              >
                重置筛选
              </button>
            </div>

            {hasActiveFilters && (
              <div className="errors-filter-summary">
                当前筛选命中 {filteredWords.length} 个{scope === 'pending' ? '未过错词' : '历史错词'}
              </div>
            )}

            <SegmentedControl
              className="errors-dim-filter"
              ariaLabel="错词维度筛选"
              value={dimFilter}
              onChange={value => setDimFilter(value as DimFilter)}
              options={[
                { value: 'all', label: '全部', badge: scopeWords.length },
                ...WRONG_WORD_DIMENSIONS.map(dimension => ({
                  value: dimension,
                  label: DIM_SHORT_LABEL[dimension],
                  badge: dimCounts[dimension] > 0 ? dimCounts[dimension] : undefined,
                  disabled: dimCounts[dimension] === 0,
                })),
              ]}
            />

            {filteredWords.length === 0 ? (
              <EmptyState
                page
                className="errors-empty"
                title={hasActiveFilters ? '当前筛选暂无错词' : `${SCOPE_LABELS[scope]}为空`}
                description={hasActiveFilters ? '调整日期、错次或维度后再试' : (scope === 'pending' ? '当前没有待继续攻克的错词' : '继续练习，历史错词会自动累计')}
              />
            ) : (
              <div className="errors-list">
                {filteredWords.map(word => {
                  const collectedOn = formatWrongWordOccurrenceDate(word)
                  const historyDims = WRONG_WORD_DIMENSIONS.filter(dimension => getWrongWordDimensionHistoryWrong(word, dimension) > 0)
                  const pendingDimensionCount = WRONG_WORD_DIMENSIONS.filter(dimension => isWrongWordPendingInDimension(word, dimension)).length

                  return (
                    <div key={word.word} className="errors-item">
                      <div className="errors-item-main">
                        <div className="errors-item-word-row">
                          <span className="errors-item-word">{word.word}</span>
                          <span className="errors-item-total-count">
                            {scope === 'pending'
                              ? `未过×${getWrongWordActiveCount(word, 'pending')}`
                              : `历史×${getWrongWordActiveCount(word, 'history')}`}
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
                            历史 {historyDims.length} 维
                          </span>
                          <span className={`errors-dim-badge ${pendingDimensionCount > 0 ? 'errors-dim-progress' : 'errors-dim-ok'}`}>
                            未过 {pendingDimensionCount} 维
                          </span>
                          {historyDims.map(dimension => {
                            const historyWrong = getWrongWordDimensionHistoryWrong(word, dimension)
                            const progress = getWrongWordDimensionProgress(word, dimension)
                            const highlighted = dimFilter === dimension

                            return (
                              <span
                                key={dimension}
                                title={WRONG_WORD_DIMENSION_LABELS[dimension]}
                                className={`errors-dim-badge ${progress.pending ? 'errors-dim-progress' : 'errors-dim-ok'}${highlighted ? ' errors-dim-highlight' : ''}`}
                              >
                                {DIM_SHORT_LABEL[dimension]}
                                <span className="errors-dim-wrong"> 历史×{historyWrong}</span>
                                {progress.pending ? (
                                  <span className="errors-dim-correct"> 待过 {progress.streak}/{progress.target}</span>
                                ) : (
                                  <span className="errors-dim-correct"> 已过</span>
                                )}
                              </span>
                            )
                          })}
                        </div>
                      </div>
                      {scope === 'pending' && hasWrongWordPending(word) && (
                        <button
                          className="errors-item-remove"
                          onClick={() => removeWord(word.word)}
                          title="移出未过错词"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        </button>
                      )}
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
