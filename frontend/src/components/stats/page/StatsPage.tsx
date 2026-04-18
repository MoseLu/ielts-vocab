import { PageSkeleton } from '../../ui'
import { SegmentedControl, UnderlineTabs } from '../../ui/NavigationControls'
import {
  EbbinghausDualChart,
  fmtDuration,
  fmtPct,
  LearnerProfileCard,
  LearningChart,
  MODE_LABELS,
  ModeBreakdownTableBody,
  ModePieChart,
  StatsSectionSkeleton,
  WrongTopBlock,
} from '../StatsPageSupport'
import {
  ebbRateToneClass,
  METRIC_OPTIONS,
  RANGE_OPTIONS,
  StatsSummaryCards,
} from '../statsPageSections'
import { WRONG_WORD_SCOPE_LABELS } from '../../../features/vocabulary/wrongWordsStore'
import { useStatsPage } from '../../../composables/stats/page/useStatsPage'

export default function StatsPage() {
  const {
    range,
    metric,
    bookId,
    mode,
    daily,
    books,
    modes,
    summary,
    alltime,
    modeBreakdown,
    pieChart,
    learnerProfile,
    useFallback,
    chartLoading,
    learnerProfileLoading,
    historyWrongTop10,
    pendingWrongTop10,
    displayTodayNewWords,
    displayTodayReviewWords,
    displayTodayWords,
    displayTodayDuration,
    displayTodayAccuracy,
    displayTotalLearnedNewWords,
    displayTotalReviewedWords,
    displayTotalStudyDuration,
    displayStreak,
    ebbRateCaption,
    ebbSummaryHelp,
    weakestModeLabel,
    gameCampaignStats,
    hasChartData,
    ebbStages,
    isInitialLoading,
    setRange,
    setMetric,
    setBookId,
    setMode,
    goToPlan,
    startEbbinghausReview,
  } = useStatsPage()

  if (isInitialLoading) {
    return <div className="page-content stats-page"><PageSkeleton variant="stats" metricCount={9} /></div>
  }

  const periodPrimarySummary = summary
    ? (
        metric === 'duration'
          ? `${range}天共 ${summary.total_duration_seconds > 0 ? fmtDuration(summary.total_duration_seconds) : '--'}`
          : metric === 'accuracy'
            ? `${range}天平均正确率 ${summary.accuracy != null ? `${summary.accuracy}%` : '--'}`
            : `${range}天共 ${summary.total_words} 词`
      )
    : null

  return (
    <div className="page-content stats-page">
      <StatsSummaryCards
        todayNewWords={displayTodayNewWords}
        todayReviewWords={displayTodayReviewWords}
        totalLearnedNewWords={displayTotalLearnedNewWords}
        totalReviewedWords={displayTotalReviewedWords}
        totalStudyDuration={displayTotalStudyDuration}
        todayWords={displayTodayWords}
        todayDuration={displayTodayDuration}
        todayAccuracy={displayTodayAccuracy}
        streak={displayStreak}
      />

      <div className="stats-section stats-section--mode-strip">
        <div className="stats-mode-strip-header">
          <h2 className="stats-section-title">模式占比与各模式统计</h2>
          {weakestModeLabel && (
            <span className="mode-recommendation">
              建议加强：<strong>{MODE_LABELS[weakestModeLabel] || weakestModeLabel}</strong>
              {alltime?.weakest_mode_accuracy != null && (
                <span className="mode-recommendation-acc">（正确率 {alltime.weakest_mode_accuracy}%）</span>
              )}
            </span>
          )}
        </div>
        <p className="stats-section-hint">
          饼图与各模式「学习词数」：<strong>速记模式</strong>按速记词表里的不同单词统计；其余模式按练习会话累计统计，同一个词重复练会重复计数。所以各模式相加，可能高于上方「累计学习新词」。
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
              <ModeBreakdownTableBody modeBreakdown={modeBreakdown} onNavigate={goToPlan} />
            )}
          </div>
        </div>
      </div>

      {gameCampaignStats ? (
        <div className="stats-section">
          <div className="stats-mode-strip-header">
            <h2 className="stats-section-title">五维战役独立统计</h2>
            <span className="mode-recommendation">口语 Boss / 奖励关与词链数据单独归档</span>
          </div>
          <p className="stats-section-hint">
            五维战役不再混入经典练习模式和通用错词本。这里单独看战役投入、命中率与挑战频次。
          </p>
          <div className="stats-cards">
            <div className="stats-card stats-card--simple">
              <div className="stats-card-label">战役词链学习词数</div>
              <div className="stats-card-value">{gameCampaignStats.wordsStudied}</div>
            </div>
            <div className="stats-card stats-card--simple">
              <div className="stats-card-label">战役挑战次数</div>
              <div className="stats-card-value">{gameCampaignStats.sessions}</div>
            </div>
            <div className="stats-card stats-card--simple">
              <div className="stats-card-label">战役正确率</div>
              <div className="stats-card-value">{fmtPct(gameCampaignStats.accuracy)}</div>
            </div>
            <div className="stats-card stats-card--simple">
              <div className="stats-card-label">战役学习时长</div>
              <div className="stats-card-value">{fmtDuration(gameCampaignStats.durationSeconds)}</div>
            </div>
          </div>
        </div>
      ) : null}

      <div className="stats-main-layout-wrap">
        <div className="stats-insight-grid">
          <div className="stats-main-card stats-main-card--profile">
            <section className="stats-section stats-card-profile" aria-labelledby="stats-profile-title">
              <h2 id="stats-profile-title" className="stats-section-title">统一学习画像</h2>
              <p className="stats-section-hint">把薄弱模式、易错维度、重复困惑主题和下一步动作放在同一视图里。</p>
              <LearnerProfileCard learnerProfile={learnerProfile} loading={learnerProfileLoading} />
            </section>
          </div>

          <div className="stats-main-card stats-main-card--ebb stats-main-cell--ebb">
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
                          onClick={startEbbinghausReview}
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

          <div className="stats-main-card stats-main-card--learning stats-main-cell--learning">
            <section className="stats-section stats-section--learning" aria-labelledby="stats-learning-title">
              <div className="stats-section-header stats-learning-split-head">
                <h2 id="stats-learning-title" className="stats-section-title">学习记录</h2>
                <SegmentedControl
                  className="lc-tabs"
                  ariaLabel="学习记录时间范围"
                  value={range}
                  onChange={setRange}
                  options={RANGE_OPTIONS.map(option => ({
                    value: option.value,
                    label: option.label,
                  }))}
                />
              </div>

              <div className="lc-filters lc-filters--compact">
                <UnderlineTabs
                  className="lc-metric-tabs"
                  ariaLabel="学习记录指标"
                  value={metric}
                  onChange={setMetric}
                  options={METRIC_OPTIONS.map(option => ({
                    value: option.value,
                    label: option.label,
                  }))}
                />
                <div className="lc-selects">
                  {books.length > 0 && (
                    <select
                      className="lc-select"
                      value={bookId}
                      onChange={event => setBookId(event.target.value)}
                    >
                      <option value="all">全部词书</option>
                      {books.map(book => (
                        <option key={book.id} value={book.id}>{book.title}</option>
                      ))}
                    </select>
                  )}
                  {modes.length > 0 && (
                    <select
                      className="lc-select"
                      value={mode}
                      onChange={event => setMode(event.target.value)}
                    >
                      <option value="all">全部模式</option>
                      {modes.map(item => (
                        <option key={item} value={item}>{MODE_LABELS[item] || item}</option>
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
                  <a className="stats-go-practice" onClick={goToPlan}>去练习 →</a>
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
                    <span>{METRIC_OPTIONS.find(option => option.value === metric)?.label}</span>
                    {useFallback && (
                      <span className="lc-fallback-note">（基于章节进度估算）</span>
                    )}
                  </div>
                  <div className="lc-period-summary">
                    {periodPrimarySummary && <span>{periodPrimarySummary}</span>}
                    {metric !== 'accuracy' && summary.accuracy != null && <span>· 正确率 <strong>{summary.accuracy}%</strong></span>}
                    {metric !== 'words' && <span>· 学习词数 <strong>{summary.total_words}</strong> 词</span>}
                    {!useFallback && <span>· <strong>{summary.total_sessions}</strong> 次练习</span>}
                  </div>
                  {alltime?.trend_direction && alltime.trend_direction !== 'stable' && (
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

        <section className="stats-wrong-cluster" aria-label="错词分层">
          <div className="stats-wrong-cluster-grid">
            <div className="stats-main-card stats-main-card--wrong-history">
              <section className="stats-section stats-card-wrong" aria-label={`${WRONG_WORD_SCOPE_LABELS.history} Top 10`}>
                <div className="stats-card-wrong-body">
                  {chartLoading ? (
                    <StatsSectionSkeleton variant="donut" />
                  ) : historyWrongTop10.length === 0 ? (
                    <div className="stats-empty"><p>暂无累计错词数据</p></div>
                  ) : (
                    <WrongTopBlock
                      title={`${WRONG_WORD_SCOPE_LABELS.history} Top 10`}
                      scope="history"
                      items={historyWrongTop10}
                    />
                  )}
                </div>
              </section>
            </div>

            <div className="stats-main-card stats-main-card--wrong-pending">
              <section className="stats-section stats-card-wrong" aria-label={`${WRONG_WORD_SCOPE_LABELS.pending} Top 10`}>
                <div className="stats-card-wrong-body">
                  {chartLoading ? (
                    <StatsSectionSkeleton variant="donut" />
                  ) : pendingWrongTop10.length === 0 ? (
                    <div className="stats-empty"><p>暂无待清错词数据</p></div>
                  ) : (
                    <WrongTopBlock
                      title={`${WRONG_WORD_SCOPE_LABELS.pending} Top 10`}
                      scope="pending"
                      items={pendingWrongTop10}
                    />
                  )}
                </div>
              </section>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
