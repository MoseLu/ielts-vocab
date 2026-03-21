import React from 'react'

type ToastType = 'info' | 'success' | 'error'

interface ToastProps {
  message: string
  type?: ToastType
}

function Toast({ message, type = 'info' }: ToastProps) {
  return (
    <div className={`toast toast-${type}`}>
      {message}
    </div>
  )
}

export default Toast
