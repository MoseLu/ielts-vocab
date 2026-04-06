// ── Modal Components ────────────────────────────────────────────────────────────

import React, { useEffect, useId, useRef } from 'react'
import { Button } from './Button'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  closeOnOverlay?: boolean
  showCloseButton?: boolean
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  closeOnOverlay = true,
  showCloseButton = true,
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="ui-modal">
      <div
        className="ui-modal__overlay"
        onClick={closeOnOverlay ? onClose : undefined}
      />
      <div
        ref={modalRef}
        className={['ui-modal__panel', `ui-modal__panel--${size}`].join(' ')}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
      >
        {(title || showCloseButton) && (
          <div className="ui-modal__header">
            {title && (
              <h2 id={titleId} className="ui-modal__title">
                {title}
              </h2>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className="ui-modal__close"
                aria-label="关闭"
              >
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        )}
        <div className="ui-modal__body">{children}</div>
      </div>
    </div>
  )
}

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info'
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  variant = 'danger',
}: ConfirmDialogProps) {
  const confirmVariant = {
    danger: 'danger',
    warning: 'warning',
    info: 'primary',
  } as const

  const handleConfirm = () => {
    onConfirm()
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm" showCloseButton={false}>
      <p>{message}</p>
      <div className="ui-modal__actions">
        <Button variant="secondary" onClick={onClose}>
          {cancelText}
        </Button>
        <Button variant={confirmVariant[variant]} onClick={handleConfirm}>
          {confirmText}
        </Button>
      </div>
    </Modal>
  )
}
