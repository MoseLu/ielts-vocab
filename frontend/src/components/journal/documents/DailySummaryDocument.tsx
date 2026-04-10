import { Skeleton } from '../../ui'
import {
  getPracticeModeLabel,
  getWrongWordDimensionModeLabel,
  normalizeModeText,
} from '../../../constants/practiceModes'
import { renderJournalMarkdown } from '../../../lib/journalMarkdown'
import type { DailySummary, LearnerProfile, SummaryGenerationJob } from '../../../lib/schemas'

interface DailySummaryDocumentProps {
  summary: DailySummary | null
  learnerProfile: LearnerProfile | null
  learnerProfileLoading: boolean
  summaryLoading: boolean
  summaryError: string
  summaryProgress: SummaryGenerationJob | null
  formatDateTime: (iso: string) => string
}

function DailySummarySkeleton() {
  return (
    <div className="journal-doc-skeleton journal-doc-skeleton--summary" aria-hidden="true">
      <Skeleton width={110} height={28} />
      <Skeleton width="42%" height={32} />
      <Skeleton width="68%" height={16} />
      <Skeleton width="52%" height={16} />
      <Skeleton width="28%" height={14} />
      <div className="journal-doc-skeleton-body">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} width={index === 7 ? '56%' : '100%'} height={14} />
        ))}
      </div>
    </div>
  )
}

function SummaryProgressPanel({ progress }: { progress: SummaryGenerationJob }) {
  return (
    <div className="journal-summary-progress-panel" role="status" aria-live="polite">
      <span className="journal-summary-progress-panel__eyebrow">正在生成每日总结</span>
      <div className="journal-summary-progress-panel__head">
        <strong>生成进度</strong>
        <span>{progress.progress}%</span>
      </div>
      <p className="journal-summary-progress-panel__copy">{progress.message}</p>
      <div className="journal-summary-progress__track" aria-hidden="true">
        <span
          className="journal-summary-progress__fill"
          style={{ width: `${progress.progress}%` }}
        />
      </div>
    </div>
  )
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0分钟'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}分钟`
  return `${Math.floor(minutes / 60)}小时${minutes % 60 ? `${minutes % 60}分钟` : ''}`
}

