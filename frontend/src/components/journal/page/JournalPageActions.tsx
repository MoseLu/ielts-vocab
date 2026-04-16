import type { CSSProperties } from 'react'
import refreshIcon from '../../../assets/icons/refresh.svg'
import { today } from '../../../composables/journal/page/journalPageUtils'
import type { SummaryGenerationJob } from '../../../lib/schemas'
import { MicroLoading } from '../../ui'

interface NotesActionsProps {
  startDate: string
  endDate: string
  exporting: boolean
  exportLabel: string
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
  onResetDates: () => void
  onExport: () => void
}

export function JournalNotesActions({
  startDate,
  endDate,
  exporting,
  exportLabel,
  onStartDateChange,
  onEndDateChange,
  onResetDates,
  onExport,
}: NotesActionsProps) {
  return (
    <div className="journal-filter-bar">
      <div className="journal-filter-group">
        <label className="journal-filter-label" htmlFor="journal-start-date">开始日期</label>
        <input
          id="journal-start-date"
          type="date"
          className="journal-date-input"
          value={startDate}
          max={endDate || today()}
          onChange={event => onStartDateChange(event.target.value)}
        />
      </div>
      <div className="journal-filter-group">
        <label className="journal-filter-label" htmlFor="journal-end-date">结束日期</label>
        <input
          id="journal-end-date"
          type="date"
          className="journal-date-input"
          value={endDate}
          max={today()}
          onChange={event => onEndDateChange(event.target.value)}
        />
      </div>
      <button
        className="journal-filter-reset"
        title="重置日期筛选"
        aria-label="重置日期筛选"
        onClick={onResetDates}
      >
        <img src={refreshIcon} alt="" aria-hidden="true" />
      </button>
      <div className="journal-export-group">
        <button
          className="journal-export-btn"
          disabled={exporting}
          onClick={onExport}
          title={exportLabel}
          aria-label={exportLabel}
        >
          {exporting ? (
            <MicroLoading text="导出中..." />
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M12 3v11" />
              <path d="M8 10l4 4 4-4" />
              <path d="M5 19h14" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}

interface SummaryActionsProps {
  selectedSummaryDate: string | null
  summaryTargetDate: string
  generatingDate: string
  exporting: boolean
  exportLabel: string
  generateLoadingText: string
  summaryProgress: SummaryGenerationJob | null
  onGenerate: (date: string) => void
  onExport: () => void
}

export function JournalSummaryActions({
  selectedSummaryDate,
  summaryTargetDate,
  generatingDate,
  exporting,
  exportLabel,
  generateLoadingText,
  summaryProgress,
  onGenerate,
  onExport,
}: SummaryActionsProps) {
  const generationDate = selectedSummaryDate ?? summaryTargetDate
  const generationLabel = selectedSummaryDate ? '重新生成' : '生成今日总结'

  return (
    <div className="journal-summary-actions">
      <div className="journal-summary-actions__buttons">
        <button
          className={selectedSummaryDate ? 'journal-regen-btn' : 'journal-generate-btn'}
          disabled={generatingDate === generationDate}
          onClick={() => onGenerate(generationDate)}
        >
          {generatingDate === generationDate ? <MicroLoading text={generateLoadingText} /> : generationLabel}
        </button>
        <div className="journal-export-group">
          <button
            className="journal-export-btn"
            disabled={exporting}
            onClick={onExport}
            title={exportLabel}
            aria-label={exportLabel}
          >
            {exporting ? (
              <MicroLoading text="导出中..." />
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M12 3v11" />
                <path d="M8 10l4 4 4-4" />
                <path d="M5 19h14" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {summaryProgress ? (
        <div className="journal-summary-progress" role="status" aria-live="polite">
          <div className="journal-summary-progress__head">
            <span>{summaryProgress.message}</span>
            <strong>{summaryProgress.progress}%</strong>
          </div>
          <div className="journal-summary-progress__track" aria-hidden="true">
            <span
              className="journal-summary-progress__fill"
              style={{ '--progress-percent': `${summaryProgress.progress}%` } as CSSProperties}
            />
          </div>
        </div>
      ) : null}
    </div>
  )
}
