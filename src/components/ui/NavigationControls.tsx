import type { ReactNode } from 'react'

export interface NavigationOption<T extends string = string> {
  value: T
  label: ReactNode
  badge?: ReactNode
  disabled?: boolean
  title?: string
}

type NavigationSize = 'small' | 'middle' | 'large'

interface NavigationControlProps<T extends string> {
  value: T
  options: NavigationOption<T>[]
  onChange: (value: T) => void
  className?: string
  stretch?: boolean
  ariaLabel?: string
}

interface UnderlineTabsProps<T extends string> extends NavigationControlProps<T> {
  size?: NavigationSize
}

function withClassNames(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}

export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  className = '',
  stretch = false,
  ariaLabel,
}: NavigationControlProps<T>) {
  return (
    <div
      className={withClassNames('segmented-control', stretch && 'segmented-control--stretch', className)}
      role="tablist"
      aria-label={ariaLabel}
    >
      {options.map(option => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            title={option.title}
            disabled={option.disabled}
            className={withClassNames(
              'segmented-control__item',
              active && 'is-active',
              stretch && 'segmented-control__item--stretch',
            )}
            onClick={() => onChange(option.value)}
          >
            <span className="segmented-control__label">{option.label}</span>
            {option.badge != null && (
              <span className="segmented-control__badge">{option.badge}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

export function UnderlineTabs<T extends string>({
  value,
  options,
  onChange,
  className = '',
  stretch = false,
  ariaLabel,
  size = 'middle',
}: UnderlineTabsProps<T>) {
  return (
    <div
      className={withClassNames(
        'underline-tabs',
        `underline-tabs--${size}`,
        stretch && 'underline-tabs--stretch',
        className,
      )}
      role="tablist"
      aria-label={ariaLabel}
    >
      {options.map(option => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            title={option.title}
            disabled={option.disabled}
            className={withClassNames(
              'underline-tabs__item',
              `underline-tabs__item--${size}`,
              active && 'is-active',
              stretch && 'underline-tabs__item--stretch',
            )}
            onClick={() => onChange(option.value)}
          >
            <span className="underline-tabs__label">{option.label}</span>
            {option.badge != null && (
              <span className="underline-tabs__badge">{option.badge}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
