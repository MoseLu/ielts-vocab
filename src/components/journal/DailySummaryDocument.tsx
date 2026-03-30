import { renderJournalMarkdown } from '../../lib/journalMarkdown'
import type { DailySummary } from '../../lib/schemas'

interface DailySummaryDocumentProps {
  summary: DailySummary | null
  summaryLoading: boolean
  summaryError: string
  formatDateTime: (iso: string) => string
}

export default function DailySummaryDocument({
  summary,
  summaryLoading,
  summaryError,
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
                  根据当日学习数据生成的复盘摘要，适合按学习日直接查看和回顾。
                </p>
                <div className="journal-doc-meta-row">
                  <span>更新于 {formatDateTime(summary.generated_at)}</span>
                </div>
              </header>

              <div
                className="journal-doc-body journal-doc-body--summary markdown-content"
                dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(summary.content) }}
              />
            </>
          ) : summaryError ? (
            <div className="journal-error">{summaryError}</div>
          ) : (
            <div className="journal-empty journal-empty--main">
              <p>{summaryLoading ? '加载中...' : '暂无可阅读的总结记录。'}</p>
              {!summaryLoading && <p>如果当天已有学习记录，可以在右上角生成当日总结。</p>}
            </div>
          )}
        </div>
      </article>
    </div>
  )
}
