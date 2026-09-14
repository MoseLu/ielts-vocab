import { useEffect, useMemo, useRef, useState } from 'react'
import refreshIcon from '../../../assets/icons/refresh.svg'
import { today } from '../../../composables/journal/page/journalPageUtils'
import { MicroLoading } from '../../ui'

const CALENDAR_ICON = (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M16 3v4M8 3v4M3 10h18" />
  </svg>
)

const START_DATE_PLACEHOLDER = '开始日期'
const END_DATE_PLACEHOLDER = '结束日期'
const DATE_INPUT_PATTERN = /^([0-9]{4})[/-]([0-9]{2})[/-]([0-9]{2})$/
const WEEKDAY_LABELS = ['日', '一', '二', '三', '四', '五', '六']
const RANGE_SHORTCUTS = [
  { label: '上星期', days: 7 },
  { label: '上个月', months: 1 },
  { label: '过去三个月', months: 3 },
] as const

function formatDateForInput(value: string): string {
  return value.replace(/-/g, '/')
}

function normalizeDateInput(value: string, max?: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''

  const match = DATE_INPUT_PATTERN.exec(trimmed)
  const normalized = match ? `${match[1]}-${match[2]}-${match[3]}` : trimmed.replace(/\//g, '-')
  if (max && DATE_INPUT_PATTERN.test(normalized) && normalized > max) return max
  return normalized
}

function dateFromISO(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function isoFromDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addMonths(date: Date, offset: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + offset, 1)
}

function addDays(date: Date, offset: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + offset)
  return next
}

function monthLabel(date: Date): string {
  return `${date.getFullYear()}年 ${date.getMonth() + 1}月`
}

function buildMonthDays(monthDate: Date) {
  const firstDay = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1)
  const start = addDays(firstDay, -firstDay.getDay())
  return Array.from({ length: 42 }, (_, index) => addDays(start, index))
}

/* ── Today Notes Actions (edit toggle + AI polish) ── */

interface TodayNotesActionsProps {
  editMode: boolean
  polishing: boolean
  onToggleEdit: () => void
  onPolish: () => void
}

const ROBOT_ICON_SVG = `<svg viewBox="0 0 1024 1024" width="18" height="18"><path d="M482.816 64a127.104 127.104 0 0 1 39.616 247.872l-0.128 43.776h106.368a272.96 272.96 0 0 1 256.064 178.56 39.552 39.552 0 0 1-74.24 27.392 193.92 193.92 0 0 0-181.888-126.784H336.896a193.856 193.856 0 0 0-193.856 193.792v58.432a193.856 193.856 0 0 0 193.92 193.856h291.712a39.552 39.552 0 1 1 0 79.04H336.896A272.96 272.96 0 0 1 64 686.912V628.48a272.96 272.96 0 0 1 272.96-272.768h106.304v-43.904A127.104 127.104 0 0 1 482.752 64h0.064z m323.392 593.728a16.192 16.192 0 0 1 13.376 13.376 140.16 140.16 0 0 0 104.512 114.24l12.16 2.432a16 16 0 0 1 0 31.808c-55.552 8.768-100.608 49.92-114.24 104.512l-2.432 12.16a16 16 0 0 1-31.808 0 140.16 140.16 0 0 0-104.576-114.24l-12.096-2.432a16 16 0 0 1 0-31.808 140.16 140.16 0 0 0 114.24-104.576l2.432-12.096a16 16 0 0 1 18.432-13.312zM336.96 570.304a58.368 58.368 0 1 1 3.84 116.736 58.368 58.368 0 0 1-3.84-116.736z m291.776 0a58.368 58.368 0 1 1 4.032 116.736 58.368 58.368 0 0 1-4.096-116.736z m-145.92-427.136a48 48 0 1 0-3.2 96 48 48 0 0 0 3.2-96z" fill="currentColor"/></svg>`

export function TodayNotesActions({
  editMode,
  polishing,
  onToggleEdit,
  onPolish,
}: TodayNotesActionsProps) {
  return (
    <div className="journal-today-actions">
      <button
        className="journal-edit-toggle-btn"
        title={editMode ? '退出编辑' : '编辑今日复盘'}
        aria-label={editMode ? '退出编辑' : '编辑今日复盘'}
        onClick={onToggleEdit}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
          {editMode ? (
            <>
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
              <polyline points="17 21 17 13 7 13 7 21" />
              <polyline points="7 3 7 8 15 8" />
            </>
          ) : (
            <>
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </>
          )}
        </svg>
      </button>

      {editMode && (
        <button
          className="journal-polish-btn"
          disabled={polishing}
          onClick={() => onPolish()}
          title="AI 润色"
          aria-label="AI 润色"
        >
          {polishing ? (
            <MicroLoading text="润色中..." />
          ) : (
            <span className="journal-polish-icon" dangerouslySetInnerHTML={{ __html: ROBOT_ICON_SVG }} />
          )}
        </button>
      )}
    </div>
  )
}

