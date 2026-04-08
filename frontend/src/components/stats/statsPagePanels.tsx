import { Skeleton } from '../ui'
import { getPracticeModeLabel, normalizeModeText } from '../../constants/practiceModes'
import { getWrongWordDimensionLabel, type WrongWordCollectionScope } from '../../features/vocabulary/wrongWordsStore'
import type { LearnerProfile, ModeStat } from '../../features/vocabulary/hooks'
import { MODE_LABELS, fmtDuration, fmtPct, inferErrorReason, trendDirectionLabel, type WrongTopDisplayItem } from './statsPageCore'
import { WrongTopPieChart } from './statsPageCharts'

export function StatsSectionSkeleton({
  variant = 'panel',
}: {
  variant?: 'panel' | 'table' | 'chart' | 'donut' | 'split'
}) {
  if (variant === 'table') {
    return (
      <div className="stats-skeleton stats-skeleton--table" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} width="100%" height={16} />
        ))}
      </div>
    )
  }

  if (variant === 'donut') {
    return (
      <div className="stats-skeleton stats-skeleton--donut" aria-hidden="true">
        <div className="stats-skeleton-donut" />
        <div className="stats-skeleton-legend">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="stats-skeleton-legend-row">
              <Skeleton width="54%" height={12} />
              <Skeleton width="18%" height={12} />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (variant === 'split') {
    return (
      <div className="stats-skeleton stats-skeleton--split" aria-hidden="true">
        <div className="stats-skeleton-split-head">
          <Skeleton width="24%" height={40} />
          <div className="stats-skeleton-split-meta">
            <Skeleton width="100%" height={12} />
            <Skeleton width="72%" height={12} />
            <Skeleton width="86%" height={12} />
          </div>
        </div>
        <div className="stats-skeleton-chart" />
      </div>
    )
  }

  return (
    <div className={`stats-skeleton stats-skeleton--${variant}`} aria-hidden="true">
      <Skeleton width="34%" height={16} />
      <Skeleton width="58%" height={12} />
      <div className="stats-skeleton-chart" />
    </div>
  )
}

export function LearnerProfileCard({
  learnerProfile,
  loading,
}: {
  learnerProfile: LearnerProfile | null
  loading: boolean
}) {
  if (loading) {
    return <StatsSectionSkeleton variant="panel" />
  }

  if (!learnerProfile) {
    return (
      <div className="stats-empty">
        <p>暂无学习画像数据</p>
      </div>
    )
  }

  const { summary, dimensions, focus_words: focusWords, repeated_topics: repeatedTopics, next_actions: nextActions } = learnerProfile

  return (
    <div className="stats-profile-card">
      <div className="stats-profile-summary">
        <div className="stats-profile-pill">
          <span className="stats-profile-pill__label">最弱模式</span>
          <strong>{getPracticeModeLabel(summary.weakest_mode, summary.weakest_mode_label) || '待判定'}</strong>
        </div>
        <div className="stats-profile-pill">
          <span className="stats-profile-pill__label">连续学习</span>
          <strong>{summary.streak_days || 0} 天</strong>
        </div>
        <div className="stats-profile-pill">
          <span className="stats-profile-pill__label">速记待复习</span>
          <strong>{summary.due_reviews || 0} 词</strong>
        </div>
      </div>

      <div className="stats-profile-block">
        <h3 className="stats-subsection-title">薄弱维度</h3>
        <div className="stats-profile-chip-list">
          {dimensions.slice(0, 3).map(item => (
            <div key={item.dimension} className="stats-profile-chip">
              <span>{getWrongWordDimensionLabel(item.dimension, item.label) ?? item.label}</span>
              <strong>{fmtPct(item.accuracy)}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="stats-profile-block stats-profile-block--focus">
        <h3 className="stats-subsection-title">重点突破词</h3>
        {focusWords.length > 0 ? (
          <ul className="stats-profile-list stats-profile-list--focus">
            {focusWords.slice(0, 3).map(item => (
              <li key={item.word}>
                <strong>{item.word}</strong>
                <span>{getWrongWordDimensionLabel(item.dominant_dimension, item.dominant_dimension_label) ?? item.dominant_dimension_label}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="stats-profile-muted">暂无重点突破词</p>
        )}
      </div>

      <div className="stats-profile-block stats-profile-block--topics">
        <h3 className="stats-subsection-title">重复困惑主题</h3>
        {repeatedTopics.length > 0 ? (
          <ul className="stats-profile-list stats-profile-list--topics">
            {repeatedTopics.slice(0, 3).map(topic => (
              <li key={`${topic.word_context}-${topic.title}`}>
                <strong>{topic.word_context || '主题'}</strong>
                <span>{topic.count} 次</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="stats-profile-muted">近期没有重复追问主题</p>
        )}
      </div>

      <div className="stats-profile-block stats-profile-block--actions">
        <h3 className="stats-subsection-title">下一步动作</h3>
        <ul className="stats-profile-actions">
          {nextActions.slice(0, 2).map(action => (
            <li key={action}>{normalizeModeText(action)}</li>
          ))}
        </ul>
      </div>

      <p className="stats-profile-trend">{trendDirectionLabel(summary.trend_direction)}</p>
    </div>
  )
}

export function ModeBreakdownTableBody({
  modeBreakdown,
  onNavigate,
}: {
  modeBreakdown: ModeStat[]
  onNavigate: () => void
}) {
  if (modeBreakdown.length === 0) {
    return (
      <div className="stats-empty stats-empty--mode-strip">
        <p>完成练习后将显示各模式数据</p>
        <a className="stats-go-practice" onClick={onNavigate}>去练习 →</a>
      </div>
    )
  }

  return (
    <div className="mode-breakdown-table-wrap mode-breakdown-table-wrap--strip">
      <table className="stats-data-table stats-table--compact stats-table--mode-strip">
        <thead>
          <tr>
            <th>模式</th>
            <th title="速记：词表去重；其他模式：会话累计（可重复）">学习词数</th>
            <th>答题次数</th>
            <th>正确率</th>
            <th>练习</th>
            <th>场均</th>
            <th>时长</th>
          </tr>
        </thead>
        <tbody>
          {modeBreakdown.map(mode => (
            <tr key={mode.mode}>
              <td>{mode.mode in MODE_LABELS ? MODE_LABELS[mode.mode] : mode.mode}</td>
              <td>{mode.words_studied}</td>
              <td>{mode.attempts ?? (mode.correct_count + mode.wrong_count)}</td>
              <td>{fmtPct(mode.accuracy)}</td>
              <td>{mode.sessions}</td>
              <td>{mode.avg_words_per_session ?? '--'}</td>
              <td>{mode.duration_seconds > 0 ? fmtDuration(mode.duration_seconds) : '--'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function WrongTopBlock({
  title,
  scope,
  items,
}: {
  title: string
  scope: WrongWordCollectionScope
  items: WrongTopDisplayItem[]
}) {
  if (items.length === 0) {
    return (
      <div className="stats-wrong-vertical">
        <h3 className="stats-subsection-title">{title}</h3>
        <div className="stats-empty"><p>暂无数据</p></div>
      </div>
    )
  }

  return (
    <div className="stats-wrong-vertical">
      <div className="stats-wrong-pie-block">
        <h3 className="stats-subsection-title">{title}占比（扇形图）</h3>
        <WrongTopPieChart items={items} />
      </div>
      <div className="stats-wrong-table-block">
        <h3 className="stats-subsection-title">{title}明细</h3>
        <div className="stats-wrong-table-scroll">
          <table className="stats-data-table">
            <thead>
              <tr>
                <th>序号</th>
                <th>单词</th>
                <th>音标</th>
                <th>{scope === 'pending' ? '待清错次' : '累计错次'}</th>
                <th>主要问题类型</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={`${item.word}-${index}`}>
                  <td>{index + 1}</td>
                  <td className="td-word">{item.word}</td>
                  <td className="td-muted">{item.phonetic || '—'}</td>
                  <td><span className="wrong-count-badge">{item.wrong_count}</span></td>
                  <td><span className="error-reason-tag">{inferErrorReason(item, scope)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
