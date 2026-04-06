// ── Input Components ────────────────────────────────────────────────────────────

import React, { forwardRef, useId } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  helperText,
  leftIcon,
  rightIcon,
  className = '',
  id,
  ...props
}, ref) => {
  const generatedId = useId()
  const inputId = id || generatedId
  const inputClassName = [
    'ui-input',
    leftIcon ? 'ui-input--with-left-icon' : '',
    rightIcon ? 'ui-input--with-right-icon' : '',
    error ? 'ui-input--error' : '',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className="ui-field">
      {label && (
        <label htmlFor={inputId} className="ui-field__label">
          {label}
        </label>
      )}
      <div className="ui-input-shell">
        {leftIcon && (
          <div className="ui-input-icon ui-input-icon--left">
            {leftIcon}
          </div>
        )}
        <input
          ref={ref}
          id={inputId}
          className={inputClassName}
          {...props}
        />
        {rightIcon && (
          <div className="ui-input-icon ui-input-icon--right">
            {rightIcon}
          </div>
        )}
      </div>
      {error && <p className="ui-field__message ui-field__message--error">{error}</p>}
      {helperText && !error && <p className="ui-field__message ui-field__message--helper">{helperText}</p>}
    </div>
  )
})

Input.displayName = 'Input'

// Textarea variant
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({
  label,
  error,
  className = '',
  id,
  ...props
}, ref) => {
  const generatedId = useId()
  const textareaId = id || generatedId
  const textareaClassName = [
    'ui-textarea',
    error ? 'ui-textarea--error' : '',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className="ui-field">
      {label && (
        <label htmlFor={textareaId} className="ui-field__label">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        className={textareaClassName}
        {...props}
      />
      {error && <p className="ui-field__message ui-field__message--error">{error}</p>}
    </div>
  )
})

Textarea.displayName = 'Textarea'