/* ── History Notes Actions (date filter + export) ── */

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
  const [panelOpen, setPanelOpen] = useState(false)
  const [draftStart, setDraftStart] = useState(startDate)
  const [draftEnd, setDraftEnd] = useState(endDate)
  const [monthCursor, setMonthCursor] = useState(() => dateFromISO(startDate || endDate || today()))
  const pickerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setDraftStart(startDate)
    setDraftEnd(endDate)
  }, [startDate, endDate])

  useEffect(() => {
    if (!panelOpen) return

    const handlePointerDown = (event: PointerEvent) => {
      if (!pickerRef.current?.contains(event.target as Node)) setPanelOpen(false)
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setPanelOpen(false)
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [panelOpen])

  const calendarMonths = useMemo(() => {
    const leftMonth = new Date(monthCursor.getFullYear(), monthCursor.getMonth(), 1)
    return [leftMonth, addMonths(leftMonth, 1)]
  }, [monthCursor])

  const openPanel = () => {
    setMonthCursor(dateFromISO(startDate || endDate || today()))
    setPanelOpen(true)
  }

  const applyRange = (nextStart: string, nextEnd: string) => {
    onStartDateChange(nextStart)
    onEndDateChange(nextEnd)
  }

  const handleShortcut = (shortcut: (typeof RANGE_SHORTCUTS)[number]) => {
    const end = today()
    const endDateValue = dateFromISO(end)
    const startDateValue = 'months' in shortcut
      ? addMonths(endDateValue, -shortcut.months)
      : addDays(endDateValue, -shortcut.days + 1)
    const nextStart = isoFromDate(startDateValue)
    setDraftStart(nextStart)
    setDraftEnd(end)
    applyRange(nextStart, end)
    setPanelOpen(false)
  }

  const handleDaySelect = (dateValue: string) => {
    if (!draftStart || (draftStart && draftEnd)) {
      setDraftStart(dateValue)
      setDraftEnd('')
      return
    }

    if (dateValue < draftStart) {
      setDraftEnd(draftStart)
      setDraftStart(dateValue)
      return
    }
    setDraftEnd(dateValue)
  }

  const clearRange = () => {
    setDraftStart('')
    setDraftEnd(today())
    applyRange('', today())
    setPanelOpen(false)
  }

  const confirmRange = () => {
    applyRange(draftStart, draftEnd || today())
    setPanelOpen(false)
  }

  return (
    <div className="journal-filter-bar">
      <div className="journal-date-picker" ref={pickerRef}>
        <div
          className="journal-date-range-field"
          aria-label="日记日期范围筛选"
          aria-haspopup="dialog"
          aria-expanded={panelOpen}
          onPointerDown={openPanel}
        >
          <div className="journal-filter-group journal-date-range-segment">
            <span className="journal-date-icon">{CALENDAR_ICON}</span>
            <input
              id="journal-start-date"
              type="text"
              inputMode="numeric"
              autoComplete="off"
              aria-label={START_DATE_PLACEHOLDER}
              placeholder={START_DATE_PLACEHOLDER}
              className="journal-date-input"
              value={formatDateForInput(startDate)}
              readOnly
              onFocus={openPanel}
            />
          </div>

          <span className="journal-date-range-separator" aria-hidden="true">到</span>

          <div className="journal-filter-group journal-date-range-segment">
            <span className="journal-date-icon">{CALENDAR_ICON}</span>
            <input
              id="journal-end-date"
              type="text"
              inputMode="numeric"
              autoComplete="off"
              aria-label={END_DATE_PLACEHOLDER}
              placeholder={END_DATE_PLACEHOLDER}
              className="journal-date-input"
              value={formatDateForInput(endDate)}
              readOnly
              onFocus={openPanel}
            />
          </div>
        </div>

        {panelOpen && (
          <div className="journal-date-popover" role="dialog" aria-label="选择日记日期范围">
            <div className="journal-date-shortcuts">
              {RANGE_SHORTCUTS.map(shortcut => (
                <button key={shortcut.label} type="button" onClick={() => handleShortcut(shortcut)}>
                  {shortcut.label}
                </button>
              ))}
            </div>

            <div className="journal-date-panel">
              <div className="journal-date-panel-inputs">
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="开始日期"
                  value={formatDateForInput(draftStart)}
                  onChange={event => setDraftStart(normalizeDateInput(event.target.value, draftEnd || today()))}
                />
                <span>›</span>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="结束日期"
                  value={formatDateForInput(draftEnd)}
                  onChange={event => setDraftEnd(normalizeDateInput(event.target.value, today()))}
                />
              </div>

              <div className="journal-date-calendars">
                {calendarMonths.map((monthDate, monthIndex) => (
                  <div className="journal-date-calendar" key={monthDate.toISOString()}>
                    <div className="journal-date-calendar__header">
                      {monthIndex === 0 && (
                        <button type="button" onClick={() => setMonthCursor(addMonths(monthCursor, -1))}>‹</button>
                      )}
                      <strong>{monthLabel(monthDate)}</strong>
                      {monthIndex === 1 && (
                        <button type="button" onClick={() => setMonthCursor(addMonths(monthCursor, 1))}>›</button>
                      )}
                    </div>
                    <div className="journal-date-weekdays">
                      {WEEKDAY_LABELS.map(label => <span key={label}>{label}</span>)}
                    </div>
                    <div className="journal-date-days">
                      {buildMonthDays(monthDate).map(day => {
                        const dateValue = isoFromDate(day)
                        const isOutside = day.getMonth() !== monthDate.getMonth()
                        const isDisabled = dateValue > today()
                        const isSelected = dateValue === draftStart || dateValue === draftEnd
                        const isInRange = Boolean(draftStart && draftEnd && dateValue > draftStart && dateValue < draftEnd)
                        return (
                          <button
                            key={dateValue}
                            type="button"
                            className={[
                              isOutside ? 'is-outside' : '',
                              isSelected ? 'is-selected' : '',
                              isInRange ? 'is-in-range' : '',
                            ].filter(Boolean).join(' ')}
                            disabled={isDisabled}
                            onClick={() => handleDaySelect(dateValue)}
                          >
                            {day.getDate()}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="journal-date-actions">
                <button type="button" onClick={clearRange}>清除</button>
                <button type="button" className="journal-date-actions__primary" onClick={confirmRange}>好的</button>
              </div>
            </div>
          </div>
        )}
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