function formatDurationCompact(seconds: number): string {
  if (!seconds) return ''
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}分钟`
  return `${Math.floor(minutes / 60)}小时${minutes % 60 ? `${minutes % 60}分钟` : ''}`
}

function trendLabel(value: LearnerProfile['summary']['trend_direction']): string {
  if (value === 'improving') return '学习趋势在提升'
  if (value === 'declining') return '学习趋势有下滑'
  if (value === 'new') return '画像刚开始积累'
  return '学习趋势相对稳定'
}

function formatEventTime(iso: string | null): string {
  if (!iso) return '时间未知'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function buildActivityDetail(event: LearnerProfile['recent_activity'][number]): string {
  const parts: string[] = []
  const modeLabel = getPracticeModeLabel(event.mode, event.mode_label)

  if (modeLabel) {
    parts.push(modeLabel)
  }

  if (event.word) {
    parts.push(event.word)
  }

  if (event.item_count > 0) {
    parts.push(`${event.item_count}项`)
  }

  const attempts = event.correct_count + event.wrong_count
  if (attempts > 0) {
    parts.push(`${event.correct_count}/${attempts}`)
  }

  const durationText = formatDurationCompact(event.duration_seconds)
  if (durationText) {
    parts.push(durationText)
  }

  return parts.join(' · ')
}

function SummaryProfileSkeleton() {
  return (
    <section className="journal-summary-profile journal-summary-profile--loading" aria-hidden="true">
      <div className="journal-summary-profile__head">
        <div className="journal-summary-profile__copy">
          <Skeleton width={88} height={12} />
          <Skeleton width="28%" height={24} />
          <Skeleton width="56%" height={14} />
        </div>
        <Skeleton width={120} height={28} />
      </div>

      <div className="journal-summary-profile__metrics">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="journal-summary-profile__metric">
            <Skeleton width="42%" height={12} />
            <Skeleton width="54%" height={20} />
          </div>
        ))}
      </div>

      <div className="journal-summary-profile__grid">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="journal-summary-profile__card">
            <Skeleton width="32%" height={12} />
            <Skeleton width="90%" height={14} />
            <Skeleton width="72%" height={14} />
          </div>
        ))}
      </div>
    </section>
  )
}

function SummaryProfilePanel({
  learnerProfile,
  loading,
}: {
  learnerProfile: LearnerProfile | null
  loading: boolean
}) {
  if (loading) {
    return <SummaryProfileSkeleton />
  }

  if (!learnerProfile) {
    return null
  }

  const {
    summary,
    dimensions,
    focus_words: focusWords,
    repeated_topics: repeatedTopics,
    next_actions: nextActions,
    activity_summary: activitySummary,
    activity_source_breakdown: activitySourceBreakdown,
    recent_activity: recentActivity,
  } = learnerProfile
  const weakestModeLabel = getPracticeModeLabel(summary.weakest_mode, summary.weakest_mode_label)
  const weakestModeText = weakestModeLabel
    ? `${weakestModeLabel}${summary.weakest_mode_accuracy != null ? ` · ${summary.weakest_mode_accuracy}%` : ''}`
    : '待继续积累样本'
  const activityAttempts = activitySummary.correct_count + activitySummary.wrong_count
  const activityAccuracy = activityAttempts > 0
    ? Math.round((activitySummary.correct_count / activityAttempts) * 100)
    : null
  const activityOverview = activitySummary.total_events > 0
    ? `今日共追踪 ${activitySummary.total_events} 条学习动作，覆盖 ${activitySummary.books_touched} 本词书、${activitySummary.chapters_touched} 个章节、${activitySummary.words_touched} 个单词${activitySummary.total_duration_seconds > 0 ? `，累计 ${formatDuration(activitySummary.total_duration_seconds)}` : ''}${activityAccuracy != null ? `，动作口径答题正确率 ${activityAccuracy}%` : ''}。`
    : ''

  return (
    <section className="journal-summary-profile" aria-labelledby="journal-summary-profile-title">
      <div className="journal-summary-profile__head">
        <div className="journal-summary-profile__copy">
          <span className="journal-summary-profile__eyebrow">Learning Profile</span>
          <h2 id="journal-summary-profile-title" className="journal-summary-profile__title">统一学习画像</h2>
          <p className="journal-summary-profile__subtitle">最弱模式：{weakestModeText}</p>
        </div>
        <span className="journal-summary-profile__trend">{trendLabel(summary.trend_direction)}</span>
      </div>

      <div className="journal-summary-profile__metrics">
        <div className="journal-summary-profile__metric">
          <span>今日词数</span>
          <strong>{summary.today_words}</strong>
        </div>
        <div className="journal-summary-profile__metric">
          <span>正确率</span>
          <strong>{summary.today_accuracy}%</strong>
        </div>
        <div className="journal-summary-profile__metric">
          <span>学习时长</span>
          <strong>{formatDuration(summary.today_duration_seconds)}</strong>
        </div>
        <div className="journal-summary-profile__metric">
          <span>连续学习</span>
          <strong>{summary.streak_days} 天</strong>
        </div>
        <div className="journal-summary-profile__metric">
          <span>速记待复习</span>
          <strong>{summary.due_reviews} 词</strong>
        </div>
      </div>

      <div className="journal-summary-profile__grid">
        <section className="journal-summary-profile__card journal-summary-profile__card--wide">
          <div className="journal-summary-profile__section-head">
            <h3>今日行为流</h3>
            <span className="journal-summary-profile__section-meta">{activitySummary.total_events} 条事件</span>
          </div>
          {activitySummary.total_events > 0 ? (
            <>
              <p className="journal-summary-profile__description">{activityOverview}</p>
              {activitySourceBreakdown.length > 0 ? (
                <div className="journal-summary-profile__chips">
                  {activitySourceBreakdown.map(item => (
                    <span key={item.source} className="journal-summary-profile__chip">
                      {item.label} {item.count}
                    </span>
                  ))}
                </div>
              ) : null}
              <ol className="journal-summary-profile__timeline">
                {recentActivity.slice(0, 6).map(event => {
                  const detail = buildActivityDetail(event)

                  return (
                    <li key={event.id} className="journal-summary-profile__timeline-item">
                      <div className="journal-summary-profile__timeline-main">
                        <strong className="journal-summary-profile__timeline-title">{normalizeModeText(event.title)}</strong>
                        <span className="journal-summary-profile__timeline-meta">
                          {formatEventTime(event.occurred_at)} · {event.source_label}
                        </span>
                      </div>
                      {detail ? (
                        <span className="journal-summary-profile__timeline-detail">{detail}</span>
                      ) : null}
                    </li>
                  )
                })}
              </ol>
            </>
          ) : (
            <p className="journal-summary-profile__empty">今天还没有沉淀到统一行为流的学习动作</p>
          )}
        </section>

        <section className="journal-summary-profile__card">
          <h3>薄弱维度</h3>
          {dimensions.length > 0 ? (
            <div className="journal-summary-profile__chips">
              {dimensions.slice(0, 4).map(item => (
                <span key={item.dimension} className="journal-summary-profile__chip">
                  {getWrongWordDimensionModeLabel(item.dimension, item.label) ?? item.label} {item.accuracy ?? '--'}%
                </span>
              ))}
            </div>
          ) : (
            <p className="journal-summary-profile__empty">暂无薄弱维度数据</p>
          )}
        </section>

        <section className="journal-summary-profile__card">
          <h3>重点突破词</h3>
          {focusWords.length > 0 ? (
            <ul className="journal-summary-profile__list">
              {focusWords.slice(0, 4).map(item => (
                <li key={item.word}>
                  <strong>{item.word}</strong>
                  <span>{getWrongWordDimensionModeLabel(item.dominant_dimension, item.dominant_dimension_label) ?? item.dominant_dimension_label}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="journal-summary-profile__empty">暂无重点突破词</p>
          )}
        </section>

        <section className="journal-summary-profile__card">
          <h3>重复困惑主题</h3>
          {repeatedTopics.length > 0 ? (
            <ul className="journal-summary-profile__list journal-summary-profile__list--topics">
              {repeatedTopics.slice(0, 3).map(topic => (
                <li key={`${topic.word_context}-${topic.title}`}>
                  <strong>{topic.title}</strong>
                  <span>{topic.count} 次</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="journal-summary-profile__empty">近期没有重复追问主题</p>
          )}
        </section>

        <section className="journal-summary-profile__card">
          <h3>下一步动作</h3>
          {nextActions.length > 0 ? (
            <ul className="journal-summary-profile__actions">
              {nextActions.slice(0, 4).map(action => (
                <li key={action}>{normalizeModeText(action)}</li>
              ))}
            </ul>
          ) : (
            <p className="journal-summary-profile__empty">暂无动作建议</p>
          )}
        </section>
      </div>
    </section>
  )
}

export default function DailySummaryDocument({
  summary,
  learnerProfile,
  learnerProfileLoading,
  summaryLoading,
  summaryError,
  summaryProgress,
  formatDateTime,
}: DailySummaryDocumentProps) {
  return (
    <div className="journal-doc-shell journal-doc-shell--summary">
      <article className="journal-doc-main journal-doc-main--summary">
        <div className="journal-doc-main-scroll journal-doc-main-scroll--summary">
          {summary ? (
            <>
              <header className="journal-doc-hero">
                <span className="journal-doc-date-chip">{summary.date}</span>
                <h1 className="journal-doc-title">{summary.date} 每日学习总结</h1>
                <p className="journal-doc-lead">
                  根据当天学习数据生成复盘摘要，方便按学习日期快速回看重点和后续行动。
                </p>
                <div className="journal-doc-meta-row">
                  <span>更新于 {formatDateTime(summary.generated_at)}</span>
                </div>
                {summaryError ? <div className="journal-error">{summaryError}</div> : null}
              </header>

              <SummaryProfilePanel
                learnerProfile={learnerProfile}
                loading={learnerProfileLoading}
              />

              <div
                className="journal-doc-body journal-doc-body--summary markdown-content"
                dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(summary.content) }}
              />
            </>
          ) : summaryError ? (
            <div className="journal-error">{summaryError}</div>
          ) : summaryProgress ? (
            <SummaryProgressPanel progress={summaryProgress} />
          ) : summaryLoading ? (
            <DailySummarySkeleton />
          ) : (
            <div className="journal-empty journal-empty--main">
              <p>暂无可阅读的总结记录。</p>
              <p>如果当天已有学习记录，可以在右上角生成当日总结。</p>
            </div>
          )}
        </div>
      </article>
    </div>
  )
}
