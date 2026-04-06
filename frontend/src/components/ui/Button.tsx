// ── Button Component ───────────────────────────────────────────────────────────

import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'warning'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const buttonClassName = [
    'ui-button',
    `ui-button--${variant}`,
    `ui-button--${size}`,
    className,
  ].filter(Boolean).join(' ')

  return (
    <button
      className={buttonClassName}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <svg className="ui-button__spinner loading-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {leftIcon && <span className="ui-button__icon">{leftIcon}</span>}
      {children}
      {rightIcon && <span className="ui-button__icon">{rightIcon}</span>}
    </button>
  )
}
