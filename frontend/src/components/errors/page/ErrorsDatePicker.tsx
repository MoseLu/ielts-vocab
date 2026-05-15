import { type KeyboardEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'

interface ErrorsDatePickerProps {
  ariaLabel: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']
const DATE_PATTERN = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/

function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDate(value: string): Date | null {
  const match = DATE_PATTERN.exec(value.trim())
  if (!match) return null

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(year, month - 1, day)
  if (
    date.getFullYear() !== year
    || date.getMonth() !== month - 1
    || date.getDate() !== day
  ) {
    return null
  }
  return date
}

function monthStart(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function addMonths(date: Date, amount: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1)
}

function sameDay(left: Date, right: Date): boolean {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate()
}

function calendarDays(month: Date): Date[] {
  const first = monthStart(month)
  const mondayOffset = (first.getDay() + 6) % 7
  const start = new Date(first.getFullYear(), first.getMonth(), 1 - mondayOffset)
  return Array.from({ length: 42 }, (_, index) => (
    new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
  ))
}

export function ErrorsDatePicker({
  ariaLabel,
  value,
  onChange,
  placeholder = '选择日期',
}: ErrorsDatePickerProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const selectedDate = useMemo(() => parseDate(value), [value])
  const [open, setOpen] = useState(false)
  const [openAbove, setOpenAbove] = useState(false)
  const [visibleMonth, setVisibleMonth] = useState(() => monthStart(selectedDate ?? new Date()))
  const days = useMemo(() => calendarDays(visibleMonth), [visibleMonth])
  const today = useMemo(() => new Date(), [])

  useEffect(() => {
    if (selectedDate) setVisibleMonth(monthStart(selectedDate))
  }, [selectedDate])

  useEffect(() => {
    if (!open) return
    const closeOnOutside = (event: PointerEvent) => {
      const target = event.target
      if (target instanceof Node && rootRef.current?.contains(target)) return
      setOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutside)
    return () => document.removeEventListener('pointerdown', closeOnOutside)
  }, [open])

  useLayoutEffect(() => {
    if (!open) {
      setOpenAbove(false)
      return
    }

    const updatePlacement = () => {
      const root = rootRef.current
      const popup = popupRef.current
      if (!root || !popup) return

      const gap = 8
      const rootRect = root.getBoundingClientRect()
      const popupHeight = popup.getBoundingClientRect().height
      const viewportHeight = window.visualViewport?.height ?? window.innerHeight
      const isMobileViewport = typeof window.matchMedia === 'function'
        ? window.matchMedia('(max-width: 768px)').matches
        : window.innerWidth <= 768
      const bottomSafeArea = isMobileViewport ? 96 : 12
      const spaceBelow = viewportHeight - rootRect.bottom - gap - bottomSafeArea
      const spaceAbove = rootRect.top - gap - 12
      setOpenAbove(spaceBelow < popupHeight && spaceAbove > spaceBelow)
    }

    updatePlacement()
    window.addEventListener('resize', updatePlacement)
    window.addEventListener('scroll', updatePlacement, true)
    return () => {
      window.removeEventListener('resize', updatePlacement)
      window.removeEventListener('scroll', updatePlacement, true)
    }
  }, [open, visibleMonth])

  const commitDate = (date: Date) => {
    onChange(formatDate(date))
    setVisibleMonth(monthStart(date))
    setOpen(false)
    requestAnimationFrame(() => inputRef.current?.focus())
  }

  const handleInputChange = (nextValue: string) => {
    onChange(nextValue)
    const parsed = parseDate(nextValue)
    if (parsed) setVisibleMonth(monthStart(parsed))
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setOpen(false)
      return
    }
    if (event.key === 'Enter') {
      const parsed = parseDate(value)
      if (parsed) {
        event.preventDefault()
        commitDate(parsed)
      }
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
    }
  }

  const monthLabel = `${visibleMonth.getFullYear()} 年 ${visibleMonth.getMonth() + 1} 月`

  return (
    <div ref={rootRef} className="errors-date-picker">
      <div className={`errors-date-picker-control${open ? ' is-open' : ''}`}>
        <input
          ref={inputRef}
          aria-label={ariaLabel}
          className="errors-date-picker-input"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          placeholder={placeholder}
          pattern="[0-9]{4}-[0-9]{2}-[0-9]{2}"
          value={value}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onChange={event => handleInputChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="errors-date-picker-icon"
          aria-label={`打开${ariaLabel}日历`}
          onMouseDown={event => event.preventDefault()}
          onClick={() => {
            setOpen(current => !current)
            inputRef.current?.focus()
          }}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="5" width="18" height="16" rx="2" />
            <path d="M16 3v4M8 3v4M3 10h18" />
          </svg>
        </button>
      </div>

      {open && (
        <div
          ref={popupRef}
          className={`errors-date-picker-popup${openAbove ? ' is-above' : ''}`}
          role="dialog"
          aria-label={`${ariaLabel}日历`}
        >
          <div className="errors-date-picker-header">
            <button type="button" className="errors-date-picker-nav" aria-label="上一年" onClick={() => setVisibleMonth(current => addMonths(current, -12))}>
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10.5 3.5L6 8l4.5 4.5M6.5 3.5L2 8l4.5 4.5" /></svg>
            </button>
            <button type="button" className="errors-date-picker-nav" aria-label="上个月" onClick={() => setVisibleMonth(current => addMonths(current, -1))}>
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3.5L5.5 8l4.5 4.5" /></svg>
            </button>
            <span className="errors-date-picker-title">{monthLabel}</span>
            <button type="button" className="errors-date-picker-nav" aria-label="下个月" onClick={() => setVisibleMonth(current => addMonths(current, 1))}>
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5L10.5 8 6 12.5" /></svg>
            </button>
            <button type="button" className="errors-date-picker-nav" aria-label="下一年" onClick={() => setVisibleMonth(current => addMonths(current, 12))}>
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5.5 3.5L10 8l-4.5 4.5M9.5 3.5L14 8l-4.5 4.5" /></svg>
            </button>
          </div>

          <div className="errors-date-picker-weekdays" aria-hidden="true">
            {WEEKDAYS.map(day => <span key={day}>{day}</span>)}
          </div>
          <div className="errors-date-picker-grid">
            {days.map(day => {
              const outside = day.getMonth() !== visibleMonth.getMonth()
              const selected = selectedDate ? sameDay(day, selectedDate) : false
              const currentDay = sameDay(day, today)
              return (
                <button
                  key={formatDate(day)}
                  type="button"
                  className={`errors-date-picker-day${outside ? ' is-outside' : ''}${selected ? ' is-selected' : ''}${currentDay ? ' is-today' : ''}`}
                  aria-label={`选择日期 ${formatDate(day)}`}
                  aria-pressed={selected}
                  onClick={() => commitDate(day)}
                >
                  <span>{day.getDate()}</span>
                </button>
              )
            })}
          </div>

          <div className="errors-date-picker-footer">
            <button type="button" className="errors-date-picker-action" onClick={() => commitDate(today)}>
              今天
            </button>
            <button type="button" className="errors-date-picker-action" disabled={!value} onClick={() => onChange('')}>
              清空
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
