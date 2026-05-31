import { type KeyboardEvent, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react'

export interface ErrorsFilterSelectOption<T extends string> {
  value: T
  label: string
  disabled?: boolean
  title?: string
}

interface ErrorsFilterSelectProps<T extends string> {
  ariaLabel: string
  value: T
  options: Array<ErrorsFilterSelectOption<T>>
  onChange: (value: T) => void
  className?: string
}

function nextEnabledValue<T extends string>(
  options: Array<ErrorsFilterSelectOption<T>>,
  currentValue: T,
  direction: 1 | -1,
): T {
  const enabled = options.filter(option => !option.disabled)
  if (enabled.length === 0) return currentValue
  const currentIndex = Math.max(0, enabled.findIndex(option => option.value === currentValue))
  const nextIndex = (currentIndex + direction + enabled.length) % enabled.length
  return enabled[nextIndex].value
}

export function ErrorsFilterSelect<T extends string>({
  ariaLabel,
  value,
  options,
  onChange,
  className = '',
}: ErrorsFilterSelectProps<T>) {
  const [open, setOpen] = useState(false)
  const [openAbove, setOpenAbove] = useState(false)
  const [activeValue, setActiveValue] = useState(value)
  const id = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const selected = useMemo(
    () => options.find(option => option.value === value) ?? options[0],
    [options, value],
  )
  useEffect(() => {
    if (open) setActiveValue(value)
  }, [open, value])

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
  }, [open, options.length])

  const commitValue = (nextValue: T) => {
    const nextOption = options.find(option => option.value === nextValue)
    if (!nextOption || nextOption.disabled) return
    onChange(nextValue)
    setOpen(false)
    requestAnimationFrame(() => triggerRef.current?.focus())
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Escape') {
      setOpen(false)
      return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const direction = event.key === 'ArrowDown' ? 1 : -1
      setOpen(true)
      setActiveValue(current => nextEnabledValue(options, current, direction))
      return
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (open) commitValue(activeValue)
      else setOpen(true)
    }
  }

  return (
    <div ref={rootRef} className={`errors-filter-select-shell ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        className={`errors-filter-select-trigger${open ? ' is-open' : ''}`}
        role="combobox"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={`${id}-listbox`}
        aria-activedescendant={open ? `${id}-option-${activeValue}` : undefined}
        title={selected?.title}
        onClick={() => setOpen(current => !current)}
        onKeyDown={handleKeyDown}
      >
        <span className="errors-filter-select-value">{selected?.label ?? ''}</span>
        <svg className="errors-filter-select-arrow" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M4 6l4 4 4-4" />
        </svg>
      </button>
      {open && (
        <div ref={popupRef} className={`errors-filter-select-popup${openAbove ? ' is-above' : ''}`}>
          <div id={`${id}-listbox`} className="errors-filter-select-menu" role="listbox">
            {options.map(option => {
              const active = activeValue === option.value
              const selectedOption = value === option.value
              return (
                <div
                  key={option.value}
                  id={`${id}-option-${option.value}`}
                  className={`errors-filter-select-option${active ? ' is-active' : ''}${selectedOption ? ' is-selected' : ''}${option.disabled ? ' is-disabled' : ''}`}
                  role="option"
                  aria-selected={selectedOption}
                  aria-disabled={option.disabled || undefined}
                  title={option.title}
                  onMouseEnter={() => !option.disabled && setActiveValue(option.value)}
                  onClick={() => commitValue(option.value)}
                >
                  <span className="errors-filter-select-option-label">{option.label}</span>
                  {selectedOption && (
                    <svg className="errors-filter-select-check" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="M3.5 8.2l2.8 2.8 6.2-6.4" />
                    </svg>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
