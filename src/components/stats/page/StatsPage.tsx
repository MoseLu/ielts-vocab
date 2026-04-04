import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageSkeleton } from '../../ui'
import { SegmentedControl, UnderlineTabs } from '../../ui/NavigationControls'
import { useWrongWords, useLearningStats } from '../../../features/vocabulary/hooks'
import { hasWrongWordHistory, hasWrongWordPending } from '../../../features/vocabulary/wrongWordsStore'
import type { MetricKey, RangeKey } from '../../../features/vocabulary/hooks'
import {
  StatsSectionSkeleton,
  WrongTopBlock,
  buildWrongTopItems,
  ebbinghausRateCaption,
  ebbinghausSummaryHelp,
  EbbinghausDualChart,
  fmtDuration,
  fmtPct,
  isStatsInitialLoading,
  LearnerProfileCard,
  LearningChart,
  MODE_LABELS,
  ModeBreakdownTableBody,
  ModePieChart,
  resolveEbbStages,
  useBalancedStatsLayout,
} from '../StatsPageSupport'
import {
  ebbRateToneClass,
  METRIC_OPTIONS,
  RANGE_OPTIONS,
  startEbbinghausReview,
  StatsSummaryCards,
} from '../statsPageSections'

export default function StatsPage() {
  const navigate = useNavigate()
  const { words: wrongWords } = useWrongWords()

  const [range, setRange] = useState<RangeKey>(30)
  const [metric, setMetric] = useState<MetricKey>('words')
  const [bookId, setBookId] = useState('all')
  const [mode, setMode] = useState('all')

  const {
    daily,
    books,
    modes,
    summary,
    alltime,
    modeBreakdown,
    pieChart,
    chapterBreakdown,
    chapterModeStats,
    learnerProfile,
    useFallback,
    loading: chartLoading,
  } = useLearningStats(range, bookId, mode)

  const historyWrongWords = useMemo(
    () => wrongWords.filter(word => hasWrongWordHistory(word)),
    [wrongWords],
  )
  const pendingWrongWords = useMemo(
    () => wrongWords.filter(word => hasWrongWordPending(word)),
    [wrongWords],
  )
  const historyWrongTop10 = useMemo(
    () => buildWrongTopItems(historyWrongWords, 'history'),
    [historyWrongWords],
  )
  const pendingWrongTop10 = useMemo(
    () => buildWrongTopItems(pendingWrongWords, 'pending'),
    [pendingWrongWords],
  )

  const displayTodayDuration = alltime && alltime.today_duration_seconds > 0
    ? fmtDuration(alltime.today_duration_seconds) : '--'
  const displayAlltimeDuration = alltime && alltime.duration_seconds > 0
    ? fmtDuration(alltime.duration_seconds) : '--'

  const displayTotalNew = alltime?.total_words != null ? alltime.total_words : (chartLoading ? '…' : '--')
  const displayTodayNew = alltime?.today_new_words ?? (chartLoading ? '…' : '--')
  const displayTodayReview = alltime?.today_review_words ?? (chartLoading ? '…' : '--')
  const displayAlltimeReview = alltime?.alltime_review_words ?? (chartLoading ? '…' : '--')

  const displayTodayAccuracy = fmtPct(alltime?.today_accuracy)
  const displayAlltimeAccuracy = fmtPct(alltime?.accuracy)
  const displayStreak = alltime?.streak_days != null && alltime?.streak_days > 0
    ? alltime.streak_days : '--'
  const ebbRateCaption = ebbinghausRateCaption(alltime)
  const ebbSummaryHelp = ebbinghausSummaryHelp(alltime)

  const hasChartData = daily.some(d => {
    if (metric === 'words') return d.words_studied > 0
    if (metric === 'accuracy') return d.accuracy != null
    return d.duration_seconds > 0
  })

  const ebbStages = resolveEbbStages(alltime)
  const isInitialLoading = isStatsInitialLoading({
    chartLoading,
    summary,
    alltime,
    dailyLength: daily.length,
    booksLength: books.length,
    modesLength: modes.length,
    modeBreakdownLength: modeBreakdown.length,
    pieChartLength: pieChart.length,
    historyWrongTopLength: historyWrongTop10.length,
    pendingWrongTopLength: pendingWrongTop10.length,
    chapterBreakdownLength: chapterBreakdown.length,
    chapterModeStatsLength: chapterModeStats.length,
    hasLearnerProfile: Boolean(learnerProfile),
  })

  const statsMainLayoutRef = useRef<HTMLDivElement>(null)
  const statsLeftStackRef = useRef<HTMLDivElement>(null)
  const statsRightTopRef = useRef<HTMLDivElement>(null)
  const statsRightBottomRef = useRef<HTMLDivElement>(null)

  useBalancedStatsLayout({
    layoutRef: statsMainLayoutRef,
    leftRef: statsLeftStackRef,
    topRef: statsRightTopRef,
    bottomRef: statsRightBottomRef,
    deps: [
      chartLoading,
      historyWrongTop10.length,
      pendingWrongTop10.length,
      chapterBreakdown.length,
      chapterModeStats.length,
      range,
      metric,
      alltime?.ebbinghaus_rate,
    ],
  })

  if (isInitialLoading) {
    return <PageSkeleton variant="stats" metricCount={9} />
  }

  return (
    <div className="page-content stats-page">
      <p className="stats-page-intro">
        「新词 / 复习」来自速记（艾宾浩斯）同步数据；「累计学习新词」为全书进度与去重逻辑综合结果。
      </p>

      <StatsSummaryCards
        todayNew={displayTodayNew}
        totalNew={displayTotalNew}
        todayReview={displayTodayReview}
        alltimeReview={displayAlltimeReview}
        todayDuration={displayTodayDuration}
        alltimeDuration={displayAlltimeDuration}
        todayAccuracy={displayTodayAccuracy}
        alltimeAccuracy={displayAlltimeAccuracy}
        streak={displayStreak}
      />

        <div className="stats-section stats-section--mode-strip">
          <div className="stats-mode-strip-header">
            <h2 className="stats-section-title">模式占比与各模式统计</h2>
            {alltime?.weakest_mode && (
              <span className="mode-recommendation">
                建议加强：<strong>{MODE_LABELS[alltime.weakest_mode] || alltime.weakest_mode}</strong>
                {alltime.weakest_mode_accuracy != null && (
                  <span className="mode-recommendation-acc">（正确率 {alltime.weakest_mode_accuracy}%）</span>
                )}
              </span>
            )}
          </div>
          <p className="stats-section-hint">
            饼图与各模式「学习词数」：<strong>速记模式</strong>为速记词表去重词数（每词一行）；其余模式为练习会话累计（同一词多次练习会重复计）。各模式相加仍可能高于上方「累计学习新词数」——后者为全书章节进度与全局去重综合结果。
          </p>
          <div className="stats-mode-strip-grid">
            <h3 className="stats-mode-strip-title stats-mode-strip-title--pie">模式占比</h3>
            <h3 className="stats-mode-strip-title stats-mode-strip-title--modes">各模式统计</h3>
            <div className="stats-mode-strip-col stats-mode-strip-col--pie">
              {chartLoading ? (
                <StatsSectionSkeleton variant="donut" />
              ) : (
                <ModePieChart segments={pieChart} variant="strip" />
              )}
            </div>
            <div className="stats-mode-strip-col stats-mode-strip-col--modes">
              {chartLoading ? (
                <StatsSectionSkeleton variant="table" />
              ) : (
                <ModeBreakdownTableBody modeBreakdown={modeBreakdown} onNavigate={() => navigate('/plan')} />
              )}
            </div>
          </div>
        </div>

      <div className="stats-main-layout-wrap">
        <div className="stats-main-layout" ref={statsMainLayoutRef}>
          <div className="stats-main-left">
              <div className="stats-left-stack" ref={statsLeftStackRef}>
                    <section className="stats-section stats-card-profile" aria-labelledby="stats-profile-title">
                      <h2 id="stats-profile-title" className="stats-section-title">统一学习画像</h2>
                      <p className="stats-section-hint">把薄弱模式、易错维度、重复困惑主题和下一步动作放在同一视图里。</p>
                      <LearnerProfileCard learnerProfile={learnerProfile} loading={chartLoading} />
                    </section>
                    <section className="stats-section stats-card-wrong" aria-labelledby="stats-wrong-title">
                      <h2 id="stats-wrong-title" className="stats-section-title">错词分层 Top 10</h2>
                      <p className="stats-section-hint">历史错词负责留痕，未过错词负责当前攻克，两类统计口径分开显示。</p>
                      <div className="stats-card-wrong-body">
                        {chartLoading ? (
                          <StatsSectionSkeleton variant="donut" />
                        ) : historyWrongTop10.length === 0 && pendingWrongTop10.length === 0 ? (
                          <div className="stats-empty"><p>暂无错词数据</p></div>
                        ) : (
                          <div className="stats-wrong-vertical">
                            <WrongTopBlock
                              title="历史错词 Top 10"
                              scope="history"
                              items={historyWrongTop10}
                            />
                            <WrongTopBlock
                              title="未过错词 Top 10"
                              scope="pending"
                              items={pendingWrongTop10}
                            />
                          </div>
                        )}
                      </div>
                    </section>

                    <section className="stats-section stats-card-wrong-overview" aria-labelledby="stats-wrong-overview-title">
                      <h2 id="stats-wrong-overview-title" className="stats-section-title">错词本概览</h2>
                      <div className="stats-wrong-summary">
                        <div className="stats-wrong-count">
                          <span className="wrong-num">{historyWrongWords.length}</span>
                          <span className="wrong-label">个历史错词</span>
                        </div>
                        <div className="stats-wrong-count">
                          <span className="wrong-num">{pendingWrongWords.length}</span>
                          <span className="wrong-label">个未过错词</span>
                        </div>
                        {wrongWords.length > 0 && (
                          <button type="button" className="stats-review-btn" onClick={() => navigate('/errors')}>
                            查看错词本 →
                          </button>
                        )}
                      </div>
                    </section>
              </div>
            </div>
          <div className="stats-main-right">
              <div className="stats-main-right-top" ref={statsRightTopRef}>
                <div className="stats-main-cell stats-main-cell--ebb">
                    <section className="stats-section stats-card-ebbinghaus" aria-labelledby="stats-ebb-title">
                      <h2 id="stats-ebb-title" className="stats-section-title">艾宾浩斯复习达成</h2>
                      <p className="stats-section-hint stats-ebb-hint-compact">
                        衡量「到期是否按时复习」：蓝虚线为艾宾浩斯标准遗忘曲线（理论参考折线）；橙实线为各轮实际按时完成度。橙线整体高于蓝线，说明按时复习对抗遗忘的效果越好。
                      </p>
                      <div className="stats-ebb-inner">
                        {chartLoading ? (
                          <StatsSectionSkeleton variant="split" />
                        ) : (
                          <>
                            <div className="ebbinghaus-summary-row ebbinghaus-summary-row--compact ebbinghaus-summary-row--split">
                              <div className="ebbinghaus-rate-block">
                                <div
                                  className={`ebbinghaus-big ebbinghaus-big--compact ${ebbRateToneClass(alltime?.ebbinghaus_rate)}`}
                                >
                                  {fmtPct(alltime?.ebbinghaus_rate)}
                                </div>
                                <div className="ebb-rate-caption">{ebbRateCaption}</div>
                              </div>
                              <div className="ebbinghaus-meta ebbinghaus-meta--compact">
                                <span className="ebb-meta-item">
                                  <span className="ebb-meta-label">已到复习点</span>
                                  <span className="ebb-meta-num">{alltime?.ebbinghaus_due_total ?? 0}</span>
                                </span>
                                <span className="ebb-meta-item">
                                  <span className="ebb-meta-label">按时完成</span>
                                  <span className="ebb-meta-num">{alltime?.ebbinghaus_met ?? 0}</span>
                                </span>
                                <span className="ebb-meta-item">
                                  <span className="ebb-meta-label">复习库词数</span>
                                  <span className="ebb-meta-num">{alltime?.qm_word_total ?? 0}</span>
                                </span>
                              </div>
                            </div>
                            <p className="ebb-meta-help">{ebbSummaryHelp}</p>
                            {(alltime?.upcoming_reviews_3d ?? 0) > 0 && (
                              <div className="ebb-upcoming-hint">
                                <span>接下来3天待复习 <strong>{alltime?.upcoming_reviews_3d}</strong> 词</span>
                                <button
                                  type="button"
                                  className="stats-review-btn stats-review-btn--ebb"
                                  onClick={() => startEbbinghausReview(navigate)}
                                >
                                  去复习
                                </button>
                              </div>
                            )}
                            <div className="stats-ebb-chart-wrap">
                              <EbbinghausDualChart stages={ebbStages} compact />
                            </div>
                          </>
                        )}
                      </div>
                    </section>
                </div>
                <div className="stats-main-cell stats-main-cell--learning">
                    <section className="stats-section stats-section--learning" aria-labelledby="stats-learning-title">
                      <div className="stats-section-header stats-learning-split-head">
                        <h2 id="stats-learning-title" className="stats-section-title">学习记录</h2>
                        <SegmentedControl
                          className="lc-tabs"
                          ariaLabel="学习记录时间范围"
                          value={range}
                          onChange={setRange}
                          options={RANGE_OPTIONS.map(o => ({
                            value: o.value,
                            label: o.label,
                          }))}
                        />
                      </div>

                      <div className="lc-filters lc-filters--compact">
                        <UnderlineTabs
                          className="lc-metric-tabs"
                          ariaLabel="学习记录指标"
                          value={metric}
                          onChange={setMetric}
                          options={METRIC_OPTIONS.map(o => ({
                            value: o.value,
                            label: o.label,
                          }))}
                        />
                        <div className="lc-selects">
                          {books.length > 0 && (
                            <select
                              className="lc-select"
                              value={bookId}
                              onChange={e => setBookId(e.target.value)}
                            >
                              <option value="all">全部词书</option>
                              {books.map(b => (
                                <option key={b.id} value={b.id}>{b.title}</option>
                              ))}
                            </select>
                          )}
                          {modes.length > 0 && (
                            <select
                              className="lc-select"
                              value={mode}
                              onChange={e => setMode(e.target.value)}
                            >
                              <option value="all">全部模式</option>
                              {modes.map(m => (
                                <option key={m} value={m}>{MODE_LABELS[m] || m}</option>
                              ))}
                            </select>
                          )}
                        </div>
                      </div>

                      {chartLoading ? (
                        <StatsSectionSkeleton variant="chart" />
                      ) : !hasChartData ? (
                        <div className="stats-empty stats-empty--compact">
                          <p>该时间段暂无学习记录</p>
                          <a className="stats-go-practice" onClick={() => navigate('/plan')}>去练习 →</a>
                        </div>
                      ) : (
                        <LearningChart data={daily} metric={metric} range={range} compact />
                      )}

                      {!chartLoading && hasChartData && summary && (
                        <div className="lc-legend-row lc-legend-row--compact">
                          <div className="lc-legend">
                            <span className="lc-crosshair-legend" title="悬停图表时显示">
                              <i className="lc-crosshair-icon" aria-hidden />
                              悬停所选日期
                            </span>
                            <span className="lc-legend-sep" aria-hidden>
                              ·
                            </span>
                            <span className="legend-dot legend-dot--accent" />
                            <span>{METRIC_OPTIONS.find(o => o.value === metric)?.label}</span>
                            {useFallback && (
                              <span className="lc-fallback-note">（基于章节进度估算）</span>
                            )}
                          </div>
                          <div className="lc-period-summary">
                            <span>{range}天共 <strong>{summary.total_words}</strong> 词</span>
                            {summary.accuracy != null && <span>· 正确率 <strong>{summary.accuracy}%</strong></span>}
                            {!useFallback && <span>· <strong>{summary.total_sessions}</strong> 次练习</span>}
                          </div>
                          {alltime?.trend_direction && alltime?.trend_direction !== 'stable' && (
                            <div className="lc-trend-insight">
                              <span className={`lc-trend-badge lc-trend-badge--${alltime.trend_direction}`}>
                                {alltime.trend_direction === 'improving' ? '↑' : '↓'}
                              </span>
                              <span>
                                {alltime.trend_direction === 'improving'
                                  ? '学习效果在提升'
                                  : '学习效果有下滑，建议加强复习'}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </section>
                </div>
              </div>
              <div className="stats-main-right-bottom" ref={statsRightBottomRef}>
                <div className="stats-main-cell stats-main-cell--chapter">
                    <section className="stats-section stats-section--chapter-cell" aria-labelledby="stats-chapter-detail-title">
                      <h2 id="stats-chapter-detail-title" className="stats-section-title">章节正确率（细项）</h2>
                      <p className="stats-section-hint">按章节汇总的答题与词数</p>
                      {chartLoading ? (
                        <StatsSectionSkeleton variant="table" />
                      ) : chapterBreakdown.length === 0 ? (
                        <div className="stats-empty stats-empty--chapter-cell">
                          <p>暂无章节数据</p>
                          <a className="stats-go-practice" onClick={() => navigate('/plan')}>去练习 →</a>
                        </div>
                      ) : (
                        <div className="mode-breakdown-table-wrap stats-table-scroll--in-cell">
                          <table className="stats-data-table stats-table--compact">
                            <thead>
                              <tr>
                                <th>词书</th>
                                <th>章节</th>
                                <th>已学词数</th>
                                <th>答对</th>
                                <th>答错</th>
                                <th>正确率</th>
                              </tr>
                            </thead>
                            <tbody>
                              {chapterBreakdown.map(row => (
                                <tr key={`${row.book_id}-${row.chapter_id}`}>
                                  <td>{row.book_title}</td>
                                  <td>{row.chapter_title}</td>
                                  <td>{row.words_learned}</td>
                                  <td>{row.correct}</td>
                                  <td>{row.wrong}</td>
                                  <td>{fmtPct(row.accuracy)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </section>
                </div>
                <div className="stats-main-cell stats-main-cell--chapter-mode">
                    <section className="stats-section stats-section--chapter-cell" aria-labelledby="stats-chapter-mode-title">
                      <h2 id="stats-chapter-mode-title" className="stats-section-title">章节 × 模式 正确率</h2>
                      <p className="stats-section-hint">同一章节在不同练习模式下的正确率（独立统计）</p>
                      {chartLoading ? (
                        <StatsSectionSkeleton variant="table" />
                      ) : chapterModeStats.length === 0 ? (
                        <div className="stats-empty stats-empty--chapter-cell"><p>暂无分模式章节数据</p></div>
                      ) : (
                        <div className="mode-breakdown-table-wrap stats-table-scroll--in-cell">
                          <table className="stats-data-table stats-table--compact">
                            <thead>
                              <tr>
                                <th>词书</th>
                                <th>章节</th>
                                <th>模式</th>
                                <th>答对</th>
                                <th>答错</th>
                                <th>正确率</th>
                              </tr>
                            </thead>
                            <tbody>
                              {chapterModeStats.map((row, i) => (
                                <tr key={`${row.book_id}-${row.chapter_id}-${row.mode}-${i}`}>
                                  <td>{row.book_title}</td>
                                  <td>{row.chapter_title}</td>
                                  <td>{MODE_LABELS[row.mode] || row.mode}</td>
                                  <td>{row.correct}</td>
                                  <td>{row.wrong}</td>
                                  <td>{row.accuracy}%</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </section>
                </div>
              </div>
              </div>
            </div>
          </div>
    </div>
  )
}

