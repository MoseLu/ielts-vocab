// ── Button Component ───────────────────────────────────────────────────────────

import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
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
  const baseStyles = 'inline-flex items-center justify-center gap-2 font-medium rounded-2xl border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 active:scale-[0.99]'

  const variants = {
    primary: 'border-transparent bg-accent text-white shadow-[0_14px_28px_rgba(255,126,54,0.24)] hover:-translate-y-0.5 hover:bg-accent/90 hover:shadow-[0_18px_34px_rgba(255,126,54,0.28)] focus:ring-accent',
    secondary: 'border-[#E5E7EB] bg-white/90 text-primary shadow-sm hover:-translate-y-0.5 hover:border-[#FFD5BF] hover:bg-[#FFF8F3] hover:shadow-md focus:ring-secondary',
    ghost: 'border-transparent bg-transparent text-primary hover:bg-secondary/90 focus:ring-secondary',
    danger: 'border-transparent bg-error text-white shadow-[0_14px_28px_rgba(239,68,68,0.18)] hover:-translate-y-0.5 hover:bg-error/90 focus:ring-error',
  }

  const sizes = {
    sm: 'min-h-9 px-3.5 text-sm',
    md: 'min-h-11 px-4.5 text-sm',
    lg: 'min-h-12 px-6 text-base',
  }

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${disabled || isLoading ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {leftIcon && <span className="flex items-center justify-center">{leftIcon}</span>}
      {children}
      {rightIcon && <span className="flex items-center justify-center">{rightIcon}</span>}
    </button>
  )
}
